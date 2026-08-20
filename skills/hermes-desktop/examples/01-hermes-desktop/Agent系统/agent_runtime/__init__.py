"""agent_runtime.py — Hermes Desktop 通用底座的**集成内核**（Library 进程内模式）

这是一个标准、通用的 Hermes Desktop 底座内核：只提供「进程内集成 Hermes Python
Library」的完整桥接能力，**不绑定任何业务**。未来项目复制本目录，在 `app_tools/`
里加自己的业务工具即可（`app_tools.register_into(registry)` 会被自动调用）。

架构（全部来自 hermes_agent 0.19.0 源码实证，见 references/01-library-api.md）：
  * `from run_agent import AIAgent` 在**当前进程内**跑 Agent —— 无网关、无 Node、无 HTTP 代理。
  * `disabled_toolsets=["terminal"]` 彻底禁用 spawn-per-call 的终端工具，从而**不需要
    Git Bash / PortableGit**；文件与脚本能力改由纯 Python 工具承担（file_tools.py）。
  * `registry.register(..., toolset="file", override=True)` 用纯 Python handler 覆盖内置
    read_file/write_file/patch/search_files，并新增 list_dir / run_python（零 subprocess）。
  * `host_tools.py` 提供宿主内预览（preview_asgi_app / stop_preview）与运行时装库
    （install_library，进程内 pip.main --target <root>/.deps）。
  * AIAgent 非线程安全 → 每轮对话新建；run_conversation() 同步阻塞 → worker 线程 +
    queue.Queue 桥接成 SSE 字节流。
  * 文本增量走 run_conversation(stream_callback=...)（**方法参数**）；
    工具/推理事件走 AIAgent(__init__) 的**构造器回调**。

底座契约（可被未来项目复用）：
  * `stream_agent_chat(..., agent_factory=build_agent)` —— agent_factory 可注入，
    离线测试用 FakeAIAgent 替换真实 AIAgent（见 tests/test_channels_bridge.py）。
  * `run_agent` / `tools.*` 全部**懒导入**：未安装 hermes-agent 时本模块仍可 import
    （结构门禁 / CI / 离线测试都能跑）。
"""

# 拆包后统一 re-export，保持 `import x as m; m.xxx` 完全兼容

from ._tools import (MAX_TOOL_OUTPUT, DISABLED_TOOLSETS, AUTOMATION_TOOLSETS, DANGEROUS_TOOLSETS, ensure_automation_defaults, register_pure_python_tools, SYSTEM_PROMPT)
from ._chat import (build_agent, build_trial_agent, stream_agent_chat, runtime_ready)
from ._toolsets import (TOOLSET_RUNTIME_HINTS, TOOLSET_LABELS, TOOLSET_CATEGORIES, ENV_REQUIRED, get_toolset_matrix, invalidate_toolset_cache, discover_toolsets, configure_toolset, test_toolset, set_toolset_disabled, set_toolset_profile, execute_approved_command, extract_approval)
# Spec 表（工具集元数据单一事实源，方案 A 重构引入）
from ._toolset_specs import (TOOLSET_SPECS, CATEGORY_ORDER, get_spec, build_trial_force, build_trial_prompt)

