"""channels/registry.py — 默认渠道注册表。"""
from __future__ import annotations

from .base import ChannelConnector
from .telegram import TelegramConnector
from .feishu import FeishuConnector
from .dingtalk import DingTalkConnector
from .slack import SlackConnector
from .wecom import WeComConnector
from .discord import DiscordConnector
from .qq_official import QQOfficialConnector
from .weixin_hermes import WeixinHermesConnector

_CONNECTOR_CLASSES = (
    TelegramConnector, FeishuConnector, DingTalkConnector, SlackConnector,
    WeComConnector, DiscordConnector,
    QQOfficialConnector, WeixinHermesConnector,
)

CONNECTORS: dict[str, ChannelConnector] = {}
for _cls in _CONNECTOR_CLASSES:
    _inst = _cls()
    CONNECTORS[_inst.meta.cid] = _inst


def build_default_registry() -> dict[str, ChannelConnector]:
    """返回一份全新的连接器实例字典（避免共享可变状态）。"""
    return {cid: type(c)() for cid, c in CONNECTORS.items()}
