"""工具集运行时（方案 A 重构后）：能力矩阵发现 / 配置 / 测试 / 开关。

重构要点（行为契约不变，见 tests/test_toolsets_specs.py 与基线 diff）：
  * 工具集元数据（label/分类/env/提示/试用规格/探测项）全部来自
    ``_toolset_specs.TOOLSET_SPECS`` 单一事实源；原四张平行字典以兼容视图
    从 spec 派生并保持导出名不变。
  * ``_runtime_probe`` 的 250 行 if/elif（含重复死代码分支）由声明式
    ``run_probes``（EnvSpec 通用探测 + 专用 probe_fn）取代。
  * 缓存层、config.yaml 写入路径、线程锁、审批命令执行器原样保留。
"""
from __future__ import annotations

import os
import re
import threading
from typing import Any  # noqa: F401  (保留既有签名习惯)

from ._tools import DANGEROUS_TOOLSETS, DISABLED_TOOLSETS, register_pure_python_tools
from ._toolset_specs import (
    TOOLSET_SPECS,
    # 兼容视图（由 spec 派生，键值与重构前逐字段等价）
    TOOLSET_LABELS, TOOLSET_CATEGORIES, TOOLSET_RUNTIME_HINTS, ENV_REQUIRED,
    TRIAL_FORCE, TRIAL_PROMPTS,
    CATEGORY_ORDER,
    get_spec, build_trial_force, build_trial_prompt, run_probes, inject_agent_env,
)

# 兼容别名：历史上本模块内叫 _tool_env
_tool_env = inject_agent_env

# 最后测试结果缓存（模块级，进程内持久化，不落盘）
_last_test_results: dict[str, dict] = {}


# ============================================================================
# 7) 工具集能力矩阵（设置中心「工具与集成」面板数据源）
# ============================================================================
# ── 工具集发现缓存 ───────────────────────────────────────────────
# registry.get_available_toolsets() 会逐个运行工具集 check_fn（含网络健康探测），
# 单次约 4s；若不缓存，每次进入「工具集成」都会卡数秒。这里缓存矩阵，并以
# 「过期返回旧值 + 后台刷新」策略保证前台永远即时返回；toolset 切换/配置/测试后
# 调 invalidate_toolset_cache() 强制下次同步刷新。
_TOOLSET_MATRIX_CACHE = {"ts": 0.0, "data": None, "computing": False}
_TOOLSET_CACHE_TTL = 120.0  # 秒

def _compute_toolset_matrix() -> dict:
    global _TOOLSET_MATRIX_CACHE
    import time as _t
    register_pure_python_tools()  # 必须先注册纯 Python 工具，否则矩阵为空
    from tools.registry import registry
    data = registry.get_available_toolsets() or {}
    _TOOLSET_MATRIX_CACHE["data"] = data
    _TOOLSET_MATRIX_CACHE["ts"] = _t.time()
    _TOOLSET_MATRIX_CACHE["computing"] = False
    return data

def get_toolset_matrix(force: bool = False) -> dict:
    """返回工具集能力矩阵（带缓存）。force=True 时同步重算（用于状态变更后）。"""
    global _TOOLSET_MATRIX_CACHE
    import time as _t
    cached = _TOOLSET_MATRIX_CACHE["data"]
    if force or cached is None:
        return _compute_toolset_matrix()
    if (_t.time() - _TOOLSET_MATRIX_CACHE["ts"]) >= _TOOLSET_CACHE_TTL and not _TOOLSET_MATRIX_CACHE["computing"]:
        # 已过期：后台刷新，前台立即返回旧值（避免用户每次进入都等网络探测）
        _TOOLSET_MATRIX_CACHE["computing"] = True
        threading.Thread(target=_compute_toolset_matrix, daemon=True).start()
    return cached

def invalidate_toolset_cache() -> None:
    """toolset 状态变更（禁用/启用/配置/测试）后失效缓存，下次进入重新探测。"""
    global _TOOLSET_MATRIX_CACHE
    _TOOLSET_MATRIX_CACHE["data"] = None
    _TOOLSET_MATRIX_CACHE["computing"] = False


def discover_toolsets() -> list[dict]:
    """进程内枚举工具集能力矩阵，替代网关的 /v1/toolsets。

    每项返回：
      name / label / purpose            工具集名、中文名、一句话用途
      available / configured            依赖与凭证是否齐备（check_fn 通过）
      enabled                           用户启用意图（非架构禁用且未被用户手动禁用），与 available 独立
      disabled                          当前是否处于禁用态（架构禁用 或 用户手动禁用）
      arch_disabled                     是否被架构显式禁用（terminal，不可由用户切换）
      tools: [{name, disabled}]         该工具集下的工具（含单工具级禁用初始态）
      requirements                      缺失的环境变量/依赖（available=False 时的提示）
      display_only_tools_note           内核 0.19.0 仅支持工具集级启停，工具列表为只读展示
    """
    register_pure_python_tools()
    from tools.registry import registry  # noqa: F401  (触发注册副作用，保持原语义)
    from hermes_config import get_hermes_home, read_config_yaml

    _tool_env()
    home = get_hermes_home()
    agent_cfg = (read_config_yaml(home).get("agent", {}) or {})
    disabled_tools = set(agent_cfg.get("disabled_tools", []) or [])
    user_disabled_ts = set(agent_cfg.get("disabled_toolsets", []) or [])
    arch_set = set(DISABLED_TOOLSETS)
    cfg_env = dict(agent_cfg.get("env") or {})
    matrix = get_toolset_matrix() or {}
    out: list[dict] = []
    for name in sorted(matrix.keys()):
        info = matrix.get(name) or {}
        spec = get_spec(name)
        available = bool(info.get("available"))
        # 运行时环境检查：模块可加载(available) ≠ 运行配置就绪
        # 对有已知 env 要求的工具集，检查至少一个所需环境变量已设置
        _env_required = list(spec.env) if spec else []
        _env_set = [v for v in _env_required if os.environ.get(v) or cfg_env.get(v)]
        env_configured = len(_env_required) == 0 or len(_env_set) > 0
        arch_disabled = name in arch_set
        user_dis = name in user_disabled_ts
        is_disabled = arch_disabled or user_dis
        if spec is not None:
            label = spec.label or name
            purpose = spec.purpose
        else:
            label, purpose = name, info.get("description") or ""
        req = list(info.get("requirements") or [])
        # 合并运行时环境变量到 requirements，使前端"配置"弹窗显示输入框
        if _env_required:
            for v in _env_required:
                if v not in req:
                    req.append(v)
        # 诊断未配置原因：有缺失 env 则列出；否则查运行时环境提示
        reason = ""
        if not available:
            missing = [v for v in req if not os.environ.get(v)]
            if missing:
                reason = "缺少配置：" + ", ".join(missing)
            else:
                hint = spec.runtime_hint if spec else ""
                if hint:
                    reason = hint
                else:
                    reason = "依赖运行环境/专用服务未就绪，点「测试」查看详情"
        elif not env_configured:
            missing_env = [v for v in _env_required if not (os.environ.get(v) or cfg_env.get(v))]
            reason = "缺少运行时配置：" + ", ".join(missing_env[:5])
            if len(missing_env) > 5:
                reason += " 等" + str(len(missing_env)) + "个"
        tool_names = list(info.get("tools") or [])
        tools_out = [{"name": tn, "disabled": tn in disabled_tools} for tn in tool_names]
        # 附加运行时环境提示（模块可加载但缺运行时配置时也显示）
        runtime_hint = (spec.runtime_hint if spec else "") if (not available) or (available and not env_configured) else ""
        # 上次测试结果（模块级缓存，带5分钟TTL #8）
        _last_test = _last_test_results.get(name)
        last_test = None
        if _last_test:
            import time as _t
            if _t.time() - (_last_test.get("ts") or 0) < 300:  # 5分钟TTL
                last_test = _last_test

        out.append({
            "name": name, "label": label, "purpose": purpose,
            "available": available, "configured": env_configured,
            "enabled": (not arch_disabled) and (not user_dis), "disabled": is_disabled,
            "arch_disabled": arch_disabled,
            "tools": tools_out,
            "requirements": req,
            "reason": reason,
            "runtime_hint": runtime_hint,
            "last_test": last_test,
            "configured_env": _env_set,
            "category": (spec.category if spec else "🔧 其他"),
            "dangerous": name in DANGEROUS_TOOLSETS,
            # 内核 0.19.0 仅支持工具集级启停（AIAgent 只接受 disabled_toolsets）；
            # 工具列表供只读展示与未来内核支持后的开关预留。
            "tools_readonly_note": "内核 0.19.0 仅支持工具集级启停，工具明细为只读展示",
        })
    return out


def configure_toolset(name: str, values: dict) -> dict:
    """保存工具集依赖配置（API Key 等）到 config.yaml 的 agent.env，并即时生效。

    传空字符串的值会从配置中移除。保存后失效 check_fn 缓存，available 实时重查。
    """
    from hermes_config import get_hermes_home, read_config_yaml, update_config_yaml
    from tools.registry import invalidate_check_fn_cache
    home = get_hermes_home()
    cfg = read_config_yaml(home)
    agent = cfg.get("agent") or {}
    env = dict(agent.get("env") or {})
    changed = False
    removed: list[str] = []
    for k, v in (values or {}).items():
        k = str(k).strip()
        if not k:
            continue
        v = str(v or "").strip()
        if v:
            if env.get(k) != v:
                env[k] = v
                changed = True
        else:
            if k in env:
                del env[k]
                removed.append(k)
                changed = True
    if changed:
        agent["env"] = env
        # 统一用 update_config_yaml（深合并），与 set_toolset_disabled 保持同一条写入路径
        full = read_config_yaml(home)
        full.setdefault("agent", {})
        if env:
            full["agent"]["env"] = env
        else:
            full["agent"].pop("env", None)
        update_config_yaml(home, full)
        # 同步环境变量：新增/更新注入，移除项从 os.environ 清理（仅本次移除的）
        for k, v in env.items():
            os.environ[k] = str(v)
        for k in removed:
            os.environ.pop(k, None)
        invalidate_check_fn_cache()
    invalidate_toolset_cache()
    return {"ok": True, "name": name, "env": env}


def test_toolset(name: str) -> dict:
    """配置诊断级测试：逐项检查依赖，返回详细报告（每项是否设置 + check_fn 结果 + 运行时探测）。

    结果缓存到 _last_test_results 供 discover_toolsets 的 last_test 字段使用。
    运行时探测走声明式 run_probes（spec 驱动），替代原 250 行 if/elif 链。
    """
    _tool_env()  # 确保 config.yaml 中的 env 已注入 os.environ
    from tools.registry import registry
    check = None
    env_vars: list[str] = []
    try:
        reqs = registry.get_toolset_requirements()
        info = reqs.get(name, {}) or {}
        check = info.get("check_fn")
        env_vars = list(info.get("env_vars") or [])
    except Exception:  # noqa: BLE001
        pass
    checks = [{"var": v, "set": bool(os.environ.get(v))} for v in env_vars]
    missing = [v for v in env_vars if not os.environ.get(v)]

    # 运行时探测（声明式：spec.probe_env + spec.probe_fn）
    runtime_checks, runtime_detail = run_probes(name)

    avail = False
    reason = ""
    detail = ""
    if missing:
        reason = "缺少配置：" + ", ".join(missing)
        detail = "以下环境变量未设置，导致依赖判定不满足：\n" + "\n".join(
            "  - %s：未设置" % v for v in missing)
    elif check is not None:
        # 尝试获取 check_fn 的更多诊断信息
        check_fn_detail = ""
        try:
            # 先尝试用标准方式调用
            avail = bool(check())
        except Exception as e:  # noqa: BLE001
            import traceback as _tb
            reason = "依赖检测异常：%s" % e
            detail = "check_fn 抛出异常：%s\n%s" % (e, _tb.format_exc())
            avail = False
        else:
            if not avail:
                reason = "环境校验未通过"
                detail_parts = ["环境变量已齐备，但环境校验（check_fn）未通过。"]
                if runtime_detail:
                    detail_parts.append(runtime_detail)
                # 尝试获取更具体的失败原因：对已知工具集添加额外探测
                try:
                    # 再次调用 check_fn 但捕获其 stderr 输出（很多 check_fn 内部有 print/log）
                    import io as _io
                    import sys as _sys
                    _stderr_capture = _io.StringIO()
                    _old_stderr = _sys.stderr
                    _sys.stderr = _stderr_capture
                    try:
                        check()
                    except Exception:
                        pass
                    finally:
                        _sys.stderr = _old_stderr
                    _captured = _stderr_capture.getvalue().strip()
                    if _captured:
                        check_fn_detail = _captured[:500]
                except Exception:
                    pass
                if check_fn_detail:
                    detail_parts.append("check_fn 内部诊断：" + check_fn_detail)
                detail_parts.append("点击「试用」实际调用可看到真实错误信息。")
                detail = "\n".join(detail_parts)
            else:
                detail = "所有依赖检查通过，工具集可用。"
                if runtime_detail:
                    detail += "\n" + runtime_detail
    else:
        avail = True
        detail = "无环境变量依赖，工具集可用。"
        if runtime_detail:
            detail += "\n" + runtime_detail

    # 合并常规检查与运行时探测
    all_checks = checks + runtime_checks

    result = {"ok": True, "name": name, "available": avail,
              "missing": missing, "reason": reason, "detail": detail,
              "checks": all_checks}
    # 缓存测试结果（模块级，进程内持久化）
    _last_test_results[name] = {
        "available": avail,
        "reason": reason,
        "detail": detail[:200],
        "checks": all_checks,
        "ts": __import__("time").time(),
    }
    invalidate_toolset_cache()
    return result


_TOOLSET_CFG_LOCK = threading.Lock()

def set_toolset_disabled(toolset_name: str, disabled: bool) -> dict:
    """工具集级开关：写 config.yaml 的 agent.disabled_toolsets（设置中心开关用）。

    与 discover_toolsets / _resolve_disabled_toolsets 保持一致：这里持久化的是
    **工具集名**，真正决定 Agent 生效状态的是合并架构禁用后的 disabled_toolsets。
    使用线程锁防止高频切换导致的 race condition（#15）。
    """
    from hermes_config import get_hermes_home, read_config_yaml, update_config_yaml

    with _TOOLSET_CFG_LOCK:
        home = get_hermes_home()
        cfg = read_config_yaml(home)
        agent = cfg.get("agent") or {}
        cur = list(agent.get("disabled_toolsets") or [])
        if disabled and toolset_name not in cur:
            cur.append(toolset_name)
        elif not disabled and toolset_name in cur:
            cur = [t for t in cur if t != toolset_name]
        agent["disabled_toolsets"] = cur
        update_config_yaml(home, {"agent": agent})
    invalidate_toolset_cache()
    return {"ok": True, "tool": toolset_name, "disabled": disabled,
            "disabled_toolsets": cur}


def set_toolset_profile(disabled_list: list[str]) -> dict:
    """场景预设应用：一次性整体写入 disabled_toolsets（与逐个 toggle 同一把锁）。

    传入的是**最终禁用名单**（架构禁用项由调用方保证不混入）。
    """
    from hermes_config import get_hermes_home, read_config_yaml, update_config_yaml

    with _TOOLSET_CFG_LOCK:
        home = get_hermes_home()
        cfg = read_config_yaml(home)
        agent = cfg.get("agent") or {}
        cur = list(dict.fromkeys(disabled_list or []))
        agent["disabled_toolsets"] = cur
        update_config_yaml(home, {"agent": agent})
    invalidate_toolset_cache()
    return {"ok": True, "disabled_toolsets": cur}


# ============================================================================
# 8) 审批命令执行（纯 Python 进程内删除，无 shell / 无 Git Bash）
# ============================================================================
def execute_approved_command(cmd: str, timeout: int = 120) -> dict:
    """审批弹窗「批准执行」与 HTTP 桥接共用的命令执行器。

    Library 模式已禁用 terminal 工具集，本环境**不支持任何 shell 命令执行**。因此这里
    不 shell out，而是识别删除类命令（rm -rf / rmdir / del / remove / delete + 路径）后，
    用纯 Python（pathlib / shutil）在进程内安全删除——跨平台、零 shell 依赖，天然规避
    Windows 下 `rm` 不存在 / 缺 Git Bash 导致执行失败的问题。

    命令字符串来自本系统自己生成的 [APPROVAL_REQUIRED] 标记、且经用户在弹窗中显式确认，
    属于已授权行为。仅支持文件/目录删除；其余命令一律拒绝（符合无终端架构）。

    `timeout` 保留以兼容 pywebview 调用约定（纯 Python 删除为同步、瞬时操作）。
    """
    import re as _re
    import shutil as _shutil
    from pathlib import Path as _Path

    raw = (cmd or "").strip()
    if not raw:
        return {"ok": False, "error": "命令为空", "command": cmd}

    if not _re.search(
        r"(?:^|[\s(])(?:rm\s+-[rf]+|rmdir|del|rm|remove|delete)\b", raw, _re.I
    ):
        return {"ok": False, "command": cmd,
                "error": "本环境不支持 shell 命令执行；仅支持文件/目录删除操作。"}

    candidates: list[str] = []
    for grp in _re.findall(r'"([^"]+)"|\'([^\']+)\'|(\S+)', raw):
        candidates.append(grp[0] or grp[1] or grp[2])
    _skip = {"rm", "-rf", "-r", "-f", "rmdir", "/s", "/q", "del",
             "remove", "delete", "/c", "/k"}
    targets = [c for c in candidates
               if c.lower() not in _skip and not c.startswith("-")]
    if not targets:
        return {"ok": False, "error": "未能从命令中解析出待删除路径", "command": cmd}

    results: list[str] = []
    overall_ok = True
    for t in targets:
        p = _Path(t).expanduser()
        if not p.exists():
            results.append(f"{t}：不存在（跳过）")
            continue
        try:
            if p.is_dir():
                _shutil.rmtree(p, ignore_errors=False)
            else:
                p.unlink()
            results.append(f"{t}：已删除")
        except Exception as _e:  # noqa: BLE001
            overall_ok = False
            results.append(f"{t}：删除失败 - {_e}")

    return {"ok": overall_ok, "rc": 0 if overall_ok else 1,
            "stdout": "\n".join(results), "stderr": "", "command": cmd}


# 审批闭环：Agent 在回答里写 [APPROVAL_REQUIRED: cmd] 即触发前端弹窗。
# A1 优化：正则模块级编译一次，流式热路径每条 chunk 调用本函数时不再重复编译。
_APPROVAL_RE = re.compile(r"\[APPROVAL_REQUIRED:\s*(.+?)\]")


def extract_approval(text: str) -> "str | None":
    """从助手文本里提取待审批命令（供 main.py 渲染审批弹窗）。

    正则已在模块级编译一次（A1 优化）：流式热路径每条 chunk 调用本函数时
    仅做一次 O(text) 匹配，不再重复编译同一正则。
    """
    m = re.search(_APPROVAL_RE, text or "")
    return m.group(1).strip() if m else None
