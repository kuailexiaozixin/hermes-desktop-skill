# 05 · 安装与环境（HERMES_HOME 唯一真相）

> 环境根目录的**唯一真相源是 `hermes_constants`**。本文所有路径 API 均经 0.19.0 内省核实。

---

## 1. 安装

```bash
python -m venv venv
venv\Scripts\python -m pip install -U pip
venv\Scripts\python -m pip install "hermes-agent[web]==0.19.0"
```

- 装 `hermes-agent`（连字符）；导入符号是 `run_agent.AIAgent`。
- `[web]` extra 拉取 FastHTML / uvicorn / jinja2 等，做 Web UI 渲染层时需要。
- 校验：`venv/Scripts/python -c "import importlib.metadata as m; print(m.version('hermes-agent'))"`
  应输出 `0.19.0`。

---

## 2. 环境根目录：`HERMES_HOME`

`HERMES_HOME` 是 Hermes 所有运行时数据（会话、记忆、技能、配置、缓存）的根。**不要手写路径常量**——
一律走 `hermes_constants`：

| 函数 | 返回 | 用途 |
| --- | --- | --- |
| `get_hermes_home()` | `Path` | 数据根（`~/.hermes` 或覆盖值） |
| `get_hermes_home_override()` | `str \| None` | 当前上下文覆盖值 |
| `set_hermes_home_override(path)` | `Token` | **运行时覆盖**（返回 contextvars token，可还原） |
| `reset_hermes_home_override(token)` | `None` | 还原覆盖 |
| `display_hermes_home()` | `str` | 给人看的根目录串 |
| `get_default_hermes_root()` | `Path` | 默认根（未覆盖时） |
| `get_config_path()` | `Path` | `config.yaml` 路径 |
| `get_hermes_dir(new_subpath, old_name)` | `Path` | 子目录解析（兼容旧名） |
| `get_real_home(env=None)` | `str` | 真实用户主目录（考虑子进程环境） |
| `get_subprocess_home(env=None)` / `apply_subprocess_home_env(env)` | `str` / `None` | 子进程继承的 HOME |
| `get_env_path()` | `Path` | env 文件位置 |
| `get_skills_dir()` | `Path` | 用户技能目录 |
| `get_optional_skills_dir(default=None)` | `Path` | 可选技能目录 |
| `get_optional_mcps_dir(default=None)` | `Path` | 可选 MCP 目录 |
| `get_bundled_skills_dir(default=None)` | `Path` | 内置技能目录 |
| `find_node_executable(command)` | `str \| None` | 找 Node（browser 工具需要） |
| `heal_hermes_managed_node()` | `bool` | 修复 Hermes 托管 Node |

> 读取/设置数据位置**只许用上述 API**。直接拼 `~/.hermes` 字符串会在非默认配置下出错。

---

## 3. 冻结（打包 EXE）后的环境约束

⛔ **铁律**：打包成单文件 EXE 后，`HERMES_HOME` **恒为 `<exe>/hermes_data`**，不可重定向。
理由：EXE 自解压到临时目录，若允许用户 HOME 会污染系统、且无法随应用卸载清理。

- 出厂数据（`.hermes_data` 内的默认配置/技能）**冻结态只读**；运行时变更写入同一目录。
- 触碰出厂数据前必须**备份 → 变更 → 还原 → md5 校验**（见 `07` §3 运行数据保护）。
- 不杀用户正在运行的 EXE。

```python
# 冻结期通常无需手动设 HERMES_HOME；run_agent 内部会把根指向 <exe>/hermes_data
import hermes_constants as hc
print(hc.get_hermes_home())   # 冻结态即 <exe>/hermes_data
```

---

## 4. Node 与浏览器工具

`browser` 工具集（13 个工具）依赖一个 Node 运行时。`hermes_constants.find_node_executable()`
会自动探测 Hermes 托管 Node；缺失时 browser 工具不可用但**不应崩溃**——用 `heal_hermes_managed_node()`
尝试修复。桌面应用若启用浏览器能力，启动自检应确认 Node 可用（见 `01` §7、`07` §3 自检）。

---

## 5. 凭证

- `api_key` / `base_url` 可构造时传入，也可走默认凭证源（环境变量 `HERMES_API_KEY`、`OPENAI_API_KEY` 等）。
- 多供应商/多 Profile 切换：`AIAgent.switch_model(...)` 运行时换；持久 Profile 由 `hermes_cli.profiles` 管理
  （进程内路线一般只用 `switch_model`，不依赖 CLI）。
- 不要在技能文件里硬编码密钥；密钥来自用户配置或环境变量。

---

## 6. 典型布局（进程内桌面应用）

```
<app>/
├── app.exe                # 打包产物（冻结态）
├── hermes_data/           # HERMES_HOME（冻结态唯一根）
│   ├── config.yaml
│   ├── skills/
│   ├── memory/
│   └── sessions/
├── venv/                  # 开发期虚拟环境（仅开发用）
└── requirements.txt       # 实际依赖清单（解析用，不写死版本锁死）
```
