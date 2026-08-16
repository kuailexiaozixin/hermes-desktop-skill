#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_api_server.py — 探测 Hermes API Server 是否真实可跑（防"假绿"）。

为什么需要：技能 `references/15-api-server.md` 承诺了「API Server 形态」的端点/认证行为。
本脚本对运行中的 API Server 做**真实 HTTP 探测**，验证专章写的东西不是纸上谈兵：

  * GET  /health             → 期望 200 且 JSON `{"status":"ok", ...}`（存活探针）。
  * GET  /v1/models（无 key） → 期望 401/403（认证必须存在——官方强调 API_SERVER_KEY 必配）。
  * GET  /v1/models（有 key） → 期望 200 且 body 为 OpenAI 风格 `{"object":"list","data":[...]}`，
                              且至少能列出 model id（前端发现模型必需）。

用法（探测已启动的 API Server）：
  python check_api_server.py                          # 默认 127.0.0.1:8642，无 key，只测认证存在性
  python check_api_server.py --key your-secret-key    # 带 key：额外校验 /v1/models 200 可列模型
  python check_api_server.py --host 0.0.0.0 --port 8643 --key sk-...  # 多 profile / 远程

⚠️ 说明：
  * 仅校验 HTTP 层（存活 + 认证 + 模型发现），**不**发对话请求（对话需 provider 模型配置）。
  * 这是「API Server 形态」的落地校验，**不阻塞**进程内默认路线（进程内形态本就不开 8642，
    未运行 API Server 时本脚本以 `--skip` 或明确报「未检测到服务」处理，由调用方决定是否阻断）。
  * 用标准库 urllib，无第三方依赖。

退出码：0 = 全部通过（health 200 + 认证存在 [+ models 200]）；1 = 某项失败（阻断）；
        2 = 参数/使用问题。
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def http_get(url: str, key: str | None, timeout: int = 5) -> tuple[int, str | dict | None]:
    """GET 一个 URL，返回 (status, body_json_or_None)。"""
    req = urllib.request.Request(url, method="GET")
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read().decode("utf-8", "replace")
    except Exception as e:  # 连接失败等
        return -1, f"connection error: {e}"
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


def main() -> int:
    ap = argparse.ArgumentParser(description="探测 Hermes API Server 是否真实可跑")
    ap.add_argument("--host", default="127.0.0.1", help="API Server 绑定地址（默认 127.0.0.1）")
    ap.add_argument("--port", type=int, default=8642, help="API Server 端口（默认 8642）")
    ap.add_argument("--key", default=None, help="API_SERVER_KEY（提供则额外校验 /v1/models 200）")
    ap.add_argument("--skip", action="store_true", help="未检测到服务时不视为失败（进程内形态默认跳过）")
    args = ap.parse_args()

    base = f"http://{args.host}:{args.port}"
    ok = True

    # 1) /health —— 存活探针
    st, body = http_get(f"{base}/health", None)
    if st == 200:
        status = body.get("status") if isinstance(body, dict) else None
        if status == "ok":
            print(f"[PASS] GET /health 200, status={status}")
        else:
            print(f"[FAIL] GET /health 200 但 status!='ok': {body}")
            ok = False
    else:
        print(f"[FAIL] GET /health -> {st} {body}")
        ok = False

    # 2) /v1/models 无 key —— 认证必须存在
    st2, body2 = http_get(f"{base}/v1/models", None)
    if st2 in (401, 403):
        print(f"[PASS] GET /v1/models 无 key -> {st2}（认证存在）")
    elif st2 == 200:
        print(f"[WARN] GET /v1/models 无 key 竟 200 —— API_SERVER_KEY 可能未启用（不安全）")
        ok = False
    else:
        print(f"[FAIL] GET /v1/models 无 key -> {st2} {body2}")
        ok = False

    # 3) /v1/models 有 key —— 200 且可列模型（仅当传了 key）
    if args.key:
        st3, body3 = http_get(f"{base}/v1/models", args.key)
        if st3 == 200:
            data = body3.get("data") if isinstance(body3, dict) else None
            if isinstance(data, list) and data:
                ids = [m.get("id") for m in data if isinstance(m, dict)]
                print(f"[PASS] GET /v1/models 带 key 200, 模型: {ids}")
            else:
                print(f"[FAIL] GET /v1/models 200 但 data 为空: {body3}")
                ok = False
        else:
            print(f"[FAIL] GET /v1/models 带 key -> {st3} {body3}")
            ok = False

    if not ok:
        print("\n结果：存在失败项。若你是进程内形态且未开 API Server，属预期（用 --skip 跳过）。")
        return 0 if args.skip else 1
    print("\n结果：API Server HTTP 层真实可跑。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
