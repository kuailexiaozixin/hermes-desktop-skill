from routes import _err, _guard, _ok, app, ar, hc, sessions, we
# ---------------------------------------------------------------------------
@app.post("/api/conversations/{cid}/usage")
async def api_conv_usage(cid: str, req):
    """接收前端对单会话的累计 token 用量估算（覆盖式），供聚合分析。"""
    body = await req.json()
    return sessions.set_usage(cid, int(body.get("input") or 0),
                              int(body.get("output") or 0), body.get("model"))


@app.get("/api/analytics")
def api_analytics(days: int = 30):
    return sessions.analytics(days)


# ---------------------------------------------------------------------------
# 设置中心 · 模型
# ---------------------------------------------------------------------------
@app.get("/api/models")
def api_models():
    """已配置模型 + 36 家厂商预设（预设里不含任何密钥）。"""
    cfg = hc.get_llm_config()
    presets = {
        k: {"label": v.get("label"), "provider": v.get("provider"),
            "base_url": v.get("base_url"), "models": list(v.get("models") or []),
            "env": v.get("env"), "note": v.get("note"), "auth": v.get("auth")}
        for k, v in hc.VENDOR_PRESETS.items()
    }
    # DeepSeek 新端点（无 /v1 后缀），用户可 base_url 下拉切换
    if "deepseek" in presets:
        presets["deepseek"]["base_url"] = "https://api.deepseek.com"
        presets["deepseek"]["alt_base_urls"] = [
            "https://api.deepseek.com",
            "https://api.deepseek.com/anthropic",
        ]
    items = []
    for m in hc.get_models_list(cfg):
        d = dict(m)
        d["has_key"] = bool(d.pop("api_key", ""))      # 不把密钥回传给前端
        items.append(d)
    return _ok(items=items, active=(cfg or {}).get("model"),
               vendors=presets, web=_guard(hc.get_web_search_status))


@app.post("/api/models")
async def api_models_save(req):
    """整体保存模型列表。前端传 api_key="" 表示「保持原密钥不变」。"""
    body = await req.json()
    incoming = body.get("items") or []
    active = body.get("active") or None
    old = {m.get("id"): m for m in hc.get_models_list()}
    merged = []
    for m in incoming:
        mid = m.get("id") or m.get("model")
        key = m.get("api_key") or ""
        if not key and mid in old:
            key = old[mid].get("api_key") or ""        # 保留既有密钥
        entry = dict(m)                                 # 保留逐模型参数（温度/Top-P/…）
        entry["id"] = mid
        entry["api_key"] = key
        merged.append(entry)
    return _guard(hc.save_models_list, merged, active)


@app.post("/api/models/upsert")
async def api_models_upsert(req):
    """增量保存单个模型（按 id 新增/更新），避免前端全量提交。
    api_key="" 表示「保持原密钥不变」；set_active=true 时把该模型设为当前活跃模型。"""
    body = await req.json()
    m = body.get("model") or {}
    mid = m.get("id") or m.get("model")
    if not mid:
        return _err("缺少模型 id")
    cfg = hc.get_llm_config()
    cur = hc.get_models_list(cfg)
    old = {x.get("id"): x for x in cur}
    key = m.get("api_key") or ""
    if not key and mid in old:
        key = old[mid].get("api_key") or ""
    entry = {
        "id": mid, "vendor": m.get("vendor") or "", "model": m.get("model") or "",
        "base_url": m.get("base_url") or "", "api_key": key,
    }
    if m.get("max_tokens"):
        try:
            mt = int(m["max_tokens"])
            if mt > 0: entry["max_tokens"] = mt
        except (TypeError, ValueError):
            pass
    if m.get("reasoning_effort"):
        entry["reasoning_effort"] = m["reasoning_effort"]
    # 模型能力字段
    for cap in ("tools", "vision", "thinking", "custom_protocol"):
        if cap in m:
            entry[cap] = bool(m[cap])
    if m.get("input_max_tokens"):
        try:
            entry["input_max_tokens"] = int(m["input_max_tokens"])
        except (TypeError, ValueError):
            pass
    if m.get("output_max_tokens"):
        try:
            entry["output_max_tokens"] = int(m["output_max_tokens"])
        except (TypeError, ValueError):
            pass
    # DeepSeek 高级参数
    for float_field in ("temperature", "top_p"):
        if m.get(float_field):
            try:
                entry[float_field] = float(m[float_field])
            except (TypeError, ValueError):
                pass
    if m.get("top_logprobs"):
        try:
            entry["top_logprobs"] = int(m["top_logprobs"])
        except (TypeError, ValueError):
            pass
    if m.get("stop_sequences"):
        entry["stop_sequences"] = str(m["stop_sequences"])
    if m.get("response_format"):
        entry["response_format"] = str(m["response_format"])
    if "web_search" in m:
        entry["web_search"] = bool(m["web_search"])
    idx = next((i for i, x in enumerate(cur) if x.get("id") == mid), -1)
    if idx >= 0:
        cur[idx] = entry
    else:
        cur.append(entry)
    active = (cfg or {}).get("model")
    if body.get("set_active"):
        active = mid
    elif active == mid or (active is None and idx == 0):
        active = mid
    return _guard(hc.save_models_list, cur, active)


@app.post("/api/models/remove")
async def api_models_remove(req):
    """按 id 删除单个模型（增量删除，不再全量提交）。"""
    body = await req.json()
    mid = body.get("id")
    if not mid:
        return _err("缺少模型 id")
    cfg = hc.get_llm_config()
    cur = [x for x in hc.get_models_list(cfg) if x.get("id") != mid]
    active = (cfg or {}).get("model")
    if active == mid:
        active = cur[0]["id"] if cur else None
    return _guard(hc.save_models_list, cur, active)


@app.post("/api/models/test")
async def api_models_test(req):
    """轻量连通性测试：用给定 provider 信息发一次最小请求，验证密钥与可达性（对标 Hermes Studio）。"""
    body = await req.json()
    vendor = body.get("vendor") or ""
    base_url = (body.get("base_url") or "").strip()
    api_key = (body.get("api_key") or "").strip()
    model = (body.get("model") or "").strip()
    # 前端不持有明文密钥（已转 has_key 布尔），从配置中按 model ID 查找
    if not api_key and model:
        _cfg = hc.get_llm_config()
        for _m in hc.get_models_list(_cfg):
            if _m.get("id") == model:
                api_key = _m.get("api_key", "") or ""
                break
    preset = (hc.VENDOR_PRESETS.get(vendor) or {})
    base_url = base_url or (preset.get("base_url") or "")
    if not base_url:
        return _err("缺少 base_url（无法测试）")
    try:
        import openai  # hermes-agent 的依赖，通常已随 venv 安装
    except ImportError:
        return _err("openai 未安装，无法执行连通性测试")
    try:
        client = openai.OpenAI(api_key=api_key or "dummy", base_url=base_url, timeout=12, max_retries=0)
        try:
            client.models.list()
            return _ok(detail="models.list 成功（鉴权与可达性正常）")
        except openai.AuthenticationError:
            return _ok(ok=False, detail="鉴权失败：API Key 无效")
        except Exception as e:  # noqa: BLE001
            if model:
                try:
                    client.chat.completions.create(model=model, messages=[{"role": "user", "content": "hi"}],
                                                    max_tokens=1, timeout=12)
                    return _ok(detail="chat 探针成功（鉴权与可达性正常）")
                except openai.AuthenticationError:
                    return _ok(ok=False, detail="鉴权失败：API Key 无效")
                except Exception as e2:  # noqa: BLE001
                    return _ok(ok=False, detail=f"chat 探针失败：{type(e2).__name__}: {e2}")
            return _ok(ok=False, detail=f"models.list 失败：{type(e).__name__}: {e}")
    except Exception as e:  # noqa: BLE001
        return _ok(ok=False, detail=f"{type(e).__name__}: {e}")


@app.post("/api/models/detect")
async def api_models_detect(req):
    """一键检测可用模型：调用 OpenAI /v1/models 端点，返回模型 ID 列表。"""
    body = await req.json()
    base_url = (body.get("base_url") or "").strip()
    api_key = (body.get("api_key") or "").strip()
    if not base_url:
        return _err("缺少 base_url")
    if not api_key:
        return _err("缺少 API Key")
    try:
        import openai
    except ImportError:
        return _err("openai 未安装")
    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=15, max_retries=0)
        resp = client.models.list()
        models = sorted([m.id for m in resp.data])
        return _ok(models=models, count=len(models))
    except openai.AuthenticationError:
        return _ok(ok=False, error="鉴权失败：API Key 无效")
    except openai.NotFoundError:
        return _ok(ok=False, error="端点不支持 models.list，请手动填写模型名")
    except Exception as e:
        return _ok(ok=False, error=f"{type(e).__name__}: {e}")





# 各厂商/协议支持的模型工具类型（非 Hermes 系统工具，而是模型本身支持的工具能力）
_MODEL_TOOL_CAPABILITIES = {
    "deepseek": {
        "label": "DeepSeek",
        "tools": [
            {"id": "function_call", "name": "函数调用", "supported": True},
            {"id": "web_search", "name": "内置联网搜索", "supported": True},
            {"id": "custom_tool_call", "name": "自定义工具调用（apply_patch）", "supported": True},
            {"id": "file_search", "name": "文件搜索", "supported": False},
            {"id": "code_interpreter", "name": "代码解释器", "supported": False},
            {"id": "computer_use", "name": "计算机使用", "supported": False},
        ]
    },
    "openai": {
        "label": "OpenAI",
        "tools": [
            {"id": "function_call", "name": "函数调用", "supported": True},
            {"id": "web_search", "name": "内置联网搜索", "supported": False},
            {"id": "file_search", "name": "文件搜索", "supported": True},
            {"id": "code_interpreter", "name": "代码解释器", "supported": True},
            {"id": "computer_use", "name": "计算机使用", "supported": False},
        ]
    },
    "anthropic": {
        "label": "Anthropic",
        "tools": [
            {"id": "tool_use", "name": "工具调用", "supported": True},
            {"id": "web_search", "name": "内置联网搜索", "supported": True},
            {"id": "computer_use", "name": "计算机使用", "supported": True},
        ]
    },
    "gemini": {
        "label": "Google Gemini",
        "tools": [
            {"id": "function_call", "name": "函数调用", "supported": True},
            {"id": "web_search", "name": "内置联网搜索", "supported": True},
            {"id": "code_execution", "name": "代码执行", "supported": True},
        ]
    },
}


def _get_model_tool_capabilities(base_url: str, vendor: str = "") -> list:
    """根据 base_url 和 vendor 判断模型所属协议，返回支持的工类型列表。"""
    url_lower = base_url.lower()
    # Anthropic 协议
    if "anthropic" in url_lower or vendor in ("anthropic", "minimax", "minimax-cn"):
        caps = _MODEL_TOOL_CAPABILITIES.get("anthropic", {})
        return caps.get("tools", [])
    # DeepSeek
    if "deepseek" in url_lower or vendor == "deepseek":
        caps = _MODEL_TOOL_CAPABILITIES.get("deepseek", {})
        return caps.get("tools", [])
    # Gemini
    if "googleapis" in url_lower or "gemini" in url_lower or vendor == "gemini":
        caps = _MODEL_TOOL_CAPABILITIES.get("gemini", {})
        return caps.get("tools", [])
    # 默认 OpenAI 兼容
    caps = _MODEL_TOOL_CAPABILITIES.get("openai", {})
    return caps.get("tools", [])


@app.post("/api/models/check-capabilities")
async def api_models_check_capabilities(req):
    """检测模型能力：用最小请求试探模型是否支持 vision / tool calling。"""
    body = await req.json()
    base_url = (body.get("base_url") or "").strip()
    api_key = (body.get("api_key") or "").strip()
    model = (body.get("model") or "").strip()
    if not base_url or not model:
        return _ok(ok=False, error="缺少 base_url 或 model")
    try:
        import openai
    except ImportError:
        return _ok(ok=False, error="openai 未安装")

    result = {"vision": False, "tools": False}
    client = openai.OpenAI(api_key=api_key or "dummy", base_url=base_url, timeout=10, max_retries=0)

    # 检测 vision：用 1x1 像素 base64 图片试探
    if api_key:
        try:
            tiny_img = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": "describe"},
                    {"type": "image_url", "image_url": {"url": tiny_img, "detail": "low"}}
                ]}],
                max_tokens=1, timeout=8)
            if resp and resp.choices:
                result["vision"] = True
        except openai.BadRequestError:
            pass
        except Exception:
            pass

    # 检测 tool calling：用简单工具定义试探
    if api_key:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                tools=[{"type": "function", "function": {"name": "ping", "description": "test", "parameters": {"type": "object", "properties": {}}}}],
                max_tokens=1, timeout=8)
            if resp and resp.choices:
                result["tools"] = True
        except openai.BadRequestError:
            pass
        except Exception:
            pass

    # 获取模型工具类型列表
    vendor = body.get("vendor", "")
    result["tool_capabilities"] = _get_model_tool_capabilities(base_url, vendor)
    return _ok(**result)

# ---------------------------------------------------------------------------
