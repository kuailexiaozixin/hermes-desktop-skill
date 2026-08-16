# Hermes Desktop · Universal Base

> A complete reference implementation of **in-process integration of the [Hermes Python Library](https://github.com/kuailexiaozixin/hermes-agent) inside a desktop app** — FastHTML server-side rendering + pywebview native window. Full feature parity, fully decoupled from business logic.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](pyproject.toml)
[![CI](https://github.com/kuailexiaozixin/hermes-agent-fasthtml-desktop/actions/workflows/ci.yml/badge.svg)](https://github.com/kuailexiaozixin/hermes-agent-fasthtml-desktop/actions/workflows/ci.yml)

[中文](README.md) · [Docs](docs/) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

---

## What It Is

A **standard, universal Hermes Desktop base** that demonstrates the complete pattern for integrating the **Hermes Python Library in-process** inside a desktop application. It mirrors the official Hermes Desktop experience, bringing the general capabilities of a desktop AI assistant (multi-session, streaming chat, tool timeline, thinking folding, model/tool/skill/MCP/loops/delegation/scheduler, approval loop, artifact drawer, etc.) into a single self-contained project.

**Key design points:**

- **In-process runtime** — no gateway / separate HTTP service / Node; integrate directly via `AIAgent(...)` in-process
- **Business-agnostic** — zero business jargon, zero external business dependencies, self-contained
- **Reusable template** — copy this directory, add your own business tools under `app_tools/`, and wire any app to Hermes

> `app_tools/` ships one **demo tool** `sogou_weixin.py` (Sogou WeChat search) as a copyable template for "how to attach a business tool"; delete the `register_into` line in `app_tools/__init__.py` to return to a pure base.

## ✨ Highlights

| Capability | Description |
| --- | --- |
| Multi-session + streaming chat | Character-by-character SSE output, server-persisted, create/switch/rename/pin/delete |
| Thinking folding + tool timeline | `<thinking>` split + tool start/complete/result cards |
| Model center | 36 vendor presets + custom + key management |
| Tools / Skills / MCP center | toolset toggles, skill CRUD, MCP add/remove/start/stop |
| **Unified skill marketplace** | aggregates 8 sources (SkillHub / skills.sh / clawhub / lobehub / browse-sh / official / GitHub / Claude) |
| **MCP store** | LobeHub ecosystem — browse / search / install / uninstall online |
| **LLM Wiki knowledge base** | 3-layer interlinked + backlinks + auto-index + graph |
| **Bonus features × 13** | Goals / snapshots / MOA / backup / projects / curation / batch / journey / routing etc. |
| **IM channel bridge** | WeChat/WeCom/DingTalk/Feishu/QQ/Slack/Discord/Telegram/Webhook + QR login |
| Loops / delegation / scheduler | 8 built-in loops + goal delegation to sub-agents + cron NL scheduling |
| Approval loop | dangerous-command popup confirmation, pure in-process deletion |
| Token usage + analytics | session token tracking + 30-day trend + per-model distribution |
| **Context management** | `context.engine` selection + compression status + token tracking |
| **Memory management** | provider switch + vector search + layered view |
| Theme / image attachment | light/dark themes / paste-upload images via vision tool |
| Desktop packaging | pywebview native window + PyInstaller single-file EXE |

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure a model (either)
#    a) Environment variable
set HERMES_API_KEY=sk-...
#    b) Or configure a provider in HERMES_HOME/config.yaml (see .env.example)

# 3. Run
python main.py           # server mode → open http://127.0.0.1:5001
# or
python launcher.py       # desktop window mode (pywebview native window)
```

Send a message → you should see **streaming output** + **tool timeline cards** + **thinking folding**; open settings to configure models, tools, skills, MCP, etc.

## 📦 Build a Desktop EXE

```bash
python build.py          # PyInstaller single-file EXE (isolated venv + full hidden-import + HERMES_HOME handling)
```

## 🗂 Directory Layout

```
├── main.py                  # FastHTML routing: page shell + /api/* endpoints + SSE bridge
├── agent_runtime.py         # integration core: build_agent / stream_agent_chat / approval
├── hermes_config.py         # configuration: models / skills / MCP / scheduler / HERMES_HOME seeding
├── hermes_features.py       # bonus features backend (13)
├── unified_skills_client.py # unified skill marketplace (8 sources)
├── wiki_engine.py           # LLM Wiki 3-layer knowledge base
├── sessions.py              # server-side multi-session persistence
├── memory_providers.py      # memory enhancement (provider switch / vector search / layered)
├── context_provider.py      # context management (engine selection / compression / token)
├── frameworks/              # loops / delegation / commands framework
├── routes/                  # FastHTML route subpackages (chat / skills / features / misc / ...)
├── channels/                # IM channel bridge (10 connectors)
├── app_tools/               # business tool extension point (demo tool included)
├── static/                  # frontend UI (app.css / app.js / panels)
├── docs/                    # docs (mcp-server.md / integration-notes/)
├── tests/                   # test suite (offline bridge / regression)
├── bundled_skills/          # bundled demo skills
├── build.py                 # PyInstaller packaging
├── launcher.py              # pywebview desktop shell
└── 启动.bat                 # Windows one-click launcher
```

## ✅ Verification

```bash
python -m py_compile *.py          # syntax compilation
python -c "import main"            # offline importable (graceful degradation without hermes-agent)
python -m pytest tests/            # run tests (incl. offline bridge)
```

After startup, `curl /healthz`, `/api/conversations`, `/api/models` return 200.

## 🤝 Contributing

Contributions of bug fixes, integration examples, and documentation are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md). To report a security vulnerability, follow [SECURITY.md](SECURITY.md).

## 📄 License

[MIT](LICENSE) © 2026 kuailexiaozixin
