# 01 · hermes-desktop 三系统参考实现

> 本目录是**三系统解耦架构**的参考落地（理念见 `../../references/18-tristructure-architecture.md`）。
> 它同时也是「进程内 `AIAgent` + FastHTML + pywebview」的旗舰底座——底座本身即下面三个目录中的 `Agent系统/`。

## 三个目录

| 目录 | 是什么 | 关键约束 |
|---|---|---|
| `Agent系统/` | 纯净 Hermes 底座（= 上游 hermes-desktop 仓库，**git submodule**） | 零改动、零业务痕迹；可整体替换（见 `替换Agent系统.md`） |
| `业务系统/` | 纯业务逻辑与界面，不依赖 Agent | 绝不 `import` Agent 模块；有独立入口 `app.py` + `启动.bat`，可独立打包 |
| `连接系统/` | 纯桥接，**唯一装配耦合点** | 只做装配与启动，不承载可独立执行的业务功能 |

依赖方向单向：

```
业务系统 ──► 连接系统 ──► Agent系统
```

业务系统与 Agent系统 之间**不直接发生 import**：业务侧只暴露三个纯业务接口
（`build_app()` / `mount_rd_routes(app, rt)` / `get_business_snapshot()`），
由连接系统的 `fuse_business_into_agent()` 一次性装配到 Agent 底座上。

## 两种运行模式

```bash
# 融合模式：Agent 对话 + 业务路由，同一个 app（连接系统入口）
cd 连接系统 && python main.py       # http://127.0.0.1:8800/dashboard

# 独立模式：纯业务，无 Agent（业务系统自入口，无需连接系统在场）
cd 业务系统 && python app.py        # http://127.0.0.1:8810/dashboard
```

## 首次克隆：初始化底座 submodule

`Agent系统/` 是外部仓库（`https://github.com/kuailexiaozixin/hermes-desktop.git`）挂载的 submodule，
未初始化时该目录为空，融合模式与独立打包都会失败：

```bash
git submodule update --init --recursive   # 拉取 Agent系统 底座代码
```

底座升级 = 在 `Agent系统/` 内 `git pull`；业务/连接零改动。
这条性质由 `替换Agent系统.md` 的三步替换法保证，由 `scripts/verify_tristructure.py` 门禁校验。

## 门禁

```bash
python ../../scripts/verify_tristructure.py --root .
```

六项硬门禁（骨架齐全 / 业务无 Agent import / 连接唯一装配点 / 业务独立入口 / 底座无业务痕迹 / 替换说明在位）
+ 一项软门禁（底座零差异）。检查项语义与降级路径见 `../../references/18-tristructure-architecture.md` §7。
