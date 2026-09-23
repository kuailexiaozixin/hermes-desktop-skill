# 安装与环境 — 示例实战：launcher.json + 最小 venv（from examples/01-hermes-desktop）

> 本文件从 `references/05-install-and-env.md` 抽出：该旗舰示例如何数据驱动启动 + 最小 venv。
> 属示例耦合内容，不进入技能核心骨干（通用安装/环境方法见 `references/05-install-and-env.md` §1–§5）。

---

旗舰示例用**数据驱动启动器**把"装什么、跑哪个入口、开哪个端口"全外置到配置，避免硬编码：

## 6.1 `launcher.json`（启动器唯一数据源）

```json
{
  "app_name": "你的应用",
  "entry": "main.py",
  "venv_name": "your-app-venv",
  "requirements": [
    "hermes-agent[web]==0.19.0",
    "python-fasthtml", "pywebview", "markdown", "uvicorn", "qrcode"
  ],
  "host": "127.0.0.1",
  "port": 5001,
  "window": { "width": 920, "height": 700 }
}
```

`launcher.py` 读它 → 决定 venv 名 / 入口 / 端口 / 窗口尺寸，**不写死任何路线判断**（见 `02` §5.1）。

## 6.2 最小 venv 依赖清单（只装实际依赖）

示例 `requirements.txt` 与 `launcher.json` 的 `requirements` **完全一致**，且**版本钉死**：

```
hermes-agent[web]==0.19.0     # 核心 + web 工具（需联网检索时）；纯 Tkinter 路线去掉 [web]
python-fasthtml               # FastHTML 路线才需要；Tkinter 路线不要
pywebview                     # 桌面壳（FastHTML 路线）
markdown                      # 渲染 Markdown 回复
uvicorn                       # 本地 ASGI 服务
qrcode                        # 渠道扫码登录等可选能力
```

> 🔴 **最小 venv 铁律**（与 `06-packaging.md` §1 一致）：建干净 venv → 只装 `requirements.txt`
> 实际列的依赖 → 在该 venv 内跑 PyInstaller。示例把 venv 建在目录**之外**
> （`D:\临时环境\<venv_name>`，`FD_VENV_HOME` / `HERMES_DESKTOP_VENV_HOME` 可改），不污染系统全局。
> **禁止**在示例目录内建 `.venv`、禁止写死解释器绝对路径、禁止降级全局包。

## 6.3 版本钉死是有意选择

`hermes-agent[web]==0.19.0` 钉死到技能基线版本——因为本技能的事实断言（回调签名、默认值、
SSE 事件词表）都基于 0.19.0 源码实证。锁定旧版 + 跑 `track_upstream`/`check_api_signature`
确认无破坏性变更，比盲目追最新版更安全（见 `07-quality-gates.md#drift`）。
