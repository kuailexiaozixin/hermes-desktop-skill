"""hermes_config.py — Hermes Desktop 通用底座的「配置与数据层」

职责（与业务完全解耦，任何桌面应用都可原样复用）：
  1. HERMES_HOME 定位：进程内 Library 模式下 AIAgent 读取 skills / config.yaml /
     memories 的根目录。frozen(EXE) → EXE 同目录 hermes_data；dev → 项目目录 .hermes_data。
  2. config.yaml 读 / 深合并写 / 全量覆盖写（删除键场景）。
  3. VENDOR_PRESETS：36 家厂商的原生 Hermes provider id + base_url + 候选模型，
     数据源为 hermes-llms-full.txt（HARD-GATE），供设置中心「模型」面板下拉。
  4. llm.json 多模型管理：增删改查 + 活动模型 + 采样/推理强度透传。
  5. 技能（skills/<name>/SKILL.md）CRUD + 启停。
  6. MCP servers 增删改查启停。
  7. Cron 定时任务（HERMES_HOME/cron/jobs.json）。
  8. materialize_hermes_env()：把上述环境一次性落地，供 main.py 启动时调用。

设计原则：尽量用原生 Hermes 概念（provider id / config.yaml 结构 / SKILL.md 目录），
非必要不自创；所有写操作都走深合并，绝不抹掉 config.yaml 中其它键。
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import sys
import threading
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover - yaml 随 hermes-agent 一起安装
    yaml = None  # type: ignore


# ============================================================================
# 1) 厂商预设（原生 Hermes provider id）
# ============================================================================
# 设计原则（尽量用原生 hermes，非必要不自创）：
# - 每个厂商的 `provider` 字段 = Hermes 的原生 provider id，write_config_yaml 据此
#   生成 model_routes，使 Anthropic / Gemini / Bedrock / MiniMax / Copilot / xAI 等
#   非 OpenAI 协议厂商走 Hermes 自己的原生适配器，而非统一伪装成 openai。
# - `base_url` 仅在厂商文档给出显式地址时填写；OAuth / AWS / 未公开端点厂商留空。
# - `models` 为 UI 默认候选（用户可改填任意模型名，保存时一并注册进 model_routes）。
# - 数据来源：hermes-llms-full.txt（HARD-GATE），行号见各条目注释。
VENDOR_PRESETS = {
    # ── 一线官方直连 ──
    "openai": {
        "label": "OpenAI（官方直连）",
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-5.4", "gpt-5.1", "gpt-5-mini", "gpt-4o"],
        "auth": "api_key", "env": "OPENAI_API_KEY",
        "note": "OpenAI 官方 API；GPT-5 系列走 Responses API。",
    },
    "anthropic": {
        "label": "Anthropic（Claude 官方）",
        "provider": "anthropic",
        "base_url": "https://api.anthropic.com",
        "models": ["claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"],
        "auth": "api_key", "env": "ANTHROPIC_API_KEY",
        "note": "Claude 官方 API；也可用 Max+OAuth（需额外额度）。(llm-full 26060-26094)",
    },
    "gemini": {
        "label": "Google Gemini（AI Studio）",
        "provider": "gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-3-pro-preview"],
        "auth": "api_key", "env": "GOOGLE_API_KEY / GEMINI_API_KEY",
        "note": "Google AI Studio；需 GOOGLE_API_KEY。(llm-full 25995)",
    },
    "xai": {
        "label": "xAI（Grok 官方）",
        "provider": "xai",
        "base_url": "https://api.x.ai/v1",
        "models": ["grok-4.5", "grok-4.20-0309-reasoning", "grok-4.20-0309-non-reasoning"],
        "auth": "api_key", "env": "XAI_API_KEY",
        "note": "xAI 官方 API（Responses API 自动推理）。grok-4 已于 2026-05-15 退役，请用 grok-4.5+。(llm-full 26235-26247)",
    },
    "xai-oauth": {
        "label": "xAI Grok OAuth（SuperGrok）",
        "provider": "xai-oauth",
        "base_url": "",
        "models": ["grok-4.5", "grok-4.20-0309-reasoning"],
        "auth": "oauth", "env": "（浏览器 OAuth，无需 key）",
        "note": "SuperGrok / Premium+ 订阅，浏览器 OAuth 登录，无需 API Key。(llm-full 25985)",
    },
    # ── 国产 / 聚合 ──
    "deepseek": {
        "label": "DeepSeek（官方）",
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        # 2026-07 起 DeepSeek 仅保留 deepseek-v4-flash（对话）与 deepseek-v4-pro（推理），
        # 旧名 deepseek-chat / deepseek-reasoner / deepseek-coder 已废弃。
        "models": ["deepseek-v4-flash", "deepseek-v4-pro"],
        "auth": "api_key", "env": "DEEPSEEK_API_KEY",
        "note": "DeepSeek 官方 API；仅 v4-flash / v4-pro。(llm-full 25993)",
    },
    "openrouter": {
        "label": "OpenRouter（聚合）",
        "provider": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "models": ["openai/gpt-5.4", "anthropic/claude-opus-4-7", "google/gemini-2.5-pro", "deepseek/deepseek-v4-flash"],
        "auth": "api_key", "env": "OPENROUTER_API_KEY",
        "note": "多厂商路由，模型用 publisher/model 命名（如 anthropic/claude-opus-4-7）。(llm-full 25974)",
    },
    "fireworks": {
        "label": "Fireworks AI",
        "provider": "fireworks",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "models": ["accounts/fireworks/models/kimi-k2p6", "accounts/fireworks/models/llama-4-maverick-instruct"],
        "auth": "api_key", "env": "FIREWORKS_API_KEY",
        "note": "原生 slash 形式模型 ID（accounts/fireworks/models/...）。(llm-full 25975,26171)",
    },
    "novita": {
        "label": "NovitaAI",
        "provider": "novita",
        "base_url": "https://api.novita.ai/openai/v1",
        "models": ["moonshotai/kimi-k2.5", "deepseek/deepseek-v3-0324"],
        "auth": "api_key", "env": "NOVITA_API_KEY",
        "note": "200+ 模型 API 网关。(llm-full 25976,26175)",
    },
    "zai": {
        "label": "Z.AI / 智谱 GLM",
        "provider": "zai",
        "base_url": "https://api.z.ai/api/paas/v4",
        "models": ["glm-5", "glm-4.6", "zai-org/GLM-5.1-FP8"],
        "auth": "api_key", "env": "GLM_API_KEY / ZAI_API_KEY",
        "note": "Z.AI / 智谱 GLM；自动探测多端点。(llm-full 25977,26179)",
    },
    "kimi-coding": {
        "label": "Kimi / Moonshot（国际）",
        "provider": "kimi-coding",
        "base_url": "https://api.moonshot.ai/v1",
        "models": ["kimi-for-coding", "kimi-k2.5"],
        "auth": "api_key", "env": "KIMI_API_KEY",
        "note": "Moonshot 国际端点 api.moonshot.ai。(llm-full 25978,26183)",
    },
    "kimi-coding-cn": {
        "label": "Kimi / Moonshot（中国）",
        "provider": "kimi-coding-cn",
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["kimi-k2.5"],
        "auth": "api_key", "env": "KIMI_CN_API_KEY",
        "note": "Moonshot 中国端点 api.moonshot.cn。(llm-full 25979,26187)",
    },
    "arcee": {
        "label": "Arcee AI",
        "provider": "arcee",
        "base_url": "https://api.arcee.ai/api/v1",
        "models": ["trinity-large-thinking"],
        "auth": "api_key", "env": "ARCEEAI_API_KEY",
        "note": "Trinity 系列模型。(llm-full 25980,26211)",
    },
    "gmi": {
        "label": "GMI Cloud",
        "provider": "gmi",
        "base_url": "https://api.gmi-serving.com/v1",
        "models": ["zai-org/GLM-5.1-FP8", "deepseek-ai/DeepSeek-V3.2"],
        "auth": "api_key", "env": "GMI_API_KEY",
        "note": "GMI Cloud 开放/推理模型。(llm-full 25981,26216)",
    },
    "minimax": {
        "label": "MiniMax（国际）",
        "provider": "minimax",
        "base_url": "https://api.minimax.io/anthropic",
        "models": ["MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
        "auth": "api_key", "env": "MINIMAX_API_KEY",
        "note": "MiniMax 国际端点（Anthropic 线协议）。(llm-full 25982,26191)",
    },
    "minimax-cn": {
        "label": "MiniMax（中国）",
        "provider": "minimax-cn",
        "base_url": "https://api.minimaxi.com/anthropic",
        "models": ["MiniMax-M2.7"],
        "auth": "api_key", "env": "MINIMAX_CN_API_KEY",
        "note": "MiniMax 中国端点（Anthropic 线协议）。(llm-full 25983,26195)",
    },
    "minimax-oauth": {
        "label": "MiniMax（OAuth）",
        "provider": "minimax-oauth",
        "base_url": "",
        "models": ["MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
        "auth": "oauth", "env": "（浏览器 OAuth，无需 key）",
        "note": "MiniMax-M2.7 浏览器 OAuth，无需 API Key。(llm-full 25985->26003,26404)",
    },
    "alibaba": {
        "label": "阿里云百炼 / DashScope",
        "provider": "alibaba",
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen3.5-plus", "qwen3-coder-plus", "qwen-max"],
        "auth": "api_key", "env": "DASHSCOPE_API_KEY",
        "note": "通义千问（Qwen）系列，DashScope 端点。(llm-full 25986,26199)",
    },
    "alibaba-coding-plan": {
        "label": "阿里云编程计划（Coding Plan）",
        "provider": "alibaba-coding-plan",
        "base_url": "https://coding-intl.dashscope.aliyuncs.com/v1",
        "models": ["qwen3-coder-plus"],
        "auth": "api_key", "env": "DASHSCOPE_API_KEY（与 alibaba 共用）",
        "note": "独立计费 SKU，不同端点；复用 DASHSCOPE_API_KEY。(llm-full 25987,26386)",
    },
    "huggingface": {
        "label": "Hugging Face",
        "provider": "huggingface",
        "base_url": "https://router.huggingface.co/v1",
        "models": ["Qwen/Qwen3.5-397B-A17B", "deepseek-ai/DeepSeek-V3.2"],
        "auth": "api_key", "env": "HF_TOKEN",
        "note": "20+ 开放模型统一路由，需开启 Inference Providers 权限。(llm-full 25994,26500)",
    },
    "qwen-oauth": {
        "label": "Qwen Portal（OAuth）",
        "provider": "qwen-oauth",
        "base_url": "https://portal.qwen.ai/v1",
        "models": ["qwen3-coder-plus", "qwen-max"],
        "auth": "oauth", "env": "（浏览器 PKCE OAuth，无需 key）",
        "note": "阿里 Qwen Portal 消费者端 OAuth 登录。(llm-full 26002,26360)",
    },
    "xiaomi": {
        "label": "Xiaomi MiMo",
        "provider": "xiaomi",
        "base_url": "",
        "models": ["mimo-v2-pro"],
        "auth": "api_key", "env": "XIAOMI_API_KEY",
        "note": "小米 MiMo 模型，需填写 Base URL（如有）。(llm-full 25989,26203)",
    },
    "tencent-tokenhub": {
        "label": "腾讯 TokenHub",
        "provider": "tencent-tokenhub",
        "base_url": "",
        "models": ["hy3-preview"],
        "auth": "api_key", "env": "TOKENHUB_API_KEY",
        "note": "腾讯混元 TokenHub，需填写 Base URL（如有）。(llm-full 25990,26207)",
    },
    "nvidia": {
        "label": "NVIDIA NIM",
        "provider": "nvidia",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "models": ["nvidia/nemotron-3-super-120b-a12b"],
        "auth": "api_key", "env": "NVIDIA_API_KEY",
        "note": "build.nvidia.com 托管 Nemotron 等模型。(llm-full 26000,26436)",
    },
    "ollama-cloud": {
        "label": "Ollama Cloud",
        "provider": "ollama-cloud",
        "base_url": "https://ollama.com/v1",
        "models": ["gpt-oss:120b", "qwen3-coder:480b-cloud", "glm-4.6:cloud"],
        "auth": "api_key", "env": "OLLAMA_API_KEY",
        "note": "托管版 Ollama，模型目录动态发现。(llm-full 26001,26294)",
    },
    "lmstudio": {
        "label": "LM Studio（本地）",
        "provider": "lmstudio",
        "base_url": "http://localhost:1234/v1",
        "models": ["qwen3-coder", "llama-3.3-70b", "local-model"],
        "auth": "api_key", "env": "LM_API_KEY（可选）",
        "note": "本地 OpenAI 兼容接口，默认无 key。(llm-full 26005)",
    },
    "kilocode": {
        "label": "Kilo Code",
        "provider": "kilocode",
        "base_url": "https://api.kilo.ai/api/gateway",
        "models": ["kilo-code"],
        "auth": "api_key", "env": "KILOCODE_API_KEY",
        "note": "KiloCode 托管模型，可输入任意模型名。(llm-full 25988)",
    },
    "opencode-zen": {
        "label": "OpenCode Zen",
        "provider": "opencode-zen",
        "base_url": "",
        "models": ["opencode-zen"],
        "auth": "api_key", "env": "OPENCODE_ZEN_API_KEY",
        "note": "按需付费精选模型，需填写 Base URL（如有）。(llm-full 25991)",
    },
    "opencode-go": {
        "label": "OpenCode Go",
        "provider": "opencode-go",
        "base_url": "",
        "models": ["opencode-go"],
        "auth": "api_key", "env": "OPENCODE_GO_API_KEY",
        "note": "$10/月订阅开放模型，需填写 Base URL（如有）。(llm-full 25992)",
    },
    # ── GitHub / Copilot / Codex ──
    "copilot": {
        "label": "GitHub Copilot（直连）",
        "provider": "copilot",
        "base_url": "https://api.githubcopilot.com",
        "models": ["gpt-5.4", "claude-opus-4-7", "gemini-2.5-pro"],
        "auth": "api_key", "env": "COPILOT_GITHUB_TOKEN / GH_TOKEN",
        "note": "Copilot 订阅，支持 GPT-5.x / Claude / Gemini。(llm-full 26100-26156)",
    },
    "copilot-acp": {
        "label": "GitHub Copilot ACP",
        "provider": "copilot-acp",
        "base_url": "",
        "models": ["copilot-acp"],
        "auth": "cli", "env": "（需本地 copilot CLI + copilot login）",
        "note": "拉起本地 copilot CLI 子进程，需先 copilot login。(llm-full 26145-26150)",
    },
    "openai-codex": {
        "label": "OpenAI Codex（ChatGPT OAuth）",
        "provider": "openai-codex",
        "base_url": "",
        "models": ["gpt-5.3-codex", "gpt-5.4", "gpt-5.5"],
        "auth": "oauth", "env": "（ChatGPT 设备码登录，无需 key）",
        "note": "ChatGPT OAuth 使用 Codex 模型，设备码登录。(llm-full 25970,4246)",
    },
    "nous": {
        "label": "Nous Portal（订阅网关）",
        "provider": "nous",
        "base_url": "",
        "models": ["claude-opus-4-7", "gpt-5.4", "gemini-2.5-pro", "deepseek-v4-flash"],
        "auth": "oauth", "env": "（订阅 OAuth，无需逐家 key）",
        "note": "一次 OAuth 覆盖 300+ 前沿模型 + 工具网关。(llm-full 25969,26015)",
    },
    # ── 云厂商原生 ──
    "bedrock": {
        "label": "AWS Bedrock",
        "provider": "bedrock",
        "base_url": "",
        "models": ["us.anthropic.claude-sonnet-4-6", "us.anthropic.claude-opus-4-7"],
        "auth": "aws", "env": "（boto3 链：AWS_PROFILE / AWS_ACCESS_KEY_ID 等）",
        "note": "走 Converse API，用 AWS SDK 凭据，无需 API Key。(llm-full 25999,26303)",
    },
    "azure-foundry": {
        "label": "Azure AI Foundry",
        "provider": "azure-foundry",
        "base_url": "",
        "models": ["gpt-5.4", "gpt-4o"],
        "auth": "api_key", "env": "AZURE_FOUNDRY_API_KEY + AZURE_FOUNDRY_BASE_URL",
        "note": "需填写完整端点 <resource>.openai.azure.com/openai/v1。(llm-full 25998)",
    },
    # ── 自定义 ──
    "custom": {
        "label": "自定义 / Custom Endpoint",
        "provider": "custom",
        "base_url": "",
        "models": ["custom-model"],
        "auth": "api_key", "env": "（视端点而定，可留空）",
        "note": "任意 OpenAI 兼容端点（vLLM / SGLang / Ollama / 本地），需填写 Base URL。(llm-full 26006)",
    },
}

# 上游路由兜底 provider：仅当 vendor 不在 VENDOR_PRESETS 时使用。
_DEFAULT_PROVIDER = "openai"

# 出厂默认厂商 / 模型（用户未配置时的占位，无 key 时前端会提示去设置）
DEFAULT_VENDOR = "deepseek"
DEFAULT_MODEL = "deepseek-v4-flash"

# 默认技能目录：首次启动整目录拷贝到 HERMES_HOME/skills/<name>/（原生 SKILL.md 结构）
DEFAULT_SKILLS_DIR = Path(__file__).resolve().parent / "default_skills"
# 阻止 Hermes 启动时把内置示例技能塞进我们的技能集
NO_BUNDLED_MARKER = ".no-bundled-skills"

_lock = threading.Lock()
_CRON_LOCK = threading.Lock()


# ============================================================================
# 2) 路径
# ============================================================================
def get_hermes_home() -> Path:
    """返回 Hermes 数据目录（必须可写、持久化，不能是只读的 _MEIPASS）。

    frozen：EXE 同目录下的 hermes_data（随 EXE 持久，用户运行数据）。
    dev：本示例目录下的 .hermes_data。
    可用环境变量 HERMES_DESKTOP_HOME 覆盖（便于多实例/测试隔离）。
    """
    override = os.environ.get("HERMES_DESKTOP_HOME")
    if override:
        base = Path(override)
    elif getattr(sys, "frozen", False):
        base = Path(sys.executable).parent / "hermes_data"
    else:
        base = Path(__file__).resolve().parent / ".hermes_data"
    base.mkdir(parents=True, exist_ok=True)
    return base


def project_root() -> Path:
    """相对路径的解析根：frozen = EXE 同目录；dev = 本示例目录。

    所有文件工具的相对路径统一相对此根解析，保证 `output/xxx` 始终落到产物目录，
    而不随进程 cwd 漂移。
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def output_dir() -> Path:
    d = project_root() / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ============================================================================
# 3) config.yaml 读写
# ============================================================================
def _deep_merge(base: dict, override: dict) -> dict:
    """递归深合并（override 优先）：把局部补丁并进现有 config.yaml，
    避免保存模型时把 mcp_servers / toolsets / skills 等配置抹掉。"""
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def read_config_yaml(home: Path | None = None) -> dict:
    """读取 <HERMES_HOME>/config.yaml，不存在或损坏返回 {}。

    读路径优先级：优先 yaml.safe_load（生产环境，pyyaml 随 hermes-agent 安装）；
    若 pyyaml 缺失，则回退 json.loads —— 与 _write_config_yaml_full 的 JSON 分支
    闭环，保证「写成功 → 读回」不丢配置（消除无 yaml 运行时静默返回 {} 的隐患）。
    """
    p = (home or get_hermes_home()) / "config.yaml"
    if not p.exists():
        return {}
    raw = p.read_text(encoding="utf-8")
    try:
        if yaml is not None:
            return yaml.safe_load(raw) or {}
    except Exception:
        pass
    # pyyaml 缺失时的回退：配置文件由此处的 JSON 分支写出，对应 json.loads。
    try:
        return json.loads(raw) or {}
    except Exception:
        return {}


def update_config_yaml(home: Path | None, patch: dict) -> dict:
    """把局部补丁深合并进现有 config.yaml（保留其它键），写回并返回合并后全量。"""
    h = home or get_hermes_home()
    merged = _deep_merge(read_config_yaml(h), patch)
    _write_config_yaml_full(h, merged)
    return merged


def _write_config_yaml_full(home: Path, cfg: dict) -> None:
    """整体覆盖写 config.yaml（用于需要删除键的场景，深合并无法表达删除）。"""
    if yaml is not None:
        text = yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)
    else:
        # 无 pyyaml 时的回退：用 JSON（与 read_config_yaml 的 JSON 回退解析闭环，
        # 避免「写成功、读空」静默丢配置；生产环境走上面 yaml 分支，不受影响）。
        text = json.dumps(cfg, ensure_ascii=False, indent=2)
    (home / "config.yaml").write_text(text, encoding="utf-8")


# ── .env 读写（作用域限定在示例 HERMES_HOME，不触碰真实 ~/.hermes）────────
# 对齐真实 hermes_cli.config.get_env_value / save_env_value 的落盘位置：
# 插件 requires_env 声明的变量最终由 Hermes 从 HERMES_HOME/.env 读取。
def get_env_value(name: str, home: Path | None = None) -> str | None:
    """读取 <HERMES_HOME>/.env 中某个变量的值（dotenv 风格，忽略注释与空行）。"""
    p = (home or get_hermes_home()) / ".env"
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        if k.strip() == name:
            return v.strip().strip('"').strip("'")
    return None


def set_env_value(name: str, value: str, home: Path | None = None) -> None:
    """把某个变量写入 <HERMES_HOME>/.env（已存在则更新，不存在则追加）。"""
    name = str(name).strip()
    if not name:
        raise ValueError("环境变量名不能为空")
    p = (home or get_hermes_home()) / ".env"
    lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    out, replaced = [], False
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s and s.partition("=")[0].strip() == name:
            out.append(f"{name}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{name}={value}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(out) + "\n", encoding="utf-8")


def write_model_routes(home: Path | None = None, cfg: dict | None = None) -> None:
    """把已配置模型的路由记录进 config.yaml（Library 模式下的中性记录）。

    Library 模式说明：Agent 由 agent_runtime.build_agent 直接把 provider/model/
    api_key/base_url 传给 AIAgent 构造器，**不再经 API Server 的 model_routes 选路**。
    这里写入的 model_routes 仅作「已配置模型」的持久化记录（审计/未来复用），
    不写 host/port/key/cors 等网关网络键（Library 模式无监听端口）。
    """
    h = home or get_hermes_home()
    models = get_models_list(cfg)
    model_routes: dict = {}
    for m in models:
        vendor = m.get("vendor") or DEFAULT_VENDOR
        preset = VENDOR_PRESETS.get(vendor, {})
        route = {"model": m.get("model") or m["id"],
                 "provider": preset.get("provider", vendor)}
        if m.get("api_key"):
            route["api_key"] = m["api_key"]
        if m.get("base_url"):
            route["base_url"] = m["base_url"]
        model_routes[m["id"]] = route
    update_config_yaml(h, {"platforms": {"api_server": {"extra": {
        "model_name": models[0]["id"], "model_routes": model_routes}}}})


# ── 联网搜索后端（Hermes Library 真实 schema，依据 hermes-llms-full.txt §Web Search Backends / Web Search Provider Plugins） ──
# 真实配置键（优先级从高到低）：
#   web_search  : web.search_backend  >  web.backend  >  按环境变量自动探测
#   web_extract : web.extract_backend >  web.backend  >  按环境变量自动探测
# 8 个内置后端（均随 hermes-agent 以插件形式内置，无需额外安装）：
#   firecrawl(默认,需 KEY) / searxng(免费,需 SEARXNG_URL 自托管地址) / brave-free(免费额度,需 BRAVE_SEARCH_API_KEY)
#   / ddgs(免费无需任何 Key,首次自动安装 SDK) / tavily / exa / parallel(均需 KEY) / xai(需 XAI_API_KEY,手动 opt-in)
#   - 未显式设置时 Hermes 按可用 Key 自动探测；xai 不参与自动探测，须显式 web.backend: xai。
#   - 唯一「零配置即免费」的后端是 ddgs（无需任何 Key/URL）；searxng 也免费但需自托管 SEARXNG_URL。
_WEB_BACKENDS = ("firecrawl", "searxng", "brave-free", "ddgs", "tavily", "exa", "parallel", "xai")
# 后端 -> 所需环境变量（None 表示零凭据：ddgs）
_WEB_BACKEND_KEY_ENV = {
    "firecrawl": "FIRECRAWL_API_KEY",   # 或 FIRECRAWL_API_URL（自托管时 Key 可省略）
    "searxng": "SEARXNG_URL",           # 自托管实例地址（非 API Key）
    "brave-free": "BRAVE_SEARCH_API_KEY",
    "tavily": "TAVILY_API_KEY",
    "exa": "EXA_API_KEY",
    "parallel": "PARALLEL_API_KEY",
    "xai": "XAI_API_KEY",
    "ddgs": None,
}
# 零凭据后端（无需任何 Key/URL）：ddgs
_WEB_NO_KEY_BACKENDS = {"ddgs"}
# 仅需「实例地址」(SEARXNG_URL) 而非 API Key 的后端
_WEB_URL_BACKENDS = {"searxng"}


def ensure_default_web_search_backend(home: Path | None = None) -> None:
    """保证开箱即用的免费联网搜索（零配置）。

    若用户未显式配置任何后端（web.search_backend / web.backend 均无），
    则默认写入 web.search_backend: ddgs——ddgs 是 Hermes 内置、无需任何
    API Key / URL 的后端（首次使用自动安装其 SDK），从而实现「零配置免费联网」。
    已配置任一后端的用户设置绝不覆盖（深合并，保留其它 web.* 键）。
    """
    h = home or get_hermes_home()
    cfg = read_config_yaml(h)
    web = cfg.get("web")
    if web is None:
        update_config_yaml(h, {"web": {"search_backend": "ddgs"}})
        return
    existing = (web.get("search_backend") or web.get("backend") or "").strip()
    if not existing:
        update_config_yaml(h, {"web": {"search_backend": "ddgs"}})


def get_web_search_status(home: Path | None = None) -> dict:
    """返回联网搜索后端真实状态：{ok, label, backend, needs_key, key_env, ready, message}。

    读取 Hermes 真实配置键 web.search_backend / web.backend（不再使用虚构的
    web.search_provider）。未配置时说明将自动探测（默认 firecrawl，需 Key），
    并提示零配置免费的 ddgs 方案。
    """
    cfg = read_config_yaml(home)
    web = (cfg.get("web") or {}) or {}
    backend = (web.get("search_backend") or web.get("backend") or "").strip()
    if not backend:
        return {"ok": True, "label": "未配置（自动探测）", "backend": "",
                "needs_key": True, "key_env": "FIRECRAWL_API_KEY", "ready": False,
                "message": "未配置后端：Hermes 将按可用 Key 自动选择（默认 firecrawl，"
                           "需 FIRECRAWL_API_KEY）。零配置免费方案：ddgs 无需任何 Key"
                           "（首次自动安装 SDK）；或自托管 SearXNG 并填 SEARXNG_URL。"}
    key_env = _WEB_BACKEND_KEY_ENV.get(backend)
    if key_env is None:
        # ddgs：零凭据
        ready = True
        needs_key = False
        label = backend
    elif key_env == "SEARXNG_URL":
        ready = bool(os.environ.get("SEARXNG_URL"))
        needs_key = False
        label = backend + ("" if ready else "（未就绪：需 SEARXNG_URL）")
    else:
        ready = bool(os.environ.get(key_env))
        needs_key = True
        label = backend + ("" if ready else f"（未就绪：需 {key_env}）")
    return {"ok": True, "label": label, "backend": backend,
            "needs_key": needs_key, "key_env": key_env or "", "ready": ready,
            "message": "" if ready else f"后端 {backend} 未就绪：需配置 {key_env}。"}


# ============================================================================
# 4) 模型管理（llm.json）
# ============================================================================
def get_llm_config() -> dict:
    """读取用户 LLM 配置；缺省返回默认厂商占位（无 key，原生 provider id）。"""
    p = get_hermes_home() / "llm.json"
    if p.exists():
        try:
            cfg = json.loads(p.read_text(encoding="utf-8"))
            vendor = cfg.get("vendor", DEFAULT_VENDOR)
            cfg.setdefault("vendor", vendor)
            cfg.setdefault("provider",
                           VENDOR_PRESETS.get(vendor, {}).get("provider", vendor))
            return cfg
        except Exception:
            pass
    preset = VENDOR_PRESETS.get(DEFAULT_VENDOR, {})
    return {
        "vendor": DEFAULT_VENDOR,
        "provider": preset.get("provider", DEFAULT_VENDOR),
        "base_url": preset.get("base_url", ""),
        "api_key": "",
        "model": DEFAULT_MODEL,
    }


def save_llm_config(cfg: dict) -> None:
    p = get_hermes_home() / "llm.json"
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def _model_entry_id(m: dict) -> str:
    return (m.get("model") or m.get("id") or "").strip()


def get_models_list(cfg: dict | None = None) -> list[dict]:
    """返回已配置模型列表；兼容旧版单模型 llm.json（无 models 列表时用顶层字段构造）。"""
    if cfg is None:
        cfg = get_llm_config()
    models = cfg.get("models")
    if isinstance(models, list) and models:
        out: list[dict] = []
        for m in models:
            if not isinstance(m, dict):
                continue
            mid = _model_entry_id(m)
            if not mid:
                continue
            m = dict(m)
            m["id"] = mid
            m["model"] = mid
            m.setdefault("vendor", cfg.get("vendor", DEFAULT_VENDOR))
            if not m.get("base_url"):
                m["base_url"] = cfg.get("base_url", "")
            if not m.get("api_key"):
                m["api_key"] = cfg.get("api_key", "")
            out.append(m)
        if out:
            return out
    mid = _model_entry_id(cfg) or DEFAULT_MODEL
    return [{
        "id": mid,
        "vendor": cfg.get("vendor", DEFAULT_VENDOR),
        "base_url": cfg.get("base_url", ""),
        "api_key": cfg.get("api_key", ""),
        "model": mid,
    }]


def _normalize_model_entry(m: dict) -> dict:
    """把一条模型记录归一化为 llm.json 的持久化形态。

    固定保留 id/vendor/model/base_url/api_key；其余可选字段做类型校正后保留，
    使前端设置的逐模型参数（温度、Top-P、停止序列、输出格式、上下文长度、
    能力开关等）在「保存 → 重载」后原样往返，避免「设置后消失」的数据丢失。
    """
    mid = _model_entry_id(m) or DEFAULT_MODEL
    entry = {
        "id": mid,
        "vendor": m.get("vendor") or DEFAULT_VENDOR,
        "base_url": m.get("base_url") or "",
        "api_key": m.get("api_key") or "",
        "model": mid,
    }
    # 采样/格式类（经 AIAgent.request_overrides 透传给 provider）
    if m.get("max_tokens"):
        try:
            v = int(m["max_tokens"])
            if v > 0:
                entry["max_tokens"] = v
        except (TypeError, ValueError):
            pass
    if m.get("reasoning_effort"):
        entry["reasoning_effort"] = m["reasoning_effort"]
    if isinstance(m.get("reasoning_config"), dict):
        entry["reasoning_config"] = m["reasoning_config"]
    for f in ("temperature", "top_p"):
        v = m.get(f)
        if v not in (None, ""):
            try:
                entry[f] = float(v)
            except (TypeError, ValueError):
                pass
    if m.get("top_logprobs") not in (None, ""):
        try:
            entry["top_logprobs"] = int(m["top_logprobs"])
        except (TypeError, ValueError):
            pass
    if m.get("stop_sequences") not in (None, ""):
        entry["stop_sequences"] = str(m["stop_sequences"])
    if m.get("response_format") not in (None, ""):
        entry["response_format"] = str(m["response_format"])
    for f in ("input_max_tokens", "output_max_tokens"):
        v = m.get(f)
        if v not in (None, ""):
            try:
                entry[f] = int(v)
            except (TypeError, ValueError):
                pass
    # 能力/开关类（描述性元数据，仅持久化，不影响内核行为）
    for cap in ("tools", "vision", "thinking", "custom_protocol", "web_search"):
        if cap in m:
            entry[cap] = bool(m[cap])
    return entry


def save_models_list(models: list[dict], active_id: str | None = None) -> dict:
    """以 models 列表为唯一真相写入 llm.json，并镜像 active 条目到顶层字段。

    每条模型的逐模型配置（温度、Top-P、停止序列、输出格式、上下文长度、
    能力开关等）见 ``_normalize_model_entry`` —— 一并持久化，保存后重载不丢失。
    """
    models = [dict(m) for m in (models or []) if isinstance(m, dict)]
    norm = [_normalize_model_entry(m) for m in models]
    if not norm:
        norm = [{"id": DEFAULT_MODEL, "vendor": DEFAULT_VENDOR,
                 "base_url": VENDOR_PRESETS.get(DEFAULT_VENDOR, {}).get("base_url", ""),
                 "api_key": "", "model": DEFAULT_MODEL}]
    if active_id is None or not any(m["id"] == active_id for m in norm):
        active_id = norm[0]["id"]
    active = next((m for m in norm if m["id"] == active_id), norm[0])
    cfg = {
        "vendor": active.get("vendor", DEFAULT_VENDOR),
        "provider": VENDOR_PRESETS.get(active.get("vendor", DEFAULT_VENDOR), {}).get(
            "provider", active.get("vendor", DEFAULT_VENDOR)),
        "base_url": active.get("base_url", ""),
        "api_key": active.get("api_key", ""),
        "model": active.get("model", active["id"]),
        "models": norm,
    }
    save_llm_config(cfg)
    try:
        write_model_routes(cfg=cfg)
    except Exception:
        pass
    return cfg


def get_active_model_cfg(model_id: str | None = None) -> dict:
    """返回用于构造 AIAgent 的模型配置 dict。

    {vendor, provider, base_url, api_key, model, max_tokens?, reasoning_config?,
     温度/Top-P/停止序列/输出格式/上下文长度（透传 provider）, 能力开关（描述性元数据）}
    - model_id 指定时，从已配置模型列表中按 id / model 名匹配；
    - 未指定或匹配不到时，回退 llm.json 顶层 active 模型。
    provider 统一解析为厂商原生 Hermes provider id（VENDOR_PRESETS[vendor].provider）。
    """
    models = get_models_list()
    chosen: dict | None = None
    if model_id:
        _matches = [m for m in models
                    if m.get("id") == model_id or m.get("model") == model_id]
        if _matches:
            # 同 id 可能有多条（如默认空 key 条目 + 用户配置条目）：优先选带
            # api_key 的，避免「空 key 默认条目」遮蔽真实配置导致对话 401。
            chosen = next((m for m in _matches if m.get("api_key")), _matches[0])
    if chosen is None:
        active = get_llm_config()
        mid = (active.get("model") or "").strip()
        _matches = [m for m in models
                    if m.get("id") == mid or m.get("model") == mid]
        if _matches:
            chosen = next((m for m in _matches if m.get("api_key")), _matches[0])
        if chosen is None:
            chosen = {
                "vendor": active.get("vendor", DEFAULT_VENDOR),
                "base_url": active.get("base_url", ""),
                "api_key": active.get("api_key", ""),
                "model": mid or DEFAULT_MODEL,
            }
    vendor = chosen.get("vendor") or DEFAULT_VENDOR
    cfg = {
        "vendor": vendor,
        "provider": VENDOR_PRESETS.get(vendor, {}).get("provider", vendor or _DEFAULT_PROVIDER),
        "base_url": chosen.get("base_url") or "",
        "api_key": chosen.get("api_key") or "",
        "model": chosen.get("model") or chosen.get("id") or DEFAULT_MODEL,
    }
    if chosen.get("max_tokens"):
        try:
            cfg["max_tokens"] = int(chosen["max_tokens"])
        except (TypeError, ValueError):
            pass
    _rc = reasoning_effort_to_config(chosen)
    if _rc:
        cfg["reasoning_config"] = _rc
    # 逐模型采样/格式参数：供 build_agent 经 AIAgent.request_overrides 透传给 provider
    for f in ("temperature", "top_p", "top_logprobs", "stop_sequences", "response_format",
              "input_max_tokens", "output_max_tokens"):
        if chosen.get(f) not in (None, ""):
            cfg[f] = chosen[f]
    # 能力/开关类元数据（描述性，供 UI/客户端逻辑使用，不改变内核行为）
    for cap in ("tools", "vision", "thinking", "custom_protocol", "web_search"):
        if cap in chosen:
            cfg[cap] = chosen[cap]
    return cfg


def reasoning_effort_to_config(model: dict) -> "dict | None":
    """把模型的推理强度配置转换成 AIAgent 接受的 ``reasoning_config`` 字典。

    Hermes Library 的 ``AIAgent.__init__`` 只认 ``reasoning_config``（dict），
    而模型设置 UI 存的是 ``reasoning_effort``（字符串，如 ``"high"``）。
    本函数负责两者衔接，避免「推理强度」下拉框成为摆设：

    - 若模型已显式给出 ``reasoning_config``（dict），优先用它（更具体）；
    - 否则若设有 ``reasoning_effort`` 字符串，转成 ``{"effort": <level>}``；
    - 都没有则返回 ``None``（交给 Hermes 走默认 ``medium``）。

    返回的 dict 形状 ``{"effort": "<none|minimal|low|medium|high|xhigh|max|ultra>"}``
    与批量运行（``hermes_features.batch_run``）使用的约定一致。
    """
    rc = model.get("reasoning_config")
    if isinstance(rc, dict) and rc:
        return dict(rc)
    re_ = model.get("reasoning_effort")
    if re_:
        return {"effort": str(re_)}
    return None


# ── Agent 设置（HERMES_HOME/agent_settings.json） ─────────────────────────
def read_agent_settings(home: Path | None = None) -> dict:
    p = (home or get_hermes_home()) / "agent_settings.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def write_agent_settings(patch: dict, home: Path | None = None) -> dict:
    h = home or get_hermes_home()
    cur = read_agent_settings(h)
    merged = _deep_merge(cur, patch or {})
    (h / "agent_settings.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged


def get_loop_max_iterations() -> int | None:
    """用户设置的 Agent Loop 最大迭代次数（未设置返回 None → Hermes 默认 90）。"""
    v = (read_agent_settings().get("loop") or {}).get("max_iterations")
    try:
        v = int(v)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


# ============================================================================
# 5) 技能（原生 SKILL.md 目录结构）
# ============================================================================
def ensure_default_skills(home: Path | None = None) -> Path:
    """确保 HERMES_HOME/skills 下存在内置默认技能（原生 SKILL.md 目录结构）。"""
    home = home or get_hermes_home()
    skills_dir = home / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    marker = home / NO_BUNDLED_MARKER
    if not marker.exists():
        try:
            marker.write_text("", encoding="utf-8")
        except Exception:
            pass
    if DEFAULT_SKILLS_DIR.exists():
        for d in sorted(DEFAULT_SKILLS_DIR.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                dest = skills_dir / d.name
                if not dest.exists():
                    shutil.copytree(d, dest)
    return skills_dir


def _skills_dir(home: Path | None = None) -> Path:
    return (home or get_hermes_home()) / "skills"


def _fm_scalar(val: str):
    """frontmatter 标量/内联列表归一：去引号；[a, b] 拆为列表。"""
    v = val.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_fm_scalar(x.strip()) for x in inner.split(",")]
    if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
        return v[1:-1]
    return v


def _parse_simple_frontmatter(block: str) -> dict:
    """内建极简 frontmatter 解析（pyyaml 缺失时的防御性回退）。

    支持：标量、内联列表 [a, b]、块列表（- item）。
    wiki 的 frontmatter 由 _serialize_frontmatter 写入，本函数保证「写→读」闭环不丢元数据。
    """
    meta: dict = {}
    cur_key: str | None = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if cur_key is not None and line.lstrip().startswith("- "):
            item = line.lstrip()[2:].strip()
            if isinstance(meta.get(cur_key), list):
                meta[cur_key].append(_fm_scalar(item))  # type: ignore[arg-type]
            continue
        m = re.match(r"^([A-Za-z0-9_\-]+)\s*:\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            cur_key = key
            meta.setdefault(key, [])
        else:
            cur_key = None
            meta[key] = _fm_scalar(val)
    return meta


def _parse_frontmatter(text: str):
    """解析 YAML frontmatter，返回 (meta:dict, body:str)。

    优先用 PyYAML（生产环境随 hermes-agent 安装）；若 pyyaml 缺失或解析异常，
    回退到内建轻量解析器，保证「写成功 → 读回」不丢元数据
    （消除无 yaml 运行时静默返回 {} 的隐患，防御 hermes-agent 版本/venv 变化）。
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    block, body = parts[1], parts[2].lstrip("\n")
    if yaml is not None:
        try:
            meta = yaml.safe_load(block)
            return (meta if isinstance(meta, dict) else {}), body
        except Exception:
            pass  # 解析失败也回退内建解析，避免整段元数据丢失
    return _parse_simple_frontmatter(block), body


def _dump_skill(meta: dict, body: str) -> str:
    head = "---\n" + "".join(f"{k}: {v}\n" for k, v in meta.items()) + "---\n"
    return head + body


def _serialize_frontmatter(meta: dict) -> str:
    """把 frontmatter dict 序列化回 YAML 头（与 _parse_frontmatter 互逆）。"""
    if yaml:
        import io
        buf = io.StringIO()
        yaml.safe_dump(meta, buf, allow_unicode=True, sort_keys=False, default_flow_style=False)
        return "---\n" + buf.getvalue().rstrip("\n") + "\n---\n"
    # 退化路径：无 yaml 时手工拼（仅标量/列表）
    lines = []
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(str(x) for x in v)}]")
        else:
            lines.append(f"{k}: {v}")
    return "---\n" + "\n".join(lines) + "\n---\n"


def get_disabled_skills_set(home: Path | None = None, platform: str = "api_server") -> set:
    cfg = read_config_yaml(home)
    skills_cfg = cfg.get("skills") or {}
    disabled = set(skills_cfg.get("disabled") or [])
    disabled |= set((skills_cfg.get("platform_disabled") or {}).get(platform) or [])
    return disabled


def set_skill_enabled(name: str, enabled: bool, home: Path | None = None,
                      platform: str = "api_server") -> None:
    """启用/关闭某个技能（写 config.yaml，即时生效）。"""
    h = home or get_hermes_home()
    cfg = read_config_yaml(h)
    skills_cfg = dict(cfg.get("skills") or {})
    disabled = set(skills_cfg.get("disabled") or [])
    pd = dict(skills_cfg.get("platform_disabled") or {})
    plat_disabled = set(pd.get(platform) or [])
    if enabled:
        disabled.discard(name)
        plat_disabled.discard(name)
    else:
        plat_disabled.add(name)
    skills_cfg["disabled"] = sorted(disabled)
    pd[platform] = sorted(plat_disabled)
    skills_cfg["platform_disabled"] = pd
    cfg["skills"] = skills_cfg
    _write_config_yaml_full(h, cfg)
    # 让 Hermes 立刻重建技能系统提示词缓存
    try:
        from agent.prompt_builder import clear_skills_system_prompt_cache
        clear_skills_system_prompt_cache(clear_snapshot=True)
    except Exception:
        pass


def list_skills(home: Path | None = None) -> list[dict]:
    """读取 HERMES_HOME/skills 下所有原生技能（含 enabled 状态）。"""
    out: list[dict] = []
    skills_dir = _skills_dir(home)
    if skills_dir.exists():
        for d in sorted(skills_dir.iterdir()):
            skill_md = d / "SKILL.md"
            if d.is_dir() and skill_md.exists():
                try:
                    text = skill_md.read_text(encoding="utf-8")
                except Exception:
                    continue
                meta, body = _parse_frontmatter(text)
                name = meta.get("name") or d.name
                out.append({
                    "id": d.name, "name": name, "title": name,
                    "description": meta.get("description", ""),
                    "category": meta.get("category", ""),
                    "content": body, "path": str(skill_md),
                })
    disabled = get_disabled_skills_set(home, "api_server")
    for s in out:
        s["enabled"] = s["name"] not in disabled and s["id"] not in disabled
    return out


def read_skill(name: str, home: Path | None = None) -> dict | None:
    target = _skills_dir(home) / name / "SKILL.md"
    if not target.exists():
        return None
    meta, body = _parse_frontmatter(target.read_text(encoding="utf-8"))
    return {"id": name, "name": meta.get("name", name),
            "description": meta.get("description", ""),
            "category": meta.get("category", ""), "body": body}


def create_skill(name: str, description: str, body: str, category: str = "",
                 home: Path | None = None) -> dict:
    """新建一个原生技能目录 skills/<name>/SKILL.md。"""
    skills_dir = _skills_dir(home or get_hermes_home())
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", (name or "").strip().lower()) or "skill"
    target = skills_dir / safe
    target.mkdir(parents=True, exist_ok=True)
    meta = {"name": (name or "").strip(), "description": (description or "").strip()}
    if category:
        meta["category"] = category
    (target / "SKILL.md").write_text(_dump_skill(meta, body or ""), encoding="utf-8")
    return {"ok": True, "id": safe, "name": (name or "").strip()}


def update_skill(name: str, description: str | None = None, body: str | None = None,
                 category: str | None = None, home: Path | None = None) -> dict:
    target = _skills_dir(home) / name / "SKILL.md"
    if not target.exists():
        return {"ok": False, "error": "skill not found"}
    meta, old_body = _parse_frontmatter(target.read_text(encoding="utf-8"))
    if description is not None:
        meta["description"] = description.strip()
    if category is not None and category.strip():
        meta["category"] = category.strip()
    target.write_text(_dump_skill(meta, body if body is not None else old_body),
                      encoding="utf-8")
    return {"ok": True, "id": name}


def delete_skill(name: str, home: Path | None = None) -> dict:
    target = _skills_dir(home) / name
    if not target.exists():
        return {"ok": False, "error": "skill not found"}
    shutil.rmtree(target, ignore_errors=True)
    return {"ok": True, "id": name}


# ============================================================================
# 6) MCP servers
# ============================================================================
def list_mcp_servers(home: Path | None = None) -> dict:
    """返回 config.yaml 中 mcp_servers 的完整视图（只读）。

    原样透传每条服务器的定义（stdio 传输的 command/args/env，或 HTTP/SSE
    传输的 url/headers/auth 等），仅补一个 ``enabled`` 默认值，供设置中心
    展示与 tools.mcp_tool.register_mcp_servers 直接消费。
    """
    servers = read_config_yaml(home).get("mcp_servers") or {}
    out: dict = {}
    for name, definition in servers.items():
        d = dict(definition) if isinstance(definition, dict) else {}
        d.setdefault("enabled", True)
        out[str(name)] = d
    return out


def upsert_mcp_server(name: str, definition: dict, home: Path | None = None) -> dict:
    """新增/更新一个 MCP 服务器定义并写回 config.yaml（通用持久化）。

    原样保留整条定义（stdio 传输的 command/args/env，或 HTTP/SSE 传输的
    url/headers/auth/connect_timeout 等），不再强制要求 command——
    远程 HTTP/SSE 服务器只有 url。至少需提供 command 或 url 之一；env 与
    headers 保持为字典。
    """
    h = home or get_hermes_home()
    name = (name or "").strip()
    if not name:
        raise ValueError("MCP 服务器名称不能为空")
    d = dict(definition or {})
    entry: dict = {}
    for k, v in d.items():
        if k == "env" and isinstance(v, dict):
            env = {str(kk): str(vv) for kk, vv in v.items() if str(kk).strip()}
            if env:
                entry["env"] = env
        elif k == "args" and isinstance(v, (list, tuple)):
            entry["args"] = [str(a) for a in v]
        elif k == "enabled":
            if v is False:
                entry["enabled"] = False
        elif k == "headers" and isinstance(v, dict):
            headers = {str(kk): str(vv) for kk, vv in v.items() if str(kk).strip()}
            if headers:
                entry["headers"] = headers
        else:
            entry[k] = v
    if not entry.get("command") and not entry.get("url"):
        raise ValueError("MCP 服务器必须提供 command 或 url 之一")
    servers = dict(read_config_yaml(h).get("mcp_servers") or {})
    servers[name] = entry
    update_config_yaml(h, {"mcp_servers": servers})
    return dict(entry)


def remove_mcp_server(name: str, home: Path | None = None) -> bool:
    """删除 MCP 服务器（深合并无法表达删除，故整体重写 mcp_servers）。"""
    h = home or get_hermes_home()
    cfg = read_config_yaml(h)
    servers = dict(cfg.get("mcp_servers") or {})
    if name not in servers:
        return False
    servers.pop(name)
    cfg["mcp_servers"] = servers
    _write_config_yaml_full(h, cfg)
    return True


def set_mcp_enabled(name: str, enabled: bool, home: Path | None = None) -> bool:
    h = home or get_hermes_home()
    cfg = read_config_yaml(h)
    servers = dict(cfg.get("mcp_servers") or {})
    if name not in servers:
        return False
    entry = dict(servers[name]) if isinstance(servers[name], dict) else {}
    if enabled:
        entry.pop("enabled", None)
    else:
        entry["enabled"] = False
    servers[name] = entry
    cfg["mcp_servers"] = servers
    _write_config_yaml_full(h, cfg)
    return True


def trigger_mcp_discovery() -> None:
    """后台连接本示例已启用的 MCP 服务器（stdio / SSE / HTTP）。

    复用 Hermes 真实库的 ``tools.mcp_tool.register_mcp_servers``，与进程内
    AIAgent 共用同一全局工具注册表；这样默认启用全部工具集的 Agent 就能看到
    MCP 工具。失败静默处理，不阻断主流程（例如未安装 mcp SDK 时直接跳过）。
    """
    try:
        import threading
        from tools.mcp_tool import register_mcp_servers
    except Exception:
        return

    def _run() -> None:
        try:
            servers = list_mcp_servers() or {}
            enabled = {
                n: dict(d)
                for n, d in servers.items()
                if isinstance(d, dict) and d.get("enabled", True)
            }
            if enabled:
                register_mcp_servers(enabled)
        except Exception:
            pass

    threading.Thread(target=_run, name="example-mcp-discovery", daemon=True).start()


# ============================================================================
# ============================================================================
# 7) Cron 定时任务 —— 桥接 Hermes 原生 cron 模块（cron.jobs / cron.scheduler）
# ============================================================================
# 存储与调度完全复用 Hermes 核心：schedule 支持自然语言（"2h" / "every 1d at 09:00"
# / cron 表达式）；调度由后台线程每 60s 调用 cron.scheduler.tick() 驱动
# （见 cron_scheduler.start_scheduler），到期任务由 Hermes 原生执行器运行。
# jobs 持久化在 HERMES_HOME/cron/jobs.json（与 Hermes 生态完全一致）。

def _map_job_view(job: dict) -> dict:
    """原生 job → 前端友好视图（兼容既有面板字段）。"""
    if not job:
        return {}
    enabled = bool(job.get("enabled", True))
    state = job.get("state") or ("active" if enabled else "paused")
    paused = (not enabled) or state == "paused"
    return {
        "id": job.get("id"),
        "name": job.get("name"),
        "prompt": job.get("prompt"),
        "schedule": job.get("schedule_display")
                   or (job.get("schedule") or {}).get("display") or "",
        "status": "paused" if paused else "active",
        "enabled": enabled,
        "next_run_at": job.get("next_run_at"),
        "last_run_at": job.get("last_run_at"),
        "last_status": job.get("last_status"),
        "last_error": job.get("last_error"),
        "deliver": job.get("deliver"),
        "kind": (job.get("schedule") or {}).get("kind"),
    }

def list_jobs(home: Path | None = None) -> list[dict]:
    from cron import jobs as _cj
    try:
        # include_disabled=True：让已暂停(paused/disabled)任务也在面板可见，便于重新启用
        return [_map_job_view(j) for j in _cj.list_jobs(include_disabled=True)]
    except Exception:
        return []

def add_job(prompt: str, schedule: str, home: Path | None = None,
            name: str | None = None, job_type: str | None = None) -> dict:
    from cron import jobs as _cj
    prompt = (prompt or "").strip()
    schedule = (schedule or "").strip()
    if not prompt or not schedule:
        return {"ok": False, "error": "prompt 与 schedule 均不能为空"}
    try:
        job = _cj.create_job(prompt, schedule, name=(name or None))
        return {"ok": True, "job": _map_job_view(job)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}

def update_job(job_id: str, home: Path | None = None, name: str | None = None,
               prompt: str | None = None, schedule: str | None = None,
               job_type: str | None = None) -> dict:
    from cron import jobs as _cj
    up: dict = {}
    if name and name.strip():
        up["name"] = name.strip()
    if prompt and prompt.strip():
        up["prompt"] = prompt.strip()
    if schedule and schedule.strip():
        up["schedule"] = schedule.strip()
    if not up:
        return {"ok": False, "error": "无有效更新字段"}
    try:
        job = _cj.update_job(job_id, up)
        return {"ok": True, "job": _map_job_view(job)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}

def delete_job(job_id: str, home: Path | None = None) -> dict:
    from cron import jobs as _cj
    try:
        return {"ok": bool(_cj.remove_job(job_id))}
    except Exception:
        return {"ok": False}

def set_job_status(job_id: str, status: str, home: Path | None = None) -> dict:
    from cron import jobs as _cj
    if status in ("active", "resume", "enable", "enabled"):
        try:
            _cj.resume_job(job_id)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}
    try:
        _cj.pause_job(job_id)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

def materialize_hermes_env(home: Path | None = None) -> Path:
    """把 Library 模式运行所需的环境「落地」（幂等，可重复调用）：

    1) 设置 HERMES_HOME 环境变量（AIAgent 据此定位 skills / config.yaml / memories）；
    2) 接通原生 bundled 插件目录（冻结态 _MEIPASS/plugins，开发态 site-packages/plugins）；
    3) 播种默认技能；
    4) 默认联网搜索：ensure_default_web_search_backend 写入零配置免费的 ddgs 后端（无需任何 Key/URL，首次自动安装 SDK）；已显式配置的用户设置不覆盖；
    5) 记录已配置模型路由（中性记录）。
    """
    home = home or get_hermes_home()
    with _lock:
        os.environ["HERMES_HOME"] = str(home)
        _export_bundled_plugins_env()
        ensure_default_skills(home)
        ensure_default_web_search_backend(home)
        try:
            write_model_routes(home)
        except Exception:
            pass
    return home


def _export_bundled_plugins_env() -> str | None:
    """把原生 bundled 插件目录导出到 HERMES_BUNDLED_PLUGINS。

    hermes_cli.plugins.get_bundled_plugins_dir() 优先读该环境变量；设了它，
    Hermes 自带的插件才能在冻结态（_MEIPASS/plugins）被内核发现。
    """
    try:
        if getattr(sys, "frozen", False):
            cand = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "plugins"
        else:
            import plugins as _p  # hermes-agent 顶层 plugins 包
            cand = Path(_p.__file__).resolve().parent
        if cand.exists():
            os.environ["HERMES_BUNDLED_PLUGINS"] = str(cand)
            return str(cand)
    except Exception:
        pass
    return None

# ============================================================================
# 需求3：补功能屏数据层（Soul / 记忆 / 系统提示词 / LLM Wiki / 远程渠道 / Kanban）
# 均为 HERMES_HOME 下的文件或配置 CRUD，遵循薄路由原则供 main.py 调用。
# ============================================================================
import time as _time  # noqa: E402

# ── Soul 人格 ─────────────────────────────────────────────────────────────
def get_soul(home: Path | None = None) -> dict:
    h = home or get_hermes_home()
    p = h / "SOUL.md"
    content = p.read_text(encoding="utf-8") if p.exists() else ""
    cfg = read_config_yaml(h)
    enabled = bool((cfg.get("agent") or {}).get("soul_enabled", False))
    return {"ok": True, "enabled": enabled, "content": content, "path": str(p)}

def save_soul(content: str, enabled: bool, home: Path | None = None) -> dict:
    h = home or get_hermes_home()
    (h / "SOUL.md").write_text(content or "", encoding="utf-8")
    # 统一走 update_config_yaml 深合并写入（与 toolset/agent_runtime 同一路径），
    # 避免各 save_* 重复 read→改 agent 子 dict→全量写回 的模板，降低误改共享配置风险。
    update_config_yaml(h, {"agent": {"soul_enabled": bool(enabled)}})
    return {"ok": True, "enabled": bool(enabled)}

# ── 记忆管理（MEMORY.md / USER.md，§ 分节） ─────────────────────────────
MEMORY_FILES = ["MEMORY.md", "USER.md"]

def list_memory(home: Path | None = None) -> dict:
    h = home or get_hermes_home()
    d = h / "memories"
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for name in MEMORY_FILES:
        p = d / name
        text = p.read_text(encoding="utf-8") if p.exists() else ""
        entries = [e.strip() for e in text.split("\n§\n") if e.strip()]
        out.append({"name": name, "text": text, "entries": entries,
                    "count": len(entries)})
    return {"ok": True, "files": out}

def save_memory(name: str, text: str, home: Path | None = None) -> dict:
    if name not in MEMORY_FILES:
        return {"ok": False, "error": "非法记忆文件名"}
    h = home or get_hermes_home()
    d = h / "memories"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text or "", encoding="utf-8")
    return {"ok": True, "name": name}

# ── 系统提示词 ───────────────────────────────────────────────────────────
def get_system_prompt(home: Path | None = None) -> dict:
    try:
        from agent_runtime import SYSTEM_PROMPT as default
    except Exception:
        default = ""
    cfg = read_config_yaml(home)
    custom = (cfg.get("agent") or {}).get("system_prompt") or ""
    return {"ok": True, "default": default, "custom": custom}

def save_system_prompt(custom: str, home: Path | None = None) -> dict:
    h = home or get_hermes_home()
    update_config_yaml(h, {"agent": {"system_prompt": (custom or "").strip()}})
    return {"ok": True}

# ── LLM Wiki（HERMES_HOME/wiki/，参照 Karpathy 范式、与 Hermes 内置 research/llm-wiki 同范式；本实现为自研，不加载官方 bundled skill） ──
# 重逻辑在 wiki_engine.py（目录/反链/ingest/query/lint/graph）；此处为兼容薄封装。
def _wiki_slug(name: str) -> str:
    s = (name or "").replace("..", "").strip("/")
    if s.lower().endswith(".md"):
        s = s[:-3]
    return s


def list_wiki(home: Path | None = None) -> dict:
    from wiki_engine import list_pages
    return {"ok": True, "items": list_pages(home)}


def get_wiki(name: str, home: Path | None = None) -> dict | None:
    from wiki_engine import get_page
    return get_page(home, _wiki_slug(name))


def save_wiki(name: str, title: str, category: str, tags: list, text: str,
              home: Path | None = None, type_: str = "summary",
              sources: list | None = None, confidence: str = "") -> dict:
    from wiki_engine import save_page
    slug = _wiki_slug(name) if name else None
    return save_page(home, slug=slug, title=title, type_=type_,
                     tags=tags, sources=sources, confidence=confidence,
                     category=category, text=text)


def delete_wiki(name: str, home: Path | None = None) -> dict:
    from wiki_engine import delete_page
    return delete_page(home, _wiki_slug(name))

# ── 远程渠道（Gateway Messaging：微信/QQ/飞书/钉钉/企微/Telegram/Discord/Slack） ──
CHANNELS = [
    {"id": "telegram", "label": "Telegram", "icon": "✈", "desc": "Telegram Bot（Hermes 官方网关支持）"},
    {"id": "discord", "label": "Discord", "icon": "🎮", "desc": "Discord Bot"},
    {"id": "slack", "label": "Slack", "icon": "💬", "desc": "Slack App"},
    {"id": "wechat", "label": "微信", "icon": "💚", "desc": "个人微信（需接入桥接服务）"},
    {"id": "qywx", "label": "企业微信", "icon": "🏢", "desc": "企业微信应用机器人"},
    {"id": "feishu", "label": "飞书", "icon": "🪶", "desc": "飞书机器人"},
    {"id": "dingtalk", "label": "钉钉", "icon": "🔔", "desc": "钉钉机器人"},
    {"id": "qq", "label": "QQ", "icon": "🐧", "desc": "QQ 机器人"},
]

def get_channels(home: Path | None = None) -> dict:
    cfg = read_config_yaml(home)
    cc = (cfg.get("agent") or {}).get("channels") or {}
    out = []
    for c in CHANNELS:
        conf = cc.get(c["id"]) or {}
        out.append({
            **c,
            "enabled": bool(conf.get("enabled")),
            "configured": bool(conf.get("token") or conf.get("webhook")
                               or conf.get("app_id") or conf.get("secret")),
            "config": conf,
        })
    return {"ok": True, "channels": out}

def save_channel(cid: str, config: dict, home: Path | None = None) -> dict:
    h = home or get_hermes_home()
    # 深合并进 agent.channels（保留其它渠道），与上面 save_* 同一写入路径。
    update_config_yaml(h, {"agent": {"channels": {cid: config or {}}}})
    return {"ok": True, "id": cid}

# ── Kanban 看板（复用内核 hermes_cli.kanban_db；路径与 schema 与内核完全一致） ──
# 看板数据结构由 Hermes 内核掌握。早期版本曾手写 sqlite、把真实表的 body 列错写成
# description、把 INTEGER 的 created_at 当字符串——一旦命中内核真实创建的 kanban.db
# 就报 "no such column: description"，看板空白、新增失败，且上游 schema 变更会静默损坏。
# 因此这里只复用内核的 kanban_db_path()/connect() 取路径与连接，SQL 严格按真实
# schema（tasks 表列：id/title/body/status/priority/created_at …）书写。路径解析尊重
# HERMES_KANBAN_DB / HERMES_KANBAN_BOARD / HERMES_KANBAN_HOME 与 get_default_hermes_root
# （即桌面冻结的 HERMES_HOME），与同进程内 Agent 写入同一看板。
# home 参数保留以兼容旧调用签名，但实际路径由内核 kanban_db_path() 决定。
def get_kanban(home: Path | None = None) -> dict:
    import sqlite3
    cols = ["todo", "in_progress", "done"]
    try:
        from hermes_cli import kanban_db as kb
    except Exception:
        return {"ok": True, "exists": False, "items": [], "columns": cols,
                "error": "内核 kanban_db 不可用"}
    path = kb.kanban_db_path()
    if not path.exists():
        return {"ok": True, "exists": False, "db": str(path),
                "columns": cols, "items": []}
    items = []
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, title, body, status, priority, created_at "
            "FROM tasks ORDER BY priority DESC, created_at DESC").fetchall()
        for r in rows:
            ca = r["created_at"]
            items.append({
                "id": r["id"], "title": r["title"] or "",
                "status": (r["status"] or "todo"),
                "priority": r["priority"] or 0,
                "description": r["body"] or "",
                "created_at": (_time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(ca))
                              if isinstance(ca, (int, float)) else (ca or "")),
            })
        conn.close()
    except Exception as e:
        return {"ok": True, "exists": True, "db": str(path),
                "columns": cols, "items": [], "error": str(e)}
    return {"ok": True, "exists": True, "db": str(path), "columns": cols,
            "items": items}


def add_kanban_task(title: str, description: str = "", home: Path | None = None) -> dict:
    title = (title or "").strip()
    if not title:
        return {"ok": False, "error": "任务标题不能为空"}
    import uuid
    try:
        from hermes_cli import kanban_db as kb
    except Exception as e:
        return {"ok": False, "error": f"内核 kanban_db 不可用：{e}"}
    conn = None
    try:
        conn = kb.connect()   # 初始化真实 schema（含 WAL）；库不存在则创建
        conn.execute(
            "INSERT INTO tasks (id, title, body, status, priority, created_at) "
            "VALUES (?,?,?,?,0,?)",
            (str(uuid.uuid4()), title, description or "", "todo", int(_time.time())))
        conn.commit()
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if conn is not None:
            try: conn.close()
            except Exception: pass
    return {"ok": True}
