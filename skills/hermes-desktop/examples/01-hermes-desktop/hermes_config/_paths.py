from __future__ import annotations

import copy
import json
import os
import re
import shutil
import sys
import threading
from pathlib import Path




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
