"""channels — 进程内即时通讯（IM）渠道桥。

设计要点（与 hermes-desktop 技能铁律一致）：
- 智能体核心 = 进程内 Hermes Python Library（run_agent.AIAgent）。本桥「不起外部 gateway 进程、
  不把 agent 放到 HTTP 远端执行」——agent 始终在桌面进程内直跑。
- 让桌面进程内的 AIAgent 直接通过「标准库 HTTPS」与 IM 平台通信：
    * Telegram：纯轮询（getUpdates），无需入站服务器，最干净；
    * 飞书 / 企业微信 / 钉钉 / Slack / Discord：出站 Webhook 发送 + 本地推送接收器（仅 127.0.0.1）接收事件。
- 仅依赖 Python 标准库（urllib / hashlib / hmac / base64 / http.server），**不新增任何第三方依赖**，
  符合冻结 venv 约束。
- 与 hermes 官方 `hermes gateway` 子命令的区别：官方 gateway 是另一个长驻进程，与本桌面 agent 不相交；
  本桥把渠道能力收敛回进程内，消除「渠道配置页只是装饰、桌面 agent 收不到 IM 消息」的问题（即 F1 本质）。

注：IM 平台本身使用 HTTPS API，桌面与其通信必须走 HTTPS——这是「与平台对话」，不是「把 agent 架在
HTTP 网关后面执行」。桌面 UI 自身也是本地 FastHTML(HTTP) 服务，故「不走 HTTP」指不把 agent 远端化。
"""
from .base import (
    ChannelConnector,
    InboundMessage,
    OutboundResult,
    ChannelError,
    http_post_json,
    http_get_json,
    b64_hmac_sha256,
    hex_hmac_sha256,
    sha1_hex_sorted,
)
from .bridge import ChannelBridge
from .registry import build_default_registry, CONNECTORS

__all__ = [
    "ChannelConnector", "InboundMessage", "OutboundResult", "ChannelError",
    "http_post_json", "http_get_json", "b64_hmac_sha256", "hex_hmac_sha256",
    "sha1_hex_sorted", "ChannelBridge", "build_default_registry", "CONNECTORS",
]
