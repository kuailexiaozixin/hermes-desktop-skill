"""routes/structured.py — Hermes 结构化输出（触发 + 离线校验）

对齐真实 Hermes Library 的结构化输出能力（实探 agent/plugin_llm.py +
agent/auxiliary_client.py）：

- 进程内 host-owned 结构化补全：
    agent.plugin_llm.PluginLLM.complete_structured(instructions, input,
    json_schema, json_mode) —— 背后就是把 response_format 设成
    json_schema / json_object，再由模型返回 JSON，最后用 jsonschema 校验。
    本示例并非插件，因此通过 agent.auxiliary_client.get_text_auxiliary_client
    取得「host-owned」的 OpenAI 兼容客户端（provider / 认证由 Hermes 托管，
    本示例拿不到任何密钥），再以**完全相同**的 response_format + 系统提示词
    约束来触发结构化输出，从而忠实复刻 Library 行为。
- 离线 JSON Schema 校验：把一段 JSON 按可选 schema 校验，纯本地、无需联网。

安全边界：
- 只调用 host-owned 客户端；绝不持有、打印、落盘任何密钥 / API Key。
- 只读取模型输出，不写盘、不改配置、不碰 .hermes_data。
- 模型未配置 / 认证缺失时优雅降级，给出明确提示，绝不抛 500。
- 所有异常都被 _guard 包成 {ok:false, error:...} 回显前端。
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Optional, Tuple

from routes import _err, _ok, _guard, app


# ── JSON 解析 / 校验（对齐 agent/plugin_llm._parse_structured_text）───────
# 模型有时会用 ```json ... ``` 包裹结果，先剥离代码围栏再 json.loads。
_FENCE_RE = re.compile(r"```(?:json)?\s*(.+?)```", re.DOTALL | re.IGNORECASE)


def _strip_code_fences(text: str) -> str:
    """抽出第一个 fenced code block；无围栏则原样返回。"""
    if not text:
        return ""
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


def _validate_against_schema(parsed: Any, schema: dict) -> Tuple[bool, Optional[str]]:
    """用可选 jsonschema 校验。无 schema → 视为通过；jsonschema 缺失 → 跳过校验。"""
    if schema is None:
        return True, None
    try:
        import jsonschema  # type: ignore[import-untyped]
        jsonschema.validate(parsed, schema)
        return True, None
    except ImportError:
        # jsonschema 是可选依赖：缺失时只做 JSON 解析（已通过），跳过严格校验。
        return True, None
    except Exception as e:  # noqa: BLE001  (jsonschema.ValidationError 也是 Exception)
        return False, f"{type(e).__name__}: {e}"


def _parse_and_validate(text: str, schema: Optional[dict]
                        ) -> Tuple[Optional[Any], str, Optional[str]]:
    """返回 (parsed, content_type, validation_error)。

    content_type: 'json' 表示解析成功且（若有 schema）校验通过；
                  'text' 表示不是合法 JSON。
    validation_error: 仅当 schema 校验失败时非空。
    """
    if not text:
        return None, "text", None
    try:
        parsed = json.loads(_strip_code_fences(text))
    except (json.JSONDecodeError, ValueError) as e:
        return None, "text", f"JSON 解析失败：{e}"
    ok, verr = _validate_against_schema(parsed, schema)
    if not ok:
        # 解析成功但 schema 校验失败：仍回传 parsed 供前端展示，并标出错误。
        return parsed, "json", verr
    return parsed, "json", None


# ── 消息构建（对齐 agent/plugin_llm._build_structured_messages）────────────
def _build_structured_messages(*, instructions: str, input_text: str,
                               json_mode: bool, json_schema: Optional[dict],
                               schema_name: Optional[str],
                               system_prompt: Optional[str]) -> list:
    messages: list = []
    sys_parts: list = []
    if system_prompt:
        sys_parts.append(system_prompt.strip())
    if json_mode or json_schema is not None:
        sys_parts.append(
            "Respond with a single JSON object that matches the requested shape. "
            "Do not include prose or markdown fences."
        )
    if sys_parts:
        messages.append({"role": "system", "content": "\n\n".join(sys_parts)})

    header = instructions.strip()
    if schema_name:
        header = f"{header}\n\nSchema name: {schema_name}"
    if json_schema is not None:
        try:
            schema_text = json.dumps(json_schema, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            schema_text = str(json_schema)
        header = f"{header}\n\nJSON schema:\n{schema_text}"

    user_parts: list = [{"type": "text", "text": header}]
    if input_text and input_text.strip():
        user_parts.append({"type": "text", "text": input_text.strip()})
    messages.append({"role": "user", "content": user_parts})
    return messages


# ── response_format 构建（对齐 agent/plugin_llm._json_response_format）─────
def _json_response_format(*, json_mode: bool,
                          json_schema: Optional[dict]) -> Optional[dict]:
    """拼出 extra_body 的 response_format。无 schema 时退回 json_object，
    让不识别 json_schema 的 provider 也能收到「请输出 JSON」的暗示。"""
    if json_schema is not None:
        return {
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "plugin_structured_output",
                    "schema": json_schema,
                    "strict": False,
                },
            }
        }
    if json_mode:
        return {"response_format": {"type": "json_object"}}
    return None


# ── 业务函数（供 _guard 包装）────────────────────────────────────────────
def _validate_only(json_text: str, schema_text: str) -> dict:
    """离线校验：把 JSON 文本按可选 schema 校验（纯本地，无需联网）。"""
    schema: Optional[dict] = None
    if schema_text and schema_text.strip():
        try:
            schema = json.loads(_strip_code_fences(schema_text))
        except (json.JSONDecodeError, ValueError) as e:
            return _err(f"JSON Schema 解析失败：{e}")
        if not isinstance(schema, dict):
            return _err("JSON Schema 必须是一个对象（含 type/properties 等字段）。")
    parsed, content_type, verr = _parse_and_validate(json_text, schema)
    if content_type == "text":
        return _ok(valid=False, content_type="text",
                   error=verr or "不是合法 JSON。", text=json_text,
                   note="校验仅在输入为合法 JSON 时才有意义。")
    return _ok(valid=(verr is None), content_type="json", parsed=parsed,
               validation_ok=(verr is None), validation_error=verr,
               text=json_text,
               note="已做 JSON 解析" + ("及 JSON Schema 校验。" if schema is not None
                                         else "（未提供 schema，仅做 JSON 解析）。"))


def _run_structured_sync(*, instructions: str, input_text: str,
                         json_schema: Optional[dict], json_mode: bool,
                         schema_name: Optional[str], system_prompt: Optional[str],
                         temperature: Optional[float],
                         max_tokens: Optional[int]) -> dict:
    """触发 host-owned 结构化补全（同步、可能被 to_thread 包裹）。"""
    try:
        from agent.auxiliary_client import get_text_auxiliary_client
    except Exception as e:  # noqa: BLE001
        return _err(f"Hermes 内核不可用（无法导入 agent.auxiliary_client）：{e}")

    try:
        client, model = get_text_auxiliary_client("")
    except Exception as e:  # noqa: BLE001
        return _err(f"解析 host-owned 客户端失败：{type(e).__name__}: {e}")

    if client is None or not model:
        return _ok(
            available=False,
            error="未配置可用的模型或认证。请先在 Hermes 中完成「模型 + 认证」设置，"
                  "再使用结构化输出。",
            note="结构化输出由 Hermes 托管的 host-owned 客户端执行，需要有效的模型配置。",
        )

    messages = _build_structured_messages(
        instructions=instructions, input_text=input_text,
        json_mode=json_mode, json_schema=json_schema,
        schema_name=schema_name, system_prompt=system_prompt,
    )
    extra_body = _json_response_format(json_mode=json_mode, json_schema=json_schema)

    try:
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature if temperature is not None else 0.2,
            "max_tokens": max_tokens or 2000,
        }
        if extra_body:
            kwargs["extra_body"] = extra_body
        resp = client.chat.completions.create(**kwargs)
        text = (resp.choices[0].message.content or "") if getattr(resp, "choices", None) else ""
    except Exception as e:  # noqa: BLE001
        return _err(f"模型调用失败：{type(e).__name__}: {e}")

    parsed, content_type, verr = _parse_and_validate(text, json_schema)
    return _ok(
        available=True,
        model=model,
        text=text,
        parsed=parsed,
        content_type=content_type,
        validation_ok=(verr is None),
        validation_error=verr,
        note="若模型不支持 response_format，已用系统提示词兜底要求输出 JSON；"
             "输出格式仍以模型实际返回为准。",
    )


# ── 路由 ────────────────────────────────────────────────────────────────
@app.post("/api/structured/run")
async def api_structured_run(req):
    """触发一次结构化补全：把指令 +（可选）输入 +（可选）JSON Schema 交给
    host-owned 模型，返回原始文本 / 解析后的 JSON / 校验结果。"""
    body = await req.json()
    instructions = (body.get("instructions") or "").strip()
    if not instructions:
        return _err("指令(instructions)不能为空。")
    input_text = (body.get("input") or "")
    schema_text = (body.get("schema") or "")
    schema_name = (body.get("schema_name") or "").strip() or None
    system_prompt = (body.get("system_prompt") or "").strip() or None
    json_mode = bool(body.get("json_mode"))

    schema: Optional[dict] = None
    if schema_text and schema_text.strip():
        try:
            schema = json.loads(_strip_code_fences(schema_text))
        except (json.JSONDecodeError, ValueError) as e:
            return _err(f"JSON Schema 解析失败：{e}")
        json_mode = True  # 提供 schema 即视为结构化

    temp = body.get("temperature")
    maxt = body.get("max_tokens")
    temperature = float(temp) if temp not in (None, "") else None
    max_tokens = int(maxt) if maxt not in (None, "") else None

    return await asyncio.to_thread(
        _guard,
        lambda: _run_structured_sync(
            instructions=instructions, input_text=input_text,
            json_schema=schema, json_mode=json_mode,
            schema_name=schema_name, system_prompt=system_prompt,
            temperature=temperature, max_tokens=max_tokens,
        ),
    )


@app.post("/api/structured/validate")
async def api_structured_validate(req):
    """离线校验：把一段 JSON 按可选 schema 校验，纯本地、无需联网。"""
    body = await req.json()
    json_text = body.get("json") or ""
    schema_text = body.get("schema") or ""
    return _guard(lambda: _validate_only(json_text, schema_text))
