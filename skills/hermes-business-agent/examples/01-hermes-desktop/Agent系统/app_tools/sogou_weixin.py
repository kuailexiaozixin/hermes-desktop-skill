# -*- coding: utf-8 -*-
"""
搜狗微信搜索 —— 微信公众号文章检索工具（业务扩展点）。

通过搜狗微信搜索（weixin.sogou.com/weixin?type=2）按关键词检索微信公众号文章，
返回标题、公众号名、摘要、发布时间与搜狗跳转链接。

能力边界（重要，写给 Agent 也写给使用者）：
  * 检索是免费的，无需 API Key、无需代理，直连即可使用。
  * 「检索命中」（标题/公众号/摘要/时间）可直接获得；
    真实 mp.weixin.qq.com 全文链接需登录态 —— 搜狗对无 cookie 的链接还原
    会返回 antispider 验证码页。需要正文时，可用 browser 工具打开返回的
    搜狗链接（带登录态）二次跳转获取。
  * 高频请求会触发搜狗反爬/验证码，工具内部做了检测并返回友好错误。
"""
from __future__ import annotations

import html as _html
import re
import time as _time

_SOGOU_WEIXIN_URL = "https://weixin.sogou.com/weixin"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _UA,
    "Referer": "https://weixin.sogou.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def _clean(s: str) -> str:
    """去掉 HTML 标签与高亮注释，还原 HTML 实体。"""
    if not s:
        return ""
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)  # 去掉 <!--red_beg--> 等注释
    s = re.sub(r"<[^>]+>", "", s)  # 去掉标签
    return _html.unescape(s).strip()


def _time_from_script(seg: str):
    """从 <script>document.write(timeConvert('TS'))</script> 提取发布时间。"""
    m = re.search(r"timeConvert\('(\d+)'\)", seg)
    if not m:
        return None
    try:
        ts = int(m.group(1))
        return _time.strftime("%Y-%m-%d %H:%M", _time.localtime(ts))
    except Exception:
        return None


def _parse_results(html_text: str) -> list[dict]:
    """解析搜狗微信搜索结果页，返回文章列表。"""
    items = []
    for seg in re.split(r'class="txt-box"', html_text)[1:]:
        # 标题 + 搜狗跳转链接
        tm = re.search(
            r"<h3>\s*<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", seg, re.S
        )
        if not tm:
            continue
        title = _clean(tm.group(2))
        href = tm.group(1).replace("&amp;", "&")
        # 摘要
        sm = re.search(r'<p class="txt-info"[^>]*>(.*?)</p>', seg, re.S)
        summary = _clean(sm.group(1)) if sm else ""
        # 公众号名
        account = ""
        am = re.search(r'class="all-time[^"]*"[^>]*>(.*?)<', seg, re.S)
        if am:
            account = _clean(am.group(1))
        pub_time = _time_from_script(seg)
        sogou_url = (
            "https://weixin.sogou.com" + href if href.startswith("/") else href
        )
        items.append(
            {
                "title": title,
                "account": account,
                "summary": summary,
                "time": pub_time,
                "sogou_url": sogou_url,
            }
        )
    return items


def _is_antispider(text: str) -> bool:
    low = text.lower()
    return (
        "antispider" in low
        or "请输入验证码" in text
        or "安全验证" in text
        or "访问过于频繁" in text
    )


def _search(query: str, num: int) -> dict:
    import requests
    from requests import RequestException

    params = {"type": "2", "query": query, "s_from": "input"}
    try:
        resp = requests.get(
            _SOGOU_WEIXIN_URL, params=params, headers=_HEADERS, timeout=15
        )
    except RequestException as exc:
        return {"ok": False, "error": f"请求搜狗失败: {exc}"}
    if resp.status_code != 200:
        return {"ok": False, "error": f"搜狗返回 HTTP {resp.status_code}"}
    text = resp.text
    if _is_antispider(text):
        return {
            "ok": False,
            "error": "触发搜狗反爬/验证码，请稍后重试，或改用 browser 工具带登录态检索",
        }
    items = _parse_results(text)
    limit = max(1, min(int(num), 10))
    return {"ok": True, "articles": items[:limit]}


_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_wechat_articles",
        "description": (
            "检索微信公众号文章（通过搜狗微信搜索，免费、无需 API Key、无需代理）。"
            "输入关键词，返回匹配的公众号文章列表，包含标题、公众号名、摘要、"
            "发布时间与搜狗跳转链接。需要正文全文时，可用浏览器工具打开返回的链接获取。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索关键词，如「人工智能」"},
                "num": {
                    "type": "integer",
                    "description": "返回条数（1-10），默认 5",
                },
            },
            "required": ["query"],
        },
    },
}


def _handle_search_wechat_articles(args: dict, **kwargs) -> str:
    from tools.registry import tool_error, tool_result

    query = (args.get("query") or "").strip()
    if not query:
        return tool_error("query 不能为空", success=False)
    try:
        num = int(args.get("num") or 5)
    except (TypeError, ValueError):
        num = 5
    r = _search(query, num)
    if not r.get("ok"):
        return tool_error(r.get("error", "检索失败"), success=False)
    articles = r["articles"]
    if not articles:
        return tool_result(
            success=True, count=0, message="未检索到相关公众号文章", articles=[]
        )
    return tool_result(
        success=True,
        count=len(articles),
        note="真实文章全文链接需浏览器登录态打开搜狗链接获取",
        articles=articles,
    )


def register_into(registry) -> list[str]:
    registry.register(
        name="search_wechat_articles",
        toolset="sogou_weixin",
        schema=_SEARCH_SCHEMA,
        handler=_handle_search_wechat_articles,
        is_async=False,
        description="检索微信公众号文章（搜狗微信搜索，免费无需 Key）",
        emoji="🔍",
        max_result_size_chars=20_000,
        override=True,
    )
    return ["search_wechat_articles"]
