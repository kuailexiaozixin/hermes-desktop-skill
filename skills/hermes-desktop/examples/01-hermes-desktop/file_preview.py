"""file_preview.py — 生成文件内联预览的「安全读取」层（A4，纯标准库，可离线测试）

只做两件事：

1. ``resolve_safe``：把请求路径解析为真实绝对路径，并强制限制在「允许根目录」之内
   （HERMES_HOME / 当前工作目录 / 系统临时目录 / 用户主目录）。跨软链与 ``..`` 均
   无效，杜绝任意文件读取（path traversal）。必须是已存在的普通文件。
2. ``preview_file``：按扩展名 + 文件头嗅探判定类型，返回可安全渲染的载荷
   （图片/PDF → base64 data URL；HTML/文本 → 文本）。前端一律用沙箱化
   ``<iframe sandbox>`` 或 ``<img>`` 渲染——即便内容含脚本也无法执行
   （A1 已对对话 Markdown 净化，此处再兜底一次）。

注意：本模块不依赖 hermes-agent / FastHTML，任何 Python（含受管 3.13）均可 import 与测试。
"""
from __future__ import annotations

import base64
import mimetypes
import os
import tempfile

# 允许预览的根目录（真实绝对路径）。读取必须落在其中之一内。
_ALLOWED_ROOTS: list[str] = []
_MAX_BYTES = 16 * 1024 * 1024  # 16MB 上限，避免把大文件整块读进内存


def _init_roots() -> list[str]:
    global _ALLOWED_ROOTS
    if _ALLOWED_ROOTS:
        return _ALLOWED_ROOTS
    roots: list[str] = []
    home = os.environ.get("HERMES_HOME")
    if home:
        roots.append(os.path.realpath(home))
    roots.append(os.path.realpath(os.getcwd()))
    roots.append(os.path.realpath(tempfile.gettempdir()))
    try:
        roots.append(os.path.realpath(os.path.expanduser("~")))
    except Exception:
        pass
    seen: set[str] = set()
    out: list[str] = []
    for r in roots:
        if r and r not in seen and os.path.isdir(r):
            seen.add(r)
            out.append(r)
    _ALLOWED_ROOTS = out
    return _ALLOWED_ROOTS


def reset_roots_for_test() -> None:
    """测试用：清空根缓存，便于切换 HERMES_HOME / cwd 后重算。"""
    global _ALLOWED_ROOTS
    _ALLOWED_ROOTS = []


def resolve_safe(path: str) -> str | None:
    """把路径解析为允许根目录内的真实绝对路径；非法（越界/不存在/非文件）返回 None。"""
    if not path or "\x00" in path:
        return None
    roots = _init_roots()
    try:
        real = os.path.realpath(path)
    except Exception:
        return None
    if not os.path.isfile(real):
        return None
    for r in roots:
        # 防 /root 误命中 /rootkit：要求等于 root 或以 sep 开头
        if real == r or real.startswith(r + os.sep):
            return real
    return None


def _image_mime(head: bytes) -> str | None:
    """用文件头嗅探图片类型（imghdr 在 3.13 已移除，这里手写，且排除可含脚本的 SVG）。"""
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def preview_file(path: str, max_bytes: int = _MAX_BYTES) -> dict:
    """安全读取文件并为前端返回预览载荷。失败返回 {"ok": False, ...}。"""
    real = resolve_safe(path)
    if not real:
        return {"ok": False, "error": "路径不在允许范围内或文件不存在"}
    try:
        size = os.path.getsize(real)
    except Exception:
        return {"ok": False, "error": "无法读取文件大小"}
    if size > max_bytes:
        return {"ok": False, "error": f"文件过大（{size} > {max_bytes} 字节），不予预览"}
    mime, _ = mimetypes.guess_type(real)
    mime = mime or "application/octet-stream"
    name = os.path.basename(real)

    # 图片：嗅探真实类型，读字节 → base64 data URL（不含 SVG，避免脚本）
    img_mime = None
    try:
        with open(real, "rb") as f:
            head = f.read(16)
        img_mime = _image_mime(head)
    except Exception:
        pass
    if img_mime:
        try:
            with open(real, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            return {"ok": True, "type": "image", "mime": img_mime, "name": name,
                    "data_url": f"data:{img_mime};base64,{b64}"}
        except Exception as e:
            return {"ok": False, "error": f"读取图片失败：{e}"}

    # PDF：base64 data URL（浏览器原生可渲染）
    if mime == "application/pdf":
        try:
            with open(real, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            return {"ok": True, "type": "pdf", "mime": mime, "name": name,
                    "data_url": f"data:{mime};base64,{b64}"}
        except Exception as e:
            return {"ok": False, "error": f"读取 PDF 失败：{e}"}

    # HTML / 文本：读文本（沙箱 iframe 渲染，脚本因 sandbox 不执行）
    if mime in ("text/html", "application/xhtml+xml") or mime.startswith("text/"):
        try:
            with open(real, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            return {"ok": True,
                    "type": "html" if mime.startswith("text/html") else "text",
                    "mime": mime, "name": name, "text": text}
        except Exception as e:
            return {"ok": False, "error": f"读取文本失败：{e}"}

    return {"ok": False, "error": f"不支持预览的类型：{mime}"}
