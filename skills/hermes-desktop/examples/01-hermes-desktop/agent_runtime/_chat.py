from __future__ import annotations

import json
import os
import queue
import re
import threading
from typing import Any, Callable, Iterator
import file_tools
import host_tools

from ._tools import _CancelRequested, _render_html, _resolve_disabled_toolsets, _resolve_provider, register_pure_python_tools



def _build_request_overrides(model_cfg: dict) -> "dict | None":
    """把逐模型采样/格式参数归一成 AIAgent 的 ``request_overrides``。

    Hermes Library 的 ``AIAgent`` 只认透传字典 ``request_overrides``（见
    ``scripts/api-baseline.json:54``），不直接接收 ``temperature`` / ``top_p`` /
    ``stop`` / ``response_format``。本函数负责转换：

    - ``temperature`` / ``top_p`` / ``top_logprobs`` → 原样透传（OpenAI 兼容 provider 通用）；
    - ``stop_sequences``（逗号分隔字符串）→ ``stop``（列表）；
    - ``response_format``（``"json_object"``）→ ``{"type": "json_object"}``。

    仅当确有参数时返回 dict，否则返回 ``None``（不覆盖 AIAgent 默认行为）。
    """
    ro: dict = {}
    for f in ("temperature", "top_p"):
        v = model_cfg.get(f)
        if v not in (None, ""):
            try:
                ro[f] = float(v)
            except (TypeError, ValueError):
                pass
    if model_cfg.get("top_logprobs") not in (None, ""):
        try:
            ro["top_logprobs"] = int(model_cfg["top_logprobs"])
        except (TypeError, ValueError):
            pass
    s = model_cfg.get("stop_sequences")
    if s not in (None, ""):
        ro["stop"] = [x.strip() for x in str(s).split(",") if x.strip()]
    rf = model_cfg.get("response_format")
    if rf not in (None, ""):
        ro["response_format"] = {"type": str(rf)}
    return ro or None


def build_agent(model_cfg: dict, *,
                max_iterations: int | None = None,
                ephemeral_system_prompt: str | None = None,
                tool_start_callback: Callable | None = None,
                tool_complete_callback: Callable | None = None,
                reasoning_callback: Callable | None = None,
                tool_progress_callback: Callable | None = None,
                enabled_toolsets: list[str] | None = None,
                web_search: bool = True) -> Any:
    """根据模型配置构造进程内 AIAgent（terminal 已禁用）。

    web_search=True（默认）保留 web + browser 工具集，使 Agent 可联网检索；
    web_search=False 时禁用（离线模式，避免无意义的联网工具调用）。
    """
    register_pure_python_tools()
    from hermes_adapter import create_agent

    # 循环面板开关：记忆循环（Memory Loop）与目标循环（Goal 上下文）。默认关闭 →
    # skip_memory=True / skip_context_files=True；用户在「🔁 循环」面板开启后新会话生效。
    # ② 默认开启 Hermes 持久记忆（纯本地、零依赖、配置即开）
    _memory_on = True
    _goal_on = False
    try:
        from frameworks import get_loop_flags
        _flags = get_loop_flags()
        _memory_on = bool(_flags.get("memory_enabled"))
        _goal_on = bool(_flags.get("goal_enabled"))
    except Exception as _e:  # noqa: BLE001
        print("[build_agent] loop flags warn:", _e)
        # 兜底：从 config.yaml 的 [memory] 段读取
        try:
            from hermes_config import read_config_yaml
            _mem_cfg = (read_config_yaml().get("memory", {}) or {})
            _memory_on = bool(_mem_cfg.get("memory_enabled", True))
        except Exception:
            _memory_on = True  # Hermes 默认即开启

    # 需求3：Soul 人格开关 + 自定义系统提示词（从 config.yaml 读取，会话生效）
    _custom_sp = ""
    _soul_on = False
    try:
        from hermes_config import read_config_yaml
        _acfg = read_config_yaml().get("agent") or {}
        _custom_sp = (_acfg.get("system_prompt") or "").strip()
        _soul_on = bool(_acfg.get("soul_enabled"))
    except Exception:
        pass

    vendor = model_cfg.get("vendor") or "deepseek"
    provider = _resolve_provider(vendor)
    # MOA 虚拟 provider：构造前校验预设存在，缺失则降级到默认厂商，
    # 避免 AIAgent.__init__ 在 agent_init.py:816 分支解析 MoAClient 时抛 KeyError 使对话崩溃。
    _moa_failed = False
    if provider == "moa":
        try:
            from hermes_cli.config import load_config
            from hermes_cli.moa_config import resolve_moa_preset
            _preset = model_cfg.get("model") or "default"
            resolve_moa_preset(load_config().get("moa") or {}, _preset)  # KeyError → 预设不存在
        except KeyError:
            print(f"[build_agent] MoA 预设 '{model_cfg.get('model')}' 缺失，降级到 deepseek")
            vendor = "deepseek"
            provider = _resolve_provider(vendor)
            _moa_failed = True
        except Exception:
            pass
    # MoA 降级到 deepseek 后，model 字段仍可能是预设名（如 "default"），对 deepseek 无效 → 回退默认模型
    _model = "deepseek-chat" if _moa_failed else (model_cfg.get("model") or "deepseek-chat")
    kwargs: dict[str, Any] = dict(
        provider=provider,
        model=_model,
        # enabled_toolsets=None → Hermes 默认「全部工具集」（browser/computer_use/cron/
        # code_execution/memory/web/mcp…），与网关启动等价；只用 disabled 做减法剔除
        # terminal。**绝不硬编码 ["file"]**，否则上述能力会被全部砍掉（功能退化）。
        enabled_toolsets=enabled_toolsets,
        disabled_toolsets=_resolve_disabled_toolsets(web_search),
        quiet_mode=True,
        save_trajectories=False,
        skip_memory=not _memory_on,
        skip_context_files=not _goal_on,
        load_soul_identity=_soul_on,
    )
    if model_cfg.get("api_key"):
        kwargs["api_key"] = model_cfg["api_key"]
    if model_cfg.get("base_url"):
        kwargs["base_url"] = model_cfg["base_url"]
    if model_cfg.get("max_tokens"):
        try:
            kwargs["max_tokens"] = int(model_cfg["max_tokens"])
        except (TypeError, ValueError):
            pass
    rc = model_cfg.get("reasoning_config")
    if rc and isinstance(rc, dict):
        kwargs["reasoning_config"] = rc
    # 逐模型采样/格式参数：经 request_overrides 透传给底层 provider 请求
    # （AIAgent 不直接接收 temperature/top_p/stop/response_format，见 api-baseline.json:54）。
    _ro = _build_request_overrides(model_cfg)
    if _ro:
        kwargs["request_overrides"] = _ro
    if max_iterations:
        kwargs["max_iterations"] = int(max_iterations)
    if ephemeral_system_prompt:
        kwargs["ephemeral_system_prompt"] = ephemeral_system_prompt
    elif _custom_sp:
        kwargs["ephemeral_system_prompt"] = _custom_sp
    if tool_start_callback:
        kwargs["tool_start_callback"] = tool_start_callback
    if tool_complete_callback:
        kwargs["tool_complete_callback"] = tool_complete_callback
    if reasoning_callback:
        kwargs["reasoning_callback"] = reasoning_callback
    if tool_progress_callback:
        kwargs["tool_progress_callback"] = tool_progress_callback
    agent = create_agent(**kwargs)

    # ── 强制「工具调用护栏」对所有模型生效 ────────────────────────────────
    # Hermes 默认仅对硬编码名单 TOOL_USE_ENFORCEMENT_MODELS 内的模型注入
    # TOOL_USE_ENFORCEMENT_GUIDANCE（"真正调用工具、别只描述"，属 stable_parts 权重最高
    # 段）。免费/小模型多不在名单 → 表现为「只反问、只描述、不动手」。系统提示按请求构建
    # （system_prompt.build_system_prompt_parts 每轮读 agent._tool_use_enforcement），
    # 故在进程内 agent 上直接置 True 即可让护栏对当前所有模型生效。
    try:
        agent._tool_use_enforcement = True
    except Exception as _e:  # noqa: BLE001
        print("[build_agent] force tool_use_enforcement warn:", _e)

    # 单工具级禁用（工具集级禁用见 DISABLED_TOOLSETS）。config.yaml 的
    # agent.disabled_tools 列出需关闭的单个工具名；剔除后 agent.tools（OpenAI 格式）
    # 与 agent.valid_tool_names 同步收缩，对话循环据此不再把该工具交给模型。
    try:
        from hermes_config import get_hermes_home, read_config_yaml
        home = get_hermes_home()
        disabled_tools = set(
            (read_config_yaml(home).get("agent", {}) or {}).get("disabled_tools", []) or []
        )
        if disabled_tools:
            agent.tools = [
                t for t in (agent.tools or [])
                if (t.get("function", {}) or {}).get("name") not in disabled_tools
            ]
            if getattr(agent, "valid_tool_names", None):
                agent.valid_tool_names = {
                    n for n in agent.valid_tool_names if n not in disabled_tools
                }
    except Exception as _e:  # noqa: BLE001
        print("[build_agent] disabled_tools filter warn:", _e)

    return agent


def build_trial_agent(toolset_name: str, model_cfg: dict, *,
                      max_iterations: int | None = None,
                      ephemeral_system_prompt: str | None = None,
                      tool_start_callback: Callable | None = None,
                      tool_complete_callback: Callable | None = None,
                      reasoning_callback: Callable | None = None,
                      web_search: bool = True) -> Any:
    """试用专用 Agent 工厂：强制启用目标工具集，确保 trial 时模型能调用该工具。"""
    register_pure_python_tools()
    from hermes_adapter import create_agent
    from tools.registry import invalidate_check_fn_cache
    invalidate_check_fn_cache()

    vendor = model_cfg.get("vendor") or "deepseek"
    provider = _resolve_provider(vendor)
    # MOA 虚拟 provider：构造前校验预设存在，缺失则降级到默认厂商，
    # 避免 AIAgent.__init__ 在 agent_init.py:816 分支解析 MoAClient 时抛 KeyError 使对话崩溃。
    _moa_failed = False
    if provider == "moa":
        try:
            from hermes_cli.config import load_config
            from hermes_cli.moa_config import resolve_moa_preset
            _preset = model_cfg.get("model") or "default"
            resolve_moa_preset(load_config().get("moa") or {}, _preset)  # KeyError → 预设不存在
        except KeyError:
            print(f"[build_agent] MoA 预设 '{model_cfg.get('model')}' 缺失，降级到 deepseek")
            vendor = "deepseek"
            provider = _resolve_provider(vendor)
            _moa_failed = True
        except Exception:
            pass
    # MoA 降级到 deepseek 后，model 字段仍可能是预设名（如 "default"），对 deepseek 无效 → 回退默认模型
    _model = "deepseek-chat" if _moa_failed else (model_cfg.get("model") or "deepseek-chat")
    kwargs: dict[str, Any] = dict(
        provider=provider,
        model=_model,
        enabled_toolsets=[toolset_name],
        disabled_toolsets=["terminal"],
        quiet_mode=True,
        save_trajectories=False,
        skip_memory=True,
        skip_context_files=True,
        load_soul_identity=False,
    )
    if model_cfg.get("api_key"):
        kwargs["api_key"] = model_cfg["api_key"]
    if model_cfg.get("base_url"):
        kwargs["base_url"] = model_cfg["base_url"]
    if max_iterations:
        kwargs["max_iterations"] = int(max_iterations)
    if ephemeral_system_prompt:
        kwargs["ephemeral_system_prompt"] = ephemeral_system_prompt
    if tool_start_callback:
        kwargs["tool_start_callback"] = tool_start_callback
    if tool_complete_callback:
        kwargs["tool_complete_callback"] = tool_complete_callback
    if reasoning_callback:
        kwargs["reasoning_callback"] = reasoning_callback

    agent = create_agent(**kwargs)
    try:
        agent._tool_use_enforcement = True
    except Exception:
        pass
    return agent


# ============================================================================
# 3) 消息拆分 + SSE 编码
# ============================================================================
def _split_messages(messages: list[dict]) -> tuple[str, list[dict], Any]:
    """把 OpenAI messages 拆成 (system_message, conversation_history, user_message)。"""
    system_parts: list[str] = []
    convo: list[dict] = []
    last_user_content: Any = ""
    last_user_idx = -1
    for i, m in enumerate(messages or []):
        if m.get("role") == "user":
            last_user_idx = i
    for i, m in enumerate(messages or []):
        role = m.get("role")
        content = m.get("content")
        if role == "system":
            if isinstance(content, str):
                system_parts.append(content)
            continue
        if i == last_user_idx:
            last_user_content = content
            continue
        convo.append({"role": role, "content": content})
    system_message = "\n\n".join(p for p in system_parts if p)
    return system_message, convo, last_user_content


def _sse(obj: dict) -> bytes:
    return ("data: " + json.dumps(obj, ensure_ascii=False) + "\n\n").encode("utf-8")


def _delta_chunk(text: str) -> bytes:
    return _sse({"choices": [{"index": 0, "delta": {"content": text},
                              "finish_reason": None}]})


def _preview(v: Any, n: int = 160) -> str:
    try:
        s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    except Exception:
        s = str(v)
    return s[:n]


def _parse_tool_result(result: Any) -> dict:
    """把工具返回的字符串/对象解析为 dict，供前端展示 ok/stdout/url/error 等。"""
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        try:
            return json.loads(result)
        except Exception:
            return {"ok": True, "raw": result}
    return {"ok": True, "raw": str(result)}


# ============================================================================
# 4) 思考分流：把 <thinking>…</thinking> 从正文里剥出来走 reasoning 通道
# ============================================================================
class _ThinkingSplitter:
    """增量流中把 ``<thinking>…</thinking>``（及 ``<think:6124c78e>…</think:6124c78e>``）
    包裹的推理文本分流到 reasoning 通道，其余作为 delta 透传给前端。

    免费/非推理模型不会触发原生 ``reasoning_callback``，但深度思考模式下被系统提示引导
    用 ``<thinking>`` 标签显式推理。标签常因分块而截断，这里用「后缀保留」策略缓冲可能
    未闭合的标签片段，待闭合或流结束再 flush，避免把半截标签渲染给用户。
    """

    _OPEN = ("<thinking>", "<think:6124c78e>")
    _CLOSE = ("</thinking>", "</think:6124c78e>")

    def __init__(self, emit_reasoning, emit_delta):
        self._emit_reasoning = emit_reasoning
        self._emit_delta = emit_delta
        self._in_think = False
        self._out = ""   # 待发的 delta 累积
        self._rea = ""   # 待发的 reasoning 累积
        self._tail = ""  # 跨块边界的开/闭标签前缀残留

    @staticmethod
    def _earliest(s: str, tags, start: int):
        best_idx = -1
        best_tag = None
        for tag in tags:
            idx = s.find(tag, start)
            if idx != -1 and (best_idx == -1 or idx < best_idx):
                best_idx = idx
                best_tag = tag
        return best_idx, best_tag

    @staticmethod
    def _partial_len(s: str, tags) -> int:
        """s 末尾可能是某个 tag 的前缀的最大长度（不含完整 tag）。"""
        best = 0
        for tag in tags:
            for k in range(1, len(tag)):
                if s.endswith(tag[:k]):
                    best = max(best, k)
        return best

    def feed(self, chunk: str):
        data = self._tail + chunk
        self._tail = ""
        i = 0
        n = len(data)
        while i < n:
            if self._in_think:
                ci, ctag = self._earliest(data, self._CLOSE, i)
                if ci == -1:
                    keep = self._partial_len(data[i:], self._CLOSE)
                    self._rea += data[i:n - keep]
                    self._tail = data[n - keep:]
                    i = n
                else:
                    self._rea += data[i:ci]
                    self._flush_rea()
                    self._in_think = False
                    i = ci + len(ctag)
            else:
                oi, otag = self._earliest(data, self._OPEN, i)
                if oi == -1:
                    keep = self._partial_len(data[i:], self._OPEN)
                    self._out += data[i:n - keep]
                    self._tail = data[n - keep:]
                    i = n
                else:
                    self._out += data[i:oi]
                    self._flush_out()
                    self._in_think = True
                    i = oi + len(otag)

    def _flush_out(self):
        if self._out:
            self._emit_delta(self._out)
            self._out = ""

    def _flush_rea(self):
        if self._rea:
            self._emit_reasoning(self._rea)
            self._rea = ""

    def finish(self):
        if self._tail:
            if self._in_think:
                self._rea += self._tail
            else:
                self._out += self._tail
            self._tail = ""
        self._flush_out()
        self._flush_rea()


# ============================================================================
# 5) 一轮对话：worker 线程 + 队列 → SSE 字节流
# ============================================================================
# 推理强度档位（升序）：用于 deep_think 开关把 effort 提到「至少 high」、
# 但不降级用户已设的更高档位。来源：hermes-llms-full.txt Reasoning Effort 章节。
_EFFORT_ORDER = ["none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"]


def _merge_deep_think_effort(current, target: str = "high") -> dict:
    """deep_think 开启时，返回合并推理强度的 ``reasoning_config``。

    - current 已含 effort 且档位 ≥ target：保留用户更强的设定（绝不降级）；
    - 否则把 effort 提到 target（默认 ``"high"``）；
    - 保留 current 中的其它键（如部分 provider 需要的其它推理参数）。

    返回 dict 形状 ``{"effort": "<level>"}``，与批量运行（``hermes_features.batch_run``）
    及逐模型「推理强度」下拉框（``hermes_config.reasoning_effort_to_config``）约定一致。
    """
    base = current if isinstance(current, dict) else {}
    rc = dict(base)
    cur = str(rc.get("effort", "")).strip().lower()
    if cur not in _EFFORT_ORDER or _EFFORT_ORDER.index(cur) < _EFFORT_ORDER.index(target):
        rc["effort"] = target
    return rc


def stream_agent_chat(messages: list[dict], model_cfg: dict, *,
                      max_iterations: int | None = None,
                      approval_check: Callable[[str], "str | None"] | None = None,
                      deep_think: bool = False,
                      web_search: bool = True,
                      agent_factory: Callable | None = None,
                      timeout: float | None = None,
                      cancel_event: "threading.Event | None" = None,
                      ) -> Iterator[bytes]:
    """进程内运行 AIAgent 并产出 SSE 字节流（前端 EventSource 直接消费）。

    事件契约（前端按 type 分发；文本增量沿用 OpenAI chunk 形状）：
        {"choices":[{"delta":{"content": "..."}}]}            文本增量
        {"type":"reasoning","text":str}                        思考过程（可折叠）
        {"type":"action","tool":str,"preview":str}             工具开始
        {"type":"action_result","tool":str,"preview":str,"result":dict}
        {"error":{"message":str}}                              异常

    * ``approval_check(assistant_text) -> cmd|None``：可选，用于在结束时补发
      ``[APPROVAL_REQUIRED: cmd]`` 标记（自定义审批闭环）。
    * ``deep_think=True`` 时：把推理强度（``reasoning_config.effort``）提到「至少 high」
      （不降级用户已设的更高档位），并用 ``_ThinkingSplitter`` 把 ``<thinking>`` 段分流到 reasoning。
    * ``agent_factory``：默认 build_agent；离线测试注入 FakeAIAgent 工厂（tests/test_channels_bridge.py 中的 FakeAIAgent）。
    """
    factory = agent_factory or build_agent

    def _check_cancel():
        # 最佳努力中断：cancel 事件置位即抛出，让 worker 尽快退出（见 B3）。
        if cancel_event is not None and cancel_event.is_set():
            raise _CancelRequested()

    q: "queue.Queue[tuple]" = queue.Queue()
    SENTINEL = ("__end__",)
    splitter = None
    if deep_think:
        splitter = _ThinkingSplitter(
            emit_reasoning=lambda t: q.put(("reasoning", t)),
            emit_delta=lambda t: q.put(("delta", t)),
        )

    def on_tool_start(tool_call_id, name, display_args):  # noqa: ANN001
        _check_cancel()
        q.put(("action", name, _preview(display_args)))

    def on_tool_complete(tool_call_id, name, display_args, result):  # noqa: ANN001
        _check_cancel()
        # 同时发短 preview（日志标题）与解析后的 result（前端判定成功 / 展示 stdout / url）
        q.put(("action_result", name, _preview(result), _parse_tool_result(result)))

    def on_delta(delta):  # noqa: ANN001
        _check_cancel()
        if not delta:
            return
        if splitter is not None:
            splitter.feed(delta)
        else:
            q.put(("delta", delta))

    def on_reasoning(text):  # noqa: ANN001
        _check_cancel()
        if text:
            q.put(("reasoning", text))

    def on_tool_progress(name, *args, **kwargs):  # noqa: ANN001
        # MoA 参考模型事件（agent_init._moa_reference_relay 转发）：
        # name="moa.reference"(label,text,None,moa_index=,moa_count=) /
        #       "moa.aggregating"(aggregator,None,None,moa_ref_count=)
        _check_cancel()
        q.put(("tool_progress", name, args, kwargs))

    system_message, convo, user_content = _split_messages(messages)
    # run_conversation 的 user_message 仅接受 str（见 references/01-library-api.md:263-277）；
    # 图片等多模态内容不在此处构造 content block，而是由 routes/chat.py 经 vision_analyze
    # 工具交给模型查看（视觉模型返回原生像素、纯文本模型降级为辅助视觉模型描述）。
    # 因此 user_message 始终为字符串：取最后一条 user 消息的文本即可。
    user_message = user_content if isinstance(user_content, str) else ""

    # 硬超时：如果 timeout>0，启动一个守护线程在超时后向队列注入错误
    _timeout_timer: threading.Timer | None = None
    if timeout and timeout > 0:
        def _timeout_killer():
            q.put(("error", "执行超时（%.0fs），已自动终止" % timeout))
            q.put(SENTINEL)
        _timeout_timer = threading.Timer(timeout, _timeout_killer)
        _timeout_timer.daemon = True
        _timeout_timer.start()

    def worker():
        # 清空本线程编辑记录，确保静态/服务端文件改动只归因到本轮对话
        try:
            file_tools.reset_edited_files()
        except Exception:
            pass
        try:
            # 记录父模型配置，供对话中可能触发的子智能体委派继承凭据
            try:
                from frameworks import set_parent_model_cfg
                set_parent_model_cfg(model_cfg)
            except Exception:
                pass
            # 深度思考开关：在模型自带推理强度基础上，把 effort 提到「至少 high」
            # （不降级用户已设的更高档位）。仅作用于本轮 factory 调用，不改动传入的
            # model_cfg，避免影响并行 / 后续会话。
            effective_cfg = dict(model_cfg)
            if deep_think:
                effective_cfg["reasoning_config"] = _merge_deep_think_effort(
                    effective_cfg.get("reasoning_config"), target="high")
            agent = factory(
                effective_cfg, max_iterations=max_iterations,
                ephemeral_system_prompt=system_message or None,
                tool_start_callback=on_tool_start,
                tool_complete_callback=on_tool_complete,
                reasoning_callback=on_reasoning,
                tool_progress_callback=on_tool_progress,
                web_search=web_search,
            )
            # 记录当前父 agent（原生 delegate_task registry 兜底路径需要 parent_agent
            # 上下文；模型正常路径由 AIAgent._dispatch_delegate_task 自带 self）
            try:
                from frameworks import set_parent_agent
                set_parent_agent(agent)
            except Exception:
                pass
            result = agent.run_conversation(
                user_message=user_message,
                system_message=system_message or None,
                conversation_history=convo or None,
                stream_callback=on_delta,
            )
            final = ""
            messages_out = None
            if isinstance(result, dict):
                final = result.get("final_response") or ""
                messages_out = result.get("messages")
            if splitter is not None:
                splitter.finish()
            # 回传本轮被 Agent 改动的文件路径，使前端能把「AI 改了文件」真正呈现给用户
            # （静态文件自动重载、服务端文件提示重启），破除「声称成功但界面无变化」。
            _edited = []
            try:
                _edited = file_tools.get_edited_files()
            except Exception:
                pass
            q.put(("final", final, messages_out, _edited))
        except _CancelRequested:
            pass  # 用户已点停止：最佳努力中断，不打错误、正常收尾
        except Exception as e:  # noqa: BLE001
            q.put(("error", f"{type(e).__name__}: {e}"))
        finally:
            # 取消超时定时器（如果未超时则取消，已超时则无副作用）
            if _timeout_timer:
                _timeout_timer.cancel()
            q.put(SENTINEL)

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    assistant_text = ""
    streamed_any = False
    final_text = ""
    final_messages = None
    changed_files = []
    errored = False
    while True:
        item = q.get()
        if item == SENTINEL:
            break
        kind = item[0]
        if kind == "delta":
            assistant_text += item[1]
            streamed_any = True
            yield _delta_chunk(item[1])
        elif kind == "reasoning":
            yield _sse({"type": "reasoning", "text": item[1]})
        elif kind == "action":
            yield _sse({"type": "action", "tool": item[1], "preview": item[2]})
        elif kind == "action_result":
            yield _sse({"type": "action_result", "tool": item[1],
                        "preview": item[2], "result": item[3]})
        elif kind == "tool_progress":
            # MoA 参考模型事件透传给前端（chat.js 渲染为「🔄 MOA 参考模型」折叠块）
            yield _sse({"type": "tool_progress", "name": item[1],
                        "args": item[2], "kwargs": item[3]})
        elif kind == "final":
            final_text = item[1] or ""
            final_messages = item[2]
            if len(item) > 3:
                changed_files = item[3] or []
        elif kind == "error":
            yield _sse({"error": {"message": item[1]}})
            errored = True

    # 若未产生任何增量但有最终文本（部分模型/路径不走 stream_callback），补发一次
    if not streamed_any and final_text:
        assistant_text = final_text
        yield _delta_chunk(final_text)

    # 自定义审批标记兜底
    if approval_check:
        try:
            cmd = approval_check(assistant_text)
        except Exception:
            cmd = None
        if cmd:
            yield _delta_chunk(f"\n\n[APPROVAL_REQUIRED: {cmd}]")

    # 收尾事件：把完整文本与消息历史交给前端持久化（多轮上下文契约）
    # html = 服务端渲染的 Markdown（含 language-mermaid 类），供前端做 Mermaid / 代码复制后处理
    # D2：错误路径（worker 异常 / 超时）不再下发 done，避免前端 error 提示被空 done 覆盖、
    #     重复触发 attachMsgActions 与用量上报；错误已由上方 error 事件呈现。
    if not errored:
        yield _sse({"type": "done", "final": assistant_text or final_text,
                    "html": _render_html(assistant_text or final_text),
                    "messages": final_messages,
                    "changed_files": changed_files})


# ============================================================================
# 6) 启动自检（替代网关 /health：进程内路线不起 HTTP 服务也能量健康）
# ============================================================================
def runtime_ready() -> dict:
    """确认 Library 可导入、关键回调面在位。未安装时优雅返回 importable:False。"""
    import inspect

    info: dict[str, Any] = {
        "importable": False, "version": None, "callbacks_ok": False,
        "tools_registered": False, "error": None,
    }
    try:
        import importlib.metadata as md
        info["version"] = md.version("hermes-agent")
        from hermes_adapter import get_agent_class
        AIAgent = get_agent_class()

        info["importable"] = True
        params = inspect.signature(AIAgent.__init__).parameters
        rcp = inspect.signature(AIAgent.run_conversation).parameters
        info["callbacks_ok"] = (
            "tool_start_callback" in params
            and "tool_complete_callback" in params
            and "reasoning_callback" in params
            and "event_callback" in params
            and "stream_callback" in rcp
        )
        try:
            reg = register_pure_python_tools()
            info["tools_registered"] = bool(reg.get("ok"))
        except Exception as e2:  # noqa: BLE001
            info["error"] = f"{type(e2).__name__}: {e2}"
    except Exception as e:  # noqa: BLE001
        info["error"] = f"{type(e).__name__}: {e}"
    return info
