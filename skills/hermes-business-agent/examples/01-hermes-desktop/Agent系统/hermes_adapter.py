"""hermes_adapter.py — Hermes 防腐层（Anti-Corruption Layer）

按 example01 独立性/耦合度批判报告建议 3：把本示例对 **Hermes 内部 API** 的直接调用
（`run_agent.AIAgent` 构建、`tools.registry`、`tools.*` 工具、`agent.*`、`plugins.*`）
集中封装在本适配层，业务/集成模块只依赖本文件暴露的接口。

好处：
- 升级 `hermes-agent` 时，内部 API 变化只需改本文件，业务模块不动；
- 业务模块不再钻进 Hermes 实现细节（如 `agent_init.py:816` 的 MoA KeyError 规避）；
- 可复用 `scripts/check_api_signature.py` 对本适配层做版本兼容门禁。

**设计约束**：薄封装——不改变签名与调用语义，只收敛 import 点；每个函数内部懒导入，
避免模块导入期就拉起 Hermes 内核（保持轻量 import 路径）。
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# AIAgent 构建（run_agent.AIAgent）
# ---------------------------------------------------------------------------
def create_agent(**kwargs) -> Any:
    """在**当前进程内**构造 AIAgent（无网关、无 HTTP 代理）。

    等价 `from run_agent import AIAgent; AIAgent(**kwargs)`。所有进程内 Agent 工厂
    （agent_runtime.build_agent / build_trial_agent / stream_agent_chat 的 worker）
    都应改经此入口，统一收敛对 AIAgent 的 import。
    """
    from run_agent import AIAgent
    return AIAgent(**kwargs)


def get_agent_class():
    """返回 AIAgent 类本身（用于 inspect.signature 能力探测 / 类型判断）。"""
    from run_agent import AIAgent
    return AIAgent


# ---------------------------------------------------------------------------
# tools.registry（全局工具注册表）
# ---------------------------------------------------------------------------
def get_tools_registry():
    """返回 Hermes 全局工具注册表对象（等价 `from tools.registry import registry`）。"""
    from tools.registry import registry
    return registry


def discover_builtin_tools() -> dict:
    """发现 Hermes 内置工具（等价 `tools.registry.discover_builtin_tools()`）。"""
    from tools.registry import discover_builtin_tools
    return discover_builtin_tools()


def invalidate_tool_caches() -> None:
    """使工具 check_fn 缓存失效（等价 `tools.registry.invalidate_check_fn_cache()`）。"""
    from tools.registry import invalidate_check_fn_cache
    invalidate_check_fn_cache()


def tool_error(*a, **k):
    """工具返回错误形状（等价 `tools.registry.tool_error`）。"""
    from tools.registry import tool_error
    return tool_error(*a, **k)


def tool_result(*a, **k):
    """工具返回结果形状（等价 `tools.registry.tool_result`）。"""
    from tools.registry import tool_result
    return tool_result(*a, **k)


# ---------------------------------------------------------------------------
# tools.* 工具模块
# ---------------------------------------------------------------------------
def ensure_delegate_tool() -> None:
    """确保 delegate 工具已注册（等价 `import tools.delegate_tool` 的副作用）。"""
    import tools.delegate_tool  # noqa: F401  # 副作用：注册委托工具


def is_code_sandbox_available() -> bool:
    """代码执行沙箱是否可用（等价 `tools.code_execution_tool.SANDBOX_AVAILABLE`）。"""
    from tools.code_execution_tool import SANDBOX_AVAILABLE
    return SANDBOX_AVAILABLE


def check_browser_requirements() -> bool:
    """浏览器工具依赖是否就绪（等价 `tools.browser_tool.check_browser_requirements()`）。"""
    from tools.browser_tool import check_browser_requirements
    return check_browser_requirements()


def register_mcp_servers(cfg):
    """把 MCP 服务器配置交给 tools.mcp_tool 连接（等价 `tools.mcp_tool.register_mcp_servers`）。"""
    from tools.mcp_tool import register_mcp_servers
    return register_mcp_servers(cfg)


def ensure_kanban_tools() -> None:
    """确保 kanban 工具已注册（等价 `import tools.kanban_tools` 的副作用）。"""
    import tools.kanban_tools  # noqa: F401


# ---------------------------------------------------------------------------
# agent.*（内核逻辑模块）
# ---------------------------------------------------------------------------
def clear_skills_system_prompt_cache() -> None:
    """清空技能系统提示词缓存（等价 `agent.prompt_builder.clear_skills_system_prompt_cache()`）。"""
    from agent.prompt_builder import clear_skills_system_prompt_cache
    clear_skills_system_prompt_cache()


def get_model_capabilities(model: str):
    """查询模型能力（等价 `agent.models_dev.get_model_capabilities`）。"""
    from agent.models_dev import get_model_capabilities
    return get_model_capabilities(model)


def create_context_compressor(*a, **k):
    """构造上下文压缩器（等价 `agent.context_compressor.ContextCompressor`）。"""
    from agent.context_compressor import ContextCompressor
    return ContextCompressor(*a, **k)


def get_text_auxiliary_client(*a, **k):
    """获取文本辅助客户端（等价 `agent.auxiliary_client.get_text_auxiliary_client`）。"""
    from agent.auxiliary_client import get_text_auxiliary_client
    return get_text_auxiliary_client(*a, **k)


def get_skill_bundles_module():
    """访问 `agent.skill_bundles` 模块（技能捆绑包）。"""
    import agent.skill_bundles as m
    return m


def get_learning_graph_module():
    """访问 `agent.learning_graph` 模块（学习图谱）。"""
    import agent.learning_graph as m
    return m


def get_learning_mutations_module():
    """访问 `agent.learning_mutations` 模块（学习变更）。"""
    import agent.learning_mutations as m
    return m


# ---------------------------------------------------------------------------
# plugins.*（插件扩展面）
# ---------------------------------------------------------------------------
def discover_context_engines():
    """发现上下文引擎（等价 `plugins.context_engine.discover_context_engines`）。"""
    from plugins.context_engine import discover_context_engines
    return discover_context_engines()


def load_context_engine(*a, **k):
    """加载上下文引擎（等价 `plugins.context_engine.load_context_engine`）。"""
    from plugins.context_engine import load_context_engine
    return load_context_engine(*a, **k)


def list_memory_providers():
    """列出记忆 provider（等价 `plugins.memory.list_memory_provider_names`）。"""
    from plugins.memory import list_memory_provider_names
    return list_memory_provider_names()


def create_holographic_store(*a, **k):
    """构造 Holographic 记忆存储（等价 `plugins.memory.holographic.store.MemoryStore`）。"""
    from plugins.memory.holographic.store import MemoryStore
    return MemoryStore(*a, **k)


def create_fact_retriever(*a, **k):
    """构造 Holographic 事实检索器（等价 `plugins.memory.holographic.retrieval.FactRetriever`）。"""
    from plugins.memory.holographic.retrieval import FactRetriever
    return FactRetriever(*a, **k)
