#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ui_window_verify.py — 基于 pywebview 原生窗口的自动化 UI 质检

设计动机
--------
传统机器视觉质检方案需要再拉起一个独立的 headless 浏览器、开 remote-debugging 端口、
用 websockets 连上去，才能看页面。这带来三个老问题：慢、易失败、常被浏览器授权/首次运行
弹窗卡住。

本脚本换个思路：你的应用本就跑在 pywebview 的原生窗口里（Windows=WebView2，与 Edge
同引擎）。直接驱动「这个窗口」即可——

  · window.evaluate_js(js)       在真实渲染的 DOM 上跑检查，拿返回值（无需写 JS 文件、
                                 无需 CDN、无需第二个浏览器）
  · window.dom                   Python 侧直接查/改元素（可选，本脚本主要用 evaluate_js）
  · window.native.webview        Windows 下拿 WebView2 的 CoreWebView2，做真实像素截图
  · window.evaluate_js + html2canvas  无头环境下用纯 JS 把 DOM 渲染到 canvas 导出 PNG
                                     （无需显示器、无需额外浏览器）

零额外浏览器、零 websockets、零浏览器授权。检查项：
  图标名当文本(BAN) / 元素几何重叠(UX) / WCAG 对比度(UX) / 横向溢出(UX) / 空白页(UX)。

截图说明（关键，关乎"无需额外库 / 无需第二个浏览器"）：
  · 核心的结构/视觉缺陷检查（图标/重叠/对比度/溢出/空白）全部靠 evaluate_js 读 DOM 的
    计算样式与几何盒，不需要任何像素库——这是本方案更稳健的主因。
  · 像素截图是「可选增强」，且有两级原生实现、零额外浏览器：
      - 第一级（Windows 有显示器/桌面会话）：经 window.native.webview → WebView2
        CoreWebView2.CapturePreviewAsync，用 pythonnet（pywebview WinForms 后端已自带，
        无需额外安装）截真实 PNG，可做像素级空白判读 + 视觉回归。
      - 第二级（无显示器 / 原生截图为 0 字节时自动回退）：用 evaluate_js 注入随技能离线
        分发的 html2canvas.min.js，在 pywebview 原生 JS 引擎内把 DOM 画到 canvas 导出 PNG。
        无需显示器、无需第二个浏览器、无需 CDN。
  · 两级都不可用（如 Linux 无 $DISPLAY，pywebview 窗口本身无法创建）：改用 DOM 法判空白，
    视觉回归降级关闭，并提示改用 `ui_audit.py`（纯 HTTP + bs4 结构审计，零 GUI 依赖）。
  · Pillow 仅用于像素空白判读与视觉回归；缺失时这两项自动降级，不影响 DOM 检查。

用法
----
  # 应用已在运行（推荐，与 release_gate --url 一致）
  python scripts/ui_window_verify.py --url http://127.0.0.1:5001

  # 指定截图输出 / 关闭截图
  python scripts/ui_window_verify.py --url http://127.0.0.1:5001 --out shot.png
  python scripts/ui_window_verify.py --url http://127.0.0.1:5001 --no-shot

  # 调试时显示窗口（默认隐藏，避免闪烁）
  python scripts/ui_window_verify.py --url http://127.0.0.1:5001 --show

  # 无显示器/无桌面会话时，原生截图会截出 0 字节，脚本自动回退 html2canvas 无头截图
  # （库随技能在 scripts/html2canvas.min.js，离线可用），无需任何额外操作：
  python scripts/ui_window_verify.py --url http://127.0.0.1:5001 --out shot.png --shot-scale 1.5

退出码
  0 = 通过（或仅 UX 级提示）
  1 = 存在阻断级（BAN）缺陷（如图标名当文本）
  2 = 环境/参数错误（未装 pywebview、URL 不可达、无 GUI 会话等）
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


# ── 严重级别 ──
SEV_BAN = "BAN"   # 阻断：图标名当文本
SEV_UX = "UX"     # 体验：重叠 / 低对比度 / 空白 / 横向溢出

ICON_NAME_RE = re.compile(r"^[a-z][a-z0-9_\-]{1,24}$", re.I)
FONT_ICON_RE = re.compile(r"(material-icons|fa-|fas |far |fab |glyphicon|icon-font)", re.I)
OVERLAP_RATIO = 0.4          # 交叠面积 / 较小者面积 超过此值视为异常重叠
BLANK_STD_THRESHOLD = 8.0    # 灰度标准差低于此值视为接近空白/纯色页
CONTRAST_AA = 4.5           # WCAG AA 正文对比度阈值

VISUAL_BASELINE_DIR = ".ui-window-baselines"
VR_AHASH_HAMMING = 8
VR_PIXEL_MAD = 18.0

ICON_SELECTOR = ".nav-icon,.icon,span[class*=icon],i[class*=icon],a[class*=icon]"
GEO_SELECTOR = "nav a,.nav-item,.nav-icon,button,.btn,.menu-item,a[class*=nav],.sidebar a,.toolbar button"
TEXT_SELECTOR = "h1,h2,h3,h4,h5,h6,p,span,a,button,label,td,th,li"

DOM_PROBE = r"""
(() => {
  function effBg(el){
    let e = el;
    for (let i=0;i<24 && e;i++){
      const s = getComputedStyle(e);
      const bg = s.backgroundColor;
      if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') return bg;
      e = e.parentElement;
    }
    return 'rgb(255,255,255)';
  }
  function parseRGB(str){
    const m = str.match(/(\d+)[,\s]+(\d+)[,\s]+(\d+)/);
    return m ? [+m[1], +m[2], +m[3]] : null;
  }
  function lum(rgb){
    const a = rgb.map(v => { v/=255; return v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055,2.4); });
    return 0.2126*a[0] + 0.7152*a[1] + 0.0722*a[2];
  }
  function ratio(fg,bg){
    const L1 = lum(fg), L2 = lum(bg);
    const hi = Math.max(L1,L2), lo = Math.min(L1,L2);
    return (hi+0.05)/(lo+0.05);
  }
  // 判定元素是否被某个 overflow!=visible 的祖先裁剪在可视区域之外。
  // 可滚动容器（如侧栏导航 max-height+overflow:auto）内的子项在视觉上不可见，
  // 其 getBoundingClientRect 仍返回自然坐标，直接比较会产生"假重叠/假对比度"误报。
  function isClipped(el){
    const r = el.getBoundingClientRect();
    let p = el.parentElement;
    while (p){
      const cs = getComputedStyle(p);
      const ov = cs.overflow + ' ' + cs.overflowY + ' ' + cs.overflowX;
      if (/auto|hidden|scroll/.test(ov)){
        const pr = p.getBoundingClientRect();
        if (r.bottom <= pr.top || r.top >= pr.bottom || r.right <= pr.left || r.left >= pr.right){
          return true;
        }
      }
      p = p.parentElement;
    }
    return false;
  }
  const iconSel = '__ICON_SEL__';
  const iconEls = [...document.querySelectorAll(iconSel)];
  const icons = iconEls.slice(0,300).map(el => {
    const s = getComputedStyle(el);
    return {
      cls: (el.className && el.className.toString ? el.className.toString() : '').slice(0,60),
      hasSvg: !!el.querySelector('svg'),
      hasImg: !!el.querySelector('img'),
      text: (el.textContent || '').trim().slice(0,40),
      display: s.display,
      visibility: s.visibility
    };
  });
  const geoSel = '__GEO_SEL__';
  const geoEls = [...document.querySelectorAll(geoSel)];
  const boxes = geoEls.slice(0,400).map(el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return { tag: el.tagName, cls: (el.className && el.className.toString ? el.className.toString() : '').slice(0,40), x: r.x, y: r.y, w: r.width, h: r.height, display: s.display, visibility: s.visibility, clipped: isClipped(el) };
  });
  const txtSel = '__TXT_SEL__';
  const txtEls = [...document.querySelectorAll(txtSel)].filter(el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return el.childElementCount === 0 && (el.textContent||'').trim().length > 0
      && r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'
      && !isClipped(el);
  });
  const contrast = txtEls.slice(0,300).map(el => {
    const s = getComputedStyle(el);
    const fg = parseRGB(s.color); const bg = parseRGB(effBg(el));
    let ra = null;
    try { if (fg && bg) ra = +ratio(fg,bg).toFixed(2); } catch(e) {}
    return { cls: (el.className && el.className.toString ? el.className.toString() : '').slice(0,40), tag: el.tagName, ratio: ra, fg: s.color.slice(0,30), bg: bg ? bg.slice(0,30) : '' };
  }).filter(c => c.ratio !== null);
  return JSON.stringify({
    title: document.title,
    bodyLen: document.body ? document.body.innerText.length : 0,
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    icons, boxes, contrast
  });
})()
"""
DOM_PROBE = DOM_PROBE.replace("__ICON_SEL__", ICON_SELECTOR).replace("__GEO_SEL__", GEO_SELECTOR).replace("__TXT_SEL__", TEXT_SELECTOR)

ERROR_PROBE = r"""
(() => {
    const uri = document.documentURI || '';
    const title = document.title || '';
    const body = document.body ? document.body.innerText : '';
    const isError = uri.startsWith('chrome-error') ||
        /无法访问|can.t be reached|refused to connect|ERR_|This page isn.t|Access denied|隐私错误|Privacy error/i.test(title + ' ' + body);
    return JSON.stringify({uri, title: title.slice(0,80), isError});
})()
"""

# 跨线程共享的结果容器
_STATE = {"issues": [], "exit": 0, "nr": 0, "shot_ok": False}


def health_check(url: str, timeout: float = 3.0, retries: int = 12) -> bool:
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.status == 200
        except Exception:
            if i < retries - 1:
                time.sleep(1.0)
    return False


def _contains(a, b) -> bool:
    return (a["x"] <= b["x"] and a["y"] <= b["y"]
            and a["x"] + a["w"] >= b["x"] + b["w"]
            and a["y"] + a["h"] >= b["y"] + b["h"])


def _visible(item: dict) -> bool:
    return item.get("display") != "none" and item.get("visibility") != "hidden"


def analyze_dom(data: dict, issues: list):
    for ic in data.get("icons", []):
        if not _visible(ic):
            continue
        if ic.get("hasSvg") or ic.get("hasImg"):
            continue
        if FONT_ICON_RE.search(ic.get("cls", "")):
            continue
        text = ic.get("text", "")
        if text and (" " not in text) and ICON_NAME_RE.match(text) and text.isascii():
            issues.append((SEV_BAN, f"图标容器 class='{ic['cls']}' 仅含裸图标名 '{text}'（应渲染为 SVG/<img>/字体图标 class）"))

    boxes = [b for b in data.get("boxes", []) if _visible(b) and not b.get("clipped") and b["w"] > 0 and b["h"] > 0]
    n = len(boxes)
    for i in range(n):
        for j in range(i + 1, n):
            a, c = boxes[i], boxes[j]
            if _contains(a, c) or _contains(c, a):
                continue
            ix = max(0, min(a["x"] + a["w"], c["x"] + c["w"]) - max(a["x"], c["x"]))
            iy = max(0, min(a["y"] + a["h"], c["y"] + c["h"]) - max(a["y"], c["y"]))
            inter = ix * iy
            if inter <= 0:
                continue
            small = min(a["w"] * a["h"], c["w"] * c["h"])
            if small > 0 and inter / small > OVERLAP_RATIO:
                issues.append((SEV_UX, f"元素重叠: <{a['tag']} class='{a['cls']}'> 与 <{c['tag']} class='{c['cls']}'> 重叠 {inter:.0f}px²"))

    low = [c for c in data.get("contrast", []) if c["ratio"] is not None and c["ratio"] < CONTRAST_AA]
    for c in low[:10]:
        issues.append((SEV_UX, f"低对比度({c['ratio']:.2f}<{CONTRAST_AA}): <{c['tag']} class='{c['cls']}'> fg={c['fg']} bg={c['bg']}"))

    ox = data.get("overflowX", 0)
    if ox > 2:
        issues.append((SEV_UX, f"横向溢出: 页面 scrollWidth 比视口宽 {ox:.0f}px（出现横向滚动条/内容被裁切）"))


def analyze_screenshot(png_bytes: bytes, out_path: Path, issues: list) -> bool:
    try:
        from io import BytesIO
        from PIL import Image
        import statistics
        img = Image.open(BytesIO(png_bytes)).convert("L")
        try:
            pixels = list(img.get_flattened_data())
        except AttributeError:
            pixels = list(img.getdata())
        if not pixels:
            return False
        mean = sum(pixels) / len(pixels)
        var = sum((p - mean) ** 2 for p in pixels) / len(pixels)
        std = var ** 0.5
        if std < BLANK_STD_THRESHOLD:
            issues.append((SEV_UX, f"截图接近纯色/疑似空白页（灰度标准差 {std:.1f} < {BLANK_STD_THRESHOLD}，均值 {mean:.0f}）"))
        out_path.write_bytes(png_bytes)
        return True
    except Exception as e:  # noqa: BLE001
        issues.append((SEV_UX, f"截图像素分析失败（Pillow 缺失时跳过）: {e}"))
        return False


def perceptual_hash(img) -> int:
    from PIL import Image
    small = img.convert("L").resize((8, 8), Image.BILINEAR)
    pixels = list(small.getdata())
    mean = sum(pixels) / len(pixels)
    h = 0
    for p in pixels:
        h = (h << 1) | (1 if p >= mean else 0)
    return h


def visual_regression(baseline_path: Path, current_png: bytes, issues: list) -> str:
    from io import BytesIO
    from PIL import Image
    try:
        cur = Image.open(BytesIO(current_png))
    except Exception as e:  # noqa: BLE001
        issues.append((SEV_UX, f"视觉回归：截图解码失败: {e}"))
        return "error"
    if baseline_path.exists():
        try:
            base = Image.open(baseline_path)
        except Exception:
            baseline_path.write_bytes(current_png)
            return "created"
        h_cur = perceptual_hash(cur)
        h_base = perceptual_hash(base)
        hamming = bin(h_cur ^ h_base).count("1")
        a = cur.convert("L").resize((64, 64), Image.BILINEAR)
        b = base.convert("L").resize((64, 64), Image.BILINEAR)
        pa = list(a.getdata())
        pb = list(b.getdata())
        mad = sum(abs(x - y) for x, y in zip(pa, pb)) / len(pa)
        if hamming > VR_AHASH_HAMMING or mad > VR_PIXEL_MAD:
            reasons = []
            if hamming > VR_AHASH_HAMMING:
                reasons.append(f"aHash 汉明距离={hamming} > {VR_AHASH_HAMMING}")
            if mad > VR_PIXEL_MAD:
                reasons.append(f"像素 MAD={mad:.1f} > {VR_PIXEL_MAD}")
            issues.append((SEV_UX,
                f"视觉回归：与基线差异过大（{'；'.join(reasons)}）。请人工确认是否预期变更；"
                f"若预期，删除 {baseline_path.name} 后重跑，或加 --update-baseline 覆盖"))
            return "diff"
        return "pass"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_bytes(current_png)
    return "created"


def screenshot_env_hint() -> str:
    """原生与无头截图都不可用（极少见）时，给出取图办法。"""
    if sys.platform.startswith("linux"):
        if not os.environ.get("DISPLAY"):
            return ("当前 Linux 无 $DISPLAY（无显示器），pywebview 窗口本身无法创建，两级截图都不可用。"
                    "要拿到真实截图，二选一："
                    "① 用虚拟显示器包裹运行：`xvfb-run -a python ui_window_verify.py --url <URL>`"
                    "（xvfb 内 WebView2/WebKit 有合成表面，原生截图与 html2canvas 均可用）；"
                    "② 在有图形桌面的机器上直接运行。DOM 检查不受影响。")
        return "当前 Linux 有 $DISPLAY，PyWebView(WebKit) 可正常渲染并原生截图。"
    # Windows：正常有显示器时第一级原生截图即可；仅当连 html2canvas 回退也失败时才提示
    return ("当前 Windows 两级截图（WebView2 原生 + html2canvas 无头）均不可用。"
            "请确认：① scripts/html2canvas.min.js 随技能存在；② 在【有显示器的电脑】上运行本脚本"
            "（双击 启动.bat 或命令行即可）可走第一级原生截图。DOM 检查不受影响。")


def capture_native(window, out_path: Path) -> bool:
    """经 WebView2 CoreWebView2 截取真实 PNG（仅 Windows + pythonnet 可用时）。

    实测结论（已用探针验证）：
      · CoreWebView2 只能在 UI 线程访问，必须从 pywebview 工作线程用 form.Invoke
        调度回 UI 线程；否则抛 COM/线程异常（InvalidCastException: ICoreWebView2Controller）。
      · CapturePreviewAsync 需要窗口有真实渲染表面：隐藏窗口会截出 0 字节，故截图前
        先 Show；无显示器/无桌面的 headless 环境下会截到 0 字节，此时返回 False，
        由调用方降级为 DOM 法判空白（不影响主体 DOM 检查）。
      · 图像格式必须用 WebView2 自带的 CoreWebView2CapturePreviewImageFormat.Png，
        而非 System.Drawing.Imaging.ImageFormat（类型不兼容）。
    零额外安装：pythonnet 是 pywebview WinForms 后端的自带依赖。
    """
    if sys.platform != "win32":
        return False
    try:
        import clr  # pythonnet 入口；pywebview WinForms 后端已加载，可直接 import
        from System import Func
        from Microsoft.Web.WebView2.Core import CoreWebView2CapturePreviewImageFormat
        from System.IO import MemoryStream

        form = window.native
        ctrl = getattr(form, "webview", None)
        if ctrl is None:
            return False

        # 1) UI 线程：显示窗口，提供可渲染表面
        form.Invoke(Func[bool](lambda: (form.Show(), form.BringToFront(), True)[-1]))
        time.sleep(1.0)  # 工作线程等待一帧合成（不阻塞 UI 消息泵）

        # 2) UI 线程：截图（CoreWebView2 仅 UI 线程可访问）
        def _shot() -> bool:
            core = ctrl.CoreWebView2
            if core is None:
                return False
            ms = MemoryStream()
            t = core.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png, ms)
            t.Wait(8000)
            data = ms.ToArray()
            if not data or len(data) == 0:
                return False
            out_path.write_bytes(bytes(data))
            return out_path.exists() and out_path.stat().st_size > 0

        ok = bool(form.Invoke(Func[bool](_shot)))

        # 3) 截完隐藏，避免残留可见窗口
        try:
            form.Invoke(Func[bool](lambda: (form.Hide(), True)[-1]))
        except Exception:
            pass
        return ok
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] 原生截图失败（降级为 DOM 法判空白）：{e}", file=sys.stderr)
        return False


def _html2canvas_lib() -> "str | None":
    """定位随技能离线分发的 html2canvas.min.js（与本脚本同目录）。"""
    p = Path(__file__).resolve().parent / "html2canvas.min.js"
    if p.exists():
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return None
    return None


def capture_html2canvas(window, out_path: Path, scale: float = 1.0) -> bool:
    """纯 JS 无头截图：在 pywebview 原生 JS 引擎内用 html2canvas 把 DOM 画到 canvas 导出 PNG。

    适用场景：Windows 无显示器/无桌面会话时，WebView2 CapturePreviewAsync 截出 0 字节，
    此时本函数作为自动回退，仍能产出真实 PNG。

    关键约束（实测）：
      · 库随技能离线分发（scripts/html2canvas.min.js），无需 CDN、无需联网。
      · pywebview 的 evaluate_js 不等待 JS Promise 返回，因此用全局变量 window.__h2c
        承接 toDataURL 结果，并轮询直到就绪/出错/超时。
      · 零显示器、零第二个浏览器、零浏览器授权。
    返回 True 且写出有效 PNG 时为成功。
    """
    import base64
    lib = _html2canvas_lib()
    if not lib:
        print("[WARN] 未找到 html2canvas.min.js（应随技能放在 scripts/ 下），跳过无头截图",
              file=sys.stderr)
        return False
    try:
        window.evaluate_js(lib)
        # 等待库就绪（typeof html2canvas === 'function'）
        ready = False
        for _ in range(50):
            if window.evaluate_js("typeof html2canvas === 'function'") is True:
                ready = True
                break
            time.sleep(0.1)
        if not ready:
            print("[WARN] html2canvas 注入后未就绪，跳过无头截图", file=sys.stderr)
            return False

        window.evaluate_js(
            "(function(){"
            " window.__h2c=null; window.__h2c_err=null;"
            " try{"
            "  html2canvas(document.body,{backgroundColor:null,scale:" + str(scale) +
            ",logging:false,useCORS:true,windowWidth:document.documentElement.clientWidth})"
            "   .then(function(c){window.__h2c=c.toDataURL('image/png');})"
            "   .catch(function(e){window.__h2c_err=String(e);});"
            " }catch(e){window.__h2c_err=String(e);}"
            "})()")

        # 轮询结果（最多 ~12s）
        for _ in range(120):
            res = window.evaluate_js(
                "window.__h2c ? 'OK' : (window.__h2c_err ? 'ERR:'+window.__h2c_err : 'WAIT')")
            if res == "OK":
                break
            if isinstance(res, str) and res.startswith("ERR:"):
                print("[WARN] html2canvas 渲染失败：" + res[4:], file=sys.stderr)
                return False
            time.sleep(0.1)
        else:
            print("[WARN] html2canvas 渲染超时，跳过无头截图", file=sys.stderr)
            return False

        data_url = window.evaluate_js("window.__h2c")
        if not isinstance(data_url, str) or not data_url.startswith("data:image/png;base64,"):
            return False
        out_path.write_bytes(base64.b64decode(data_url.split(",", 1)[1]))
        return out_path.exists() and out_path.stat().st_size > 0
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] 无头截图（html2canvas）失败：{e}", file=sys.stderr)
        return False


def wait_dom_stable(window, max_wait=10.0, settle=2):
    """对 htmx/异步 SPA：采样 scrollWidth 与 body 文本长度，稳定后再断言。"""
    last = None
    same = 0
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            data = window.evaluate_js(
                "JSON.stringify({w:document.documentElement.scrollWidth, t:(document.body?document.body.innerText.length:0)})")
        except Exception:
            return
        if isinstance(data, str):
            try:
                cur = json.loads(data)
            except Exception:
                cur = None
            if cur and last and abs(cur["w"] - last["w"]) < 5 and abs(cur["t"] - last["t"]) < 5:
                same += 1
                if same >= settle:
                    return
            else:
                same = 0
            last = cur
        time.sleep(0.5)


def run_checks(window, args):
    """在 pywebview 工作线程中执行：等加载 → 稳定 → 探针 → 截图 → 分析 → 关窗。"""
    loaded_ev = threading.Event()
    window.events.loaded += lambda: loaded_ev.set()
    try:
        if not loaded_ev.wait(timeout=25):
            _STATE["issues"].append((SEV_UX, "窗口加载超时（25s 内未收到 loaded 事件）"))
            _STATE["exit"] = 2
            window.destroy()
            return

        time.sleep(args.wait)
        wait_dom_stable(window, max_wait=10, settle=2)

        # 连接健康：排除 Edge/WebView2 错误页
        err = window.evaluate_js(ERROR_PROBE)
        if isinstance(err, str):
            try:
                ej = json.loads(err)
                if ej.get("isError"):
                    print(f"[ERROR] 页面未正常加载（错误页）：{ej.get('uri')} | {ej.get('title')}")
                    _STATE["exit"] = 2
                    window.destroy()
                    return
            except Exception:
                pass

        data = window.evaluate_js(DOM_PROBE)
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = {}
        analyze_dom(data if isinstance(data, dict) else {}, _STATE["issues"])

        # 截图（可选增强）
        if not args.no_shot:
            out_p = Path(args.out)
            ok = capture_native(window, out_p)
            if not ok:
                # 无显示器/无桌面会话时 WebView2 原生截图为 0 字节，自动回退纯 JS 无头截图
                ok = capture_html2canvas(window, out_p, scale=args.shot_scale)
            _STATE["shot_ok"] = ok
            if ok:
                png = Path(args.out).read_bytes()
                analyze_screenshot(png, Path(args.out), _STATE["issues"])
                if args.visual_regression:
                    if args.update_baseline:
                        try:
                            Path(args.baseline_dir).mkdir(parents=True, exist_ok=True)
                            (Path(args.baseline_dir)
                             / f"{hashlib.md5(args.url.encode('utf-8')).hexdigest()[:12]}.png"
                             ).write_bytes(png)
                            _STATE["issues"].append((SEV_UX, "视觉回归基线已用本次截图强制更新（--update-baseline）"))
                        except Exception as e:  # noqa: BLE001
                            _STATE["issues"].append((SEV_UX, f"视觉回归基线更新失败: {e}"))
                    else:
                        key = hashlib.md5(args.url.encode("utf-8")).hexdigest()[:12]
                        bl_path = Path(args.baseline_dir) / f"{key}.png"
                        vr = visual_regression(bl_path, png, _STATE["issues"])
                        if vr == "created":
                            _STATE["issues"].append((SEV_UX, f"视觉回归基线已创建: {bl_path}（下次运行将比对）"))
            else:
                # DOM 法空白判读（两种截图都不可用时的兜底）
                body_len = (data or {}).get("bodyLen", 0)
                n_boxes = len((data or {}).get("boxes", []))
                if body_len < 30 and n_boxes == 0:
                    _STATE["issues"].append((SEV_UX, "DOM 法疑似空白页（body 文本<30 且无可见交互元素）；未做像素确认"))
                # 明确告知：为何没图、如何不依赖额外浏览器拿到图
                print("[INFO] 未生成像素截图（原生与无头截图均不可用）：" + screenshot_env_hint(), file=sys.stderr)
        else:
            print("[INFO] 已关闭截图（--no-shot），仅做 DOM 结构/视觉缺陷检查", file=sys.stderr)

        window.destroy()
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] 原生窗口质检失败: {e}", file=sys.stderr)
        _STATE["exit"] = 2
        try:
            window.destroy()
        except Exception:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description="pywebview 原生窗口 UI 质检（DOM 断言 + 可选截图）")
    ap.add_argument("--url", required=True, help="运行中应用 URL，如 http://127.0.0.1:5001")
    ap.add_argument("--exe", default=None, help="可选：先启动此 EXE 再质检")
    ap.add_argument("--out", default="ui-window-screenshot.png", help="截图保存路径（--no-shot 时忽略）")
    ap.add_argument("--shot-scale", type=float, default=1.0,
                    help="无头截图（html2canvas）放大倍数，默认 1.0；提高可得更清晰图")
    ap.add_argument("--wait", type=float, default=2.0, help="页面加载后额外等待秒数")
    ap.add_argument("--no-shot", action="store_true", help="完全不做像素截图（仅 DOM 检查）")
    ap.add_argument("--show", action="store_true", help="显示窗口（默认隐藏，避免闪烁）")
    ap.add_argument("--width", type=int, default=1280, help="质检窗口宽度（默认 1280，模拟标准桌面视口）")
    ap.add_argument("--height", type=int, default=800, help="质检窗口高度（默认 800）")
    ap.add_argument("--visual-regression", dest="visual_regression", action="store_true", default=True,
                    help="启用像素级视觉回归（截图可用时生效：Windows 原生或 html2canvas 无头均可；均不可用时自动降级关闭）")
    ap.add_argument("--no-visual-regression", dest="visual_regression", action="store_false",
                    help="关闭视觉回归比对")
    ap.add_argument("--baseline-dir", default=VISUAL_BASELINE_DIR, help="视觉回归基线目录")
    ap.add_argument("--update-baseline", action="store_true", help="用本次截图强制覆盖视觉回归基线")
    args = ap.parse_args()

    try:
        import webview  # 核心技术栈依赖，未装则环境错误
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] 未安装 pywebview（本技术栈核心依赖）：{e}", file=sys.stderr)
        return 2

    proc = None
    try:
        if args.exe:
            proc = subprocess.Popen([args.exe])
        if not health_check(args.url, timeout=3.0, retries=12):
            print(f"[ERROR] 应用 URL 不可达: {args.url}（若使用 --exe，请确认 EXE 能稳定启动 HTTP 服务）")
            return 2

        window = webview.create_window(
            "UI 质检（原生窗口）",
            url=args.url,
            hidden=not args.show,
            width=args.width,
            height=args.height,
        )
        # 注意：pywebview 的 start(func, args, localization, ...) 中，args 必须是
        # 可迭代对象（元组）。把 (window, args) 作为整体传入，start 内部会按
        # threading.Thread(target=func, args=args) 展开为 run_checks(window, args)。
        webview.start(run_checks, (window, args))
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "display" in msg.lower() or "gui" in msg.lower() or "session" in msg.lower():
            print(f"[ERROR] 无法创建原生窗口（无 GUI 会话/显示器？）：{msg}\n[INFO] 无 GUI 环境请改用 ui_audit.py（纯 HTTP+bs4 结构审计）", file=sys.stderr)
        else:
            print(f"[ERROR] 质检初始化失败: {msg}", file=sys.stderr)
        return 2
    finally:
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                pass

    issues = _STATE["issues"]
    bans = [m for s, m in issues if s == SEV_BAN]
    uxs = [m for s, m in issues if s == SEV_UX]
    print("=" * 64)
    print("  UI 质检报告（pywebview 原生窗口，机器断言，无需人工）")
    print("=" * 64)
    print(f"  截图: {args.out if (not args.no_shot and _STATE['shot_ok']) else '(未生成：--no-shot 或 非 Windows/DOM法)'}")
    if not issues:
        print("  ✅ 全部通过：图标为真实图形 / 无重叠塌陷 / 对比度达标 / 无空白页 / 无横向溢出")
        print("=" * 64)
        return 0
    for m in bans:
        print(f"  ❌ [BAN] {m}")
    for m in uxs:
        print(f"  ⚠️  [UX ] {m}")
    print("=" * 64)
    print(f"  阻断(BAN) {len(bans)} 项 / 体验(UX) {len(uxs)} 项")
    print("=" * 64)
    return 1 if bans else 0


if __name__ == "__main__":
    raise SystemExit(main())
