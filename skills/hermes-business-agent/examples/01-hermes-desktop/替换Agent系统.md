# 替换 Agent系统（底座整体替换三步法）

> 本文是三系统架构的**交付件之一**：`Agent系统/` 被定义为「可整体替换的纯净底座」，
> 而"可替换"只有在替换步骤被明确写下、且业务/连接确实不依赖底座内部实现时才成立。
> 门禁 `scripts/verify_tristructure.py` 的检查项 `replace_doc` 要求本文件在位。
> 理念与判据见 `../../references/18-tristructure-architecture.md` §6。

---

## 0. 前提：什么情况下替换是"零改动"的

三个条件缺一，下面的步骤就会退化成一次迁移工程：

1. `业务系统/` 不 `import` 任何 Agent 模块（`server` / `routes` / `agent_runtime` / `tools` / `hermes_*`）——由 `biz_no_agent_import` 保证。
2. 所有「业务 ↔ Agent」桥接收拢在 `连接系统/bridge.py` 的 `fuse_business_into_agent()` 一处——由 `conn_unique_assembly` 保证。
3. `Agent系统/` 与上游底座零差异、无业务痕迹——由 `agent_zero_diff` + `agent_purity` 保证。

满足时，业务侧只看到三个稳定接口（`build_app()` / `mount_rd_routes()` / `get_business_snapshot()`），
底座换版本、换实现都不触碰它们。

**注意**：若上游底座改了这几个接口的语义（而非实现），那不是"替换"，是** breaking change**：
先跑 `python scripts/check_api_signature.py` 比对基线，确认漂移面，再决定迁移；不要直接覆盖目录。

---

## 1. 先隔离运行时数据（这一步决定替换是否无损）

底座代码和运行时数据默认混在同一棵目录树里——**开发态**的 `HERMES_HOME` 就是
`Agent系统/hermes_config/.hermes_data/`（`config.yaml`、`memories/`、`sessions/`、`skills/`、`cron/`、`SOUL.md`、`hooks/`、`state.db` 全在其中），
删目录即删数据。两种处置：

| 场景 | 数据根 | 替换时怎么办 |
|---|---|---|
| 开发态 | `Agent系统/hermes_config/.hermes_data/`（**在底座目录内**） | 先整体备份该子目录，替换后原样回填；**或**（推荐）把数据根移出去 |
| 冻结态（单 EXE） | `<exe 同目录>/hermes_data/`（由启动器 `setdefault` 钉住；外层先设 `HERMES_HOME` 即让位） | 无需处理，换代码不动数据 |

推荐做法——把数据根永久挪到底座目录之外，此后替换不再涉及任何数据迁移：

```bash
# 用 HERMES_DESKTOP_HOME 覆盖（get_hermes_home 的第一优先级）
set HERMES_DESKTOP_HOME=C:\myapp\hermes_data      # Windows
# 迁移旧数据：把 .hermes_data 全部内容原样搬过去，再启动验证
```

> 覆盖必须在**读取任何数据之前**生效（环境变量或 `启动.bat` 里设，不要设在业务代码中段）。
> 两个变量分清楚：`HERMES_DESKTOP_HOME` 管底座自己的数据根（`hermes_config/_paths.py:348-363` 的
> `get_hermes_home()`，覆盖分支排在冻结分支之前，**冻结态同样生效**）；`HERMES_HOME` 管 Library 内核，
> 底座 `main.py:6-10` 用的是 `setdefault`，所以你外层先设它就让位。两句机制的完整来源见 `05` §3。

---

## 2. 三步替换

```
① 备份并移除旧 Agent系统/           （数据已按 §1 隔离，则只剩代码备份）
② 以纯净底座重建 Agent系统/          （submodule 升级，或整仓 clone 上游 examples/01）
③ 回填运行时数据 → 跑门禁 → 双模式冒烟
```

### ① 备份并移除

```bash
# 记录当前底座版本，便于回滚与 diff
git -C Agent系统 rev-parse HEAD > ../Agent系统.bak/HEAD.txt
```

- 整个 `Agent系统/` 移到 `Agent系统.bak/`（不要原地 `rm -rf`，回滚要用）。
- 若 §1 已把数据根移走，此刻目录内应只剩代码；否则先确认 `.hermes_data` 已备份。

### ② 以纯净底座重建

两种来源，按你的接入方式择一：

```bash
# A. submodule 升级（本参考实现的方式：Agent系统 是独立 git 仓库挂载）
git submodule update --init --recursive
git -C Agent系统 fetch origin && git -C Agent系统 checkout <新版本标签>

# B. 无 submodule，直接取上游 examples/01 覆盖式重建
git clone --depth 1 https://github.com/kuailexiaozixin/hermes-desktop.git _new
# 用 _new 的顶层代码目录整体作为新的 Agent系统/，禁止把业务文件混进去
```

禁止在替换的同时"顺手改底座"——一加业务代码，`agent_zero_diff` 立刻判失败，底座再次不可替换。
需要底座改动只能走上游 PR，把 `Agent系统/` 换成包含该改动的版本。

### ③ 回填 + 验证

```bash
# 回填（仅当 §1 未外置数据根）
robocopy Agent系统.bak\hermes_config\.hermes_data Agent系统\hermes_config\.hermes_data /E

# 装依赖（底座有 requirements.txt / pyproject.toml）
python -m venv %LOCALAPPDATA%\hermes-desktop\venvs\agent && \
  %LOCALAPPDATA%\hermes-desktop\venvs\agent\Scripts\pip install -r Agent系统\requirements.txt

# 门禁 + 双模式冒烟
python ../../scripts/verify_tristructure.py --root .     # 六硬门禁全绿
python ../../scripts/check_api_signature.py             # 底座对 AIAgent 的用法未漂
cd 连接系统 && python main.py                            # 融合：Agent 对话 + 业务路由
cd 业务系统 && python app.py                             # 独立：仅业务路由
```

冒烟的最小断言（不是"页面打开了"，而是 Agent 真跑到了 `done`）：

- 融合模式：`/api/chat` 走 SSE，收到 `delta` 且最终 `done`；业务路由 200。
- 独立模式：业务路由 200，且**没有** Agent 对话端点（这是预期，不是缺陷）。
- 连接系统启动日志无 `ImportError` / 无底座告警。

---

## 3. 回滚

`Agent系统.bak/` 移回 `Agent系统/`（数据根未外置时，连同 `.hermes_data` 一起回填），
重跑门禁与冒烟即可。回滚不需要业务/连接改动——这正是三系统的意义。

---

## 4. 门禁语义边界（别误读绿色）

`verify_tristructure.py` 的 `agent_zero_diff` 是**软门禁**：它用
`git status --porcelain --untracked-files=no` 断言底座**未被本地改动**，并打印 `HEAD` 短 sha 供人工比对上游。
它**不联网、不验证"与上游最新一致"**——底座停在旧版本但本地干净，同样 PASS。要验证与上游同步，另跑：

```bash
python scripts/track_upstream.py          # 上游漂移监测
```

「软」只体现在**取不到证据**的那四类情形：无 `Agent系统/` 目录、该目录非 git 仓库或 submodule 未初始化、
`git` 命令不可用、`git status` 执行失败——它们判 SKIP 并打印原因，不阻断交付（`--strict` 下才计失败，CI 用）。
反过来，**git 可用且查出改动时它是 FAIL 并阻断**，此时唯一正确的处置是把底座改动撤回、走上游 PR，
而不是删检查项或去掉 `--strict` 让它变绿。
