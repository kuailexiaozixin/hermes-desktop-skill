# 11 · `batch_runner` 与 Hermes 自有支撑模块参考（0.19.0）

> 本文件覆盖 Library 中**除 `run_agent` / `tools` / `agent` / `hermes_cli` 之外**的、与桌面进程内集成**最相关**的 Hermes 自有模块：
> `batch_runner`（批量 Agent 运行器）以及一组**单文件支撑模块**（`hermes_constants` / `hermes_state` / `hermes_logging` / `hermes_time` / `hermes_bootstrap` / `model_tools` / `toolsets` / `toolset_distributions` / `utils` / `trajectory_compressor`）。
>
> 全部条目经 `hermes-agent==0.19.0` 已装包**逐模块 import + 读取 docstring + 提取公开 API** 核实（数据来源：`top_level.txt` 顶层模块名单 + `importlib` 内省）。
> 与 `10-hermes-cli.md` 的边界：`hermes_cli.*` 已在 `10` 全量列举；本文不含 `hermes_cli`，只列上述支撑模块。

---

## 0. 这些模块是什么、为什么桌面集成要关心

| 维度 | 说明 |
| --- | --- |
| `batch_runner` | 批量并发跑多个 Agent 任务的运行器（`BatchRunner`），适合「一次性处理一批提示词/文件」的离线批处理场景。 |
| `hermes_constants` | 全局常量与路径解析（`HERMES_HOME` / skills 目录 / node 可执行发现 / 平台判断）。**进程内最常用**——你要知道数据落哪、怎么拿 `HERMES_HOME`。 |
| `hermes_state` | SQLite 会话状态存储（`SessionDB` / `AsyncSessionDB`）。多轮会话如何落盘、如何修复损坏库，看这里。 |
| `hermes_logging` | 集中式日志配置（文件轮转 / 会话上下文）。桌面应用想统一日志格式时复用。 |
| `hermes_time` | 时区感知时钟（`now()` / `get_timezone()`）。替代 `datetime.now()`，避免时区漂移。 |
| `hermes_bootstrap` | Windows UTF-8 引导 + import 路径加固。Windows 桌面 EXE 启动时建议调用。 |
| `model_tools` | 工具集可用性与定义查询（`get_available_toolsets` / `get_tool_definitions` / `handle_function_call`）。 |
| `toolsets` | 工具集注册与解析（`get_all_toolsets` / `resolve_toolset` / `create_custom_toolset`）。自定义工具集从这里入手。 |
| `toolset_distributions` | 工具集分发档（`list_distributions` / `sample_toolsets_from_distribution`）。 |
| `utils` | 通用工具函数（原子写 YAML/JSON、env 布尔读取、代理 URL 归一）。进程内随手复用。 |
| `trajectory_compressor` | 轨迹（对话轨迹）压缩器（`TrajectoryCompressor`）。批量/长对话的轨迹压缩用。 |

> **适用说明（与 `07` §1、`10` §1 一致）**：本文档以**进程内直跑路线**为叙述示例；本表模块多为纯逻辑/本地支撑，是否适合直接调用须结合所选路线判断。
> 本文模块均为**纯逻辑/本地**支撑，进程内可放心 import；但若某函数内部起子进程（如 `batch_runner` 并发拉起 Agent），
> 仍走 `run_agent.AIAgent` 的公开接口（见 `01`），不要绕过它直接复刻循环。

---

## 1. `batch_runner` —— 批量 Agent 运行器

- **docstring**：`Batch Agent Runner`
- **公开 API**：`BatchRunner`（类）、`main`（CLI 入口）

### 1.1 它解决什么问题

当你有一批独立任务（例如「对 100 个文件各做一遍总结」「对一批提示词各跑一遍 Agent」），
逐个串行跑太慢。`BatchRunner` 负责**并发调度**多个 Agent 运行，收集各自结果。

### 1.2 进程内怎么用（要点）

- 复用 `BatchRunner` 类做并发编排时，**底层仍用 `run_agent.AIAgent`**（见 `01`）构造每个子 Agent；
  不要在桌面应用里调用 `batch_runner.main()`（那是 `hermes batch` 子命令的 CLI 入口，会走 TTY/文件参数解析）。
- 批处理的结果持久化、并发上限、失败重试，建议在桌面应用层用你自己的调度器控制，
  仅把 `BatchRunner` 当作「已知可用、行为已核实」的参考实现。

> 注：批量处理能力的**进程内实战**见 `08-capability-integration.md`（Batch 能力节）；本文只列模块定位与 API。

---

## 2. `hermes_constants` —— 全局常量与路径解析（进程内最常用）

- **docstring**：`Shared constants for Hermes Agent`
- **规模**：0 类 / 37 函数（公开签名已核实）

代表性 API（真实存在）：

| 函数 | 用途 |
| --- | --- |
| `get_hermes_home()` | 解析 `HERMES_HOME`（数据根目录）。桌面应用拿数据落点用（详见 `05-install-and-env.md`） |
| `get_hermes_home_override()` / `set_hermes_home_override()` / `reset_hermes_home_override()` | 进程内临时覆盖 `HERMES_HOME`（测试/多实例用） |
| `get_config_path()` | 配置 `config.yaml` 路径 |
| `get_skills_dir()` / `get_bundled_skills_dir()` / `get_optional_skills_dir()` | skills 目录解析 |
| `get_optional_mcps_dir()` | 可选 MCP 目录 |
| `get_default_hermes_root()` / `get_hermes_dir()` / `get_real_home()` / `get_process_hermes_home()` | 各层级根目录解析 |
| `is_wsl()` / `is_termux()` / `is_container()` | 运行环境判断（决定路径策略） |
| `windows_path_to_wsl()` / `wsl_unc_path_to_posix()` / `translate_cwd_for_wsl_backend()` | WSL 路径转换 |
| `find_node_executable()` / `find_node_executable_on_path()` / `find_hermes_node_executable()` / `iter_hermes_node_dirs()` / `hermes_managed_node_tree_present()` / `heal_hermes_managed_node()` / `node_tool_runnable()` / `agent_browser_runnable()` / `with_hermes_node_path()` | node 可执行发现（浏览器/沙箱能力前置检查） |
| `apply_ipv4_preference()` / `apply_subprocess_home_env()` / `secure_parent_dir()` / `get_env_path()` / `get_subprocess_home()` | 子进程环境/目录加固 |
| `parse_reasoning_effort()` / `resolve_reasoning_config()` / `resolve_per_model_reasoning_effort()` | 推理强度参数解析 |

> 桌面集成里**几乎一定会用到** `get_hermes_home()` 与 `get_config_path()`——它们是定位 Hermes 数据根与配置的唯一真相源。

---

## 3. `hermes_state` —— SQLite 会话状态存储

- **docstring**：`SQLite State Store for Hermes Agent`
- **规模**：2 类 / 6 函数

| 名称 | 类型 | 用途 |
| --- | --- | --- |
| `SessionDB` | 类 | 同步会话状态库（会话元数据、消息、状态_meta），`AIAgent` 自动使用 |
| `AsyncSessionDB` | 类 | 异步会话状态库 |
| `apply_wal_with_fallback()` | 函数 | WAL 模式应用（失败回退） |
| `repair_state_db_schema()` | 函数 | 修复状态库 schema（库损坏时） |
| `is_malformed_db_error()` | 函数 | 判断是否为损坏库错误 |
| `get_last_init_error()` | 函数 | 取上次初始化错误 |
| `format_session_db_unavailable()` | 函数 | 状态库不可用时的提示文本 |
| `workspace_key()` | 函数 | 工作区键生成 |

> 会话持久化（多轮、跨启动恢复）的完整行为见 `09-integration-e2e.md` 与 `01`；本文仅列模块 API。

---

## 4. `hermes_logging` —— 集中式日志

- **docstring**：`Centralized logging setup for Hermes Agent`
- **规模**：0 类 / 7 函数

| 函数 | 用途 |
| --- | --- |
| `setup_logging()` | 配置根日志（文件轮转 + 控制台） |
| `setup_verbose_logging()` | 详细日志模式 |
| `set_session_context()` / `clear_session_context()` | 给日志附加/清除会话上下文 |
| `rotating_file_handlers()` | 取轮转文件处理器 |
| `flush_log_queue()` / `drain_log_queue()` | 刷新/排空日志队列 |

---

## 5. `hermes_time` —— 时区感知时钟

- **docstring**：`Timezone-aware clock for Hermes`
- **规模**：0 类 / 3 函数

| 函数 | 用途 |
| --- | --- |
| `now()` | 取当前时区感知时间 |
| `get_timezone()` | 取当前时区 |
| `reset_cache()` | 重置时区缓存 |

---

## 6. `hermes_bootstrap` —— Windows UTF-8 引导

- **docstring**：`Windows UTF-8 bootstrap for Hermes entry points`
- **规模**：0 类 / 3 函数

| 函数 | 用途 |
| --- | --- |
| `apply_windows_utf8_bootstrap()` | 应用 Windows UTF-8 标准流引导 |
| `harden_import_path()` | 加固 import 路径（避免误导入遮蔽） |
| `activate_durable_lazy_target()` | 激活持久懒加载目标（与 `tools.lazy_deps` 联动） |

---

## 7. `model_tools` —— 工具集可用性与定义查询

- **docstring**：`Model Tools Module`
- **规模**：0 类 / 8 函数

| 函数 | 用途 |
| --- | --- |
| `get_available_toolsets()` | 取当前可用工具集 |
| `get_tool_definitions()` | 取工具定义（schema） |
| `get_all_tool_names()` | 取所有工具名 |
| `get_toolset_for_tool()` | 反查某工具所属工具集 |
| `handle_function_call()` | 工具函数调用分发 |
| `check_tool_availability()` / `check_toolset_requirements()` | 可用性/依赖检查 |
| `coerce_tool_args()` | 工具参数类型校正 |

---

## 8. `toolsets` —— 工具集注册与解析

- **docstring**：`Toolsets Module`
- **规模**：0 类 / 9 函数

| 函数 | 用途 |
| --- | --- |
| `get_all_toolsets()` | 取全部工具集 |
| `get_toolset_names()` | 取工具集名列表 |
| `get_toolset()` / `get_toolset_info()` | 取单个工具集 / 其元信息 |
| `resolve_toolset()` / `resolve_multiple_toolsets()` | 解析工具集（含依赖展开） |
| `create_custom_toolset()` | **创建自定义工具集**（进程内注册自制工具） |
| `validate_toolset()` | 校验工具集定义 |
| `bundle_non_core_tools()` | 把非核心工具打包进 bundle |

> 自定义工具集的进程内注册实战见 `01-library-api.md`（`ctx.register_tool` / `create_custom_toolset` 用法）；
> 57 个内置工具集的行为语义见 `03-capabilities-and-toolsets.md`。

---

## 9. `toolset_distributions` —— 工具集分发档

- **docstring**：`Toolset Distributions Module`
- **规模**：0 类 / 5 函数

| 函数 | 用途 |
| --- | --- |
| `list_distributions()` | 列出所有分发档 |
| `get_distribution()` | 取单个分发档 |
| `sample_toolsets_from_distribution()` | 从分发档采样工具集 |
| `validate_distribution()` | 校验分发档 |
| `print_distribution_info()` | 打印分发档信息 |

---

## 10. `utils` —— 通用工具函数

- **docstring**：`Shared utility functions for hermes-agent`
- **规模**：1 类 / 16 函数

| 名称 | 类型/用途 |
| --- | --- |
| `atomic_json_write()` / `atomic_yaml_write()` / `atomic_roundtrip_yaml_update()` / `atomic_replace()` | 原子写（防半写损坏，桌面写配置强烈建议用） |
| `fast_safe_load()` / `safe_json_loads()` | 安全反序列化 |
| `env_bool()` / `env_int()` / `env_float()` / `env_var_enabled()` / `is_truthy_value()` | 环境变量类型化读取 |
| `base_url_hostname()` / `base_url_host_matches()` / `normalize_proxy_url()` / `normalize_proxy_env_vars()` | URL/代理归一 |
| `model_forces_max_completion_tokens()` | 判断模型是否强制 `max_completion_tokens` |
| `IndentDumper` | YAML 缩进 dumper 类 |

---

## 11. `trajectory_compressor` —— 轨迹压缩器

- **docstring**：`Trajectory Compressor`
- **规模**：4 类 / 1 函数

| 名称 | 类型/用途 |
| --- | --- |
| `TrajectoryCompressor` | 轨迹压缩器主类 |
| `CompressionConfig` | 压缩配置 |
| `TrajectoryMetrics` / `AggregateMetrics` | 压缩度量 |
| `main` | CLI 入口（`hermes` 压缩子命令，桌面应用不调） |

> 上下文压缩的进程内实战见 `08`（Goals/Snapshots 等能力涉及的压缩）与 `01`；本文仅列模块 API。

---

## 12. 与本文档集其他篇目关系（避免交叉）

| 主题 | 归属文件 | 本文 role |
| --- | --- | --- |
| `AIAgent` 构造/回调/SSE | `01-library-api.md` | 对外接口（本文不涉及） |
| 进程内路径 / `HERMES_HOME` / 环境 | `05-install-and-env.md` | 环境（`hermes_constants` 的落地语义在 `05`） |
| 会话持久化行为 | `09-integration-e2e.md` | 持久化行为（本文仅列 `hermes_state` API） |
| 57 工具集逐条 / 自定义注册 | `03-capabilities-and-toolsets.md` | 能力行为（`toolsets`/`model_tools` 仅列 API） |
| `hermes_cli` 模块清单 | `10-hermes-cli.md` | 不同包（CLI vs 支撑模块） |
| `tools` / `agent` 全量枚举 | `12-tools-modules.md` / `13-agent-modules.md` | 工具/内核实现（本文不列） |
| 网关/CLI/cron/插件等基础设施 | `14-library-infra.md` | 进程外设施（本文不列） |
| 红线/门禁 | `07-quality-gates.md` | 权威红线（本文仅引用） |

> 本文只负责「`batch_runner` + 支撑单文件模块的存在性 / 用途 / 公开 API」这一层，
> 凡涉及能力行为、环境落地、持久化行为者，指向对应篇目，不重复。

---

## 13. 全文检索索引（桌面集成视角）

| 你想做的事 | 看本文哪个小节 |
| --- | --- |
| 拿 `HERMES_HOME` / 配置路径 | §2 `hermes_constants` |
| 多轮会话怎么落盘 / 库坏了怎么修 | §3 `hermes_state` |
| 统一日志格式 | §4 `hermes_logging` |
| 拿当前时间（时区正确） | §5 `hermes_time` |
| Windows EXE 启动引导 | §6 `hermes_bootstrap` |
| 查可用工具集 / 取工具定义 | §7 `model_tools` |
| **注册自定义工具集** | §8 `toolsets`（`create_custom_toolset`） |
| 按场景快速装配工具集 | §9 `toolset_distributions` |
| 原子写配置 / 读 env 布尔 | §10 `utils` |
| 批量跑一堆 Agent 任务 | §1 `batch_runner` |
| 长对话轨迹压缩 | §11 `trajectory_compressor` |
