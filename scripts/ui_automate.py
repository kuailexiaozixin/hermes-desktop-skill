#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ui_automate.py — pywebview 原生 UI 自动化（点击/输入/导航 + 断言），零额外浏览器。

设计动机
--------
传统 UI 自动化（Playwright/Puppeteer 等）需要再拉起一个独立浏览器、开调试端口、
用 websockets 连上去。这带来三个老问题：慢、易失败、常被浏览器授权/首次运行弹窗卡住。

本脚本换个思路：你的应用本就跑在 pywebview 的原生窗口里（Windows=WebView2，与 Edge
同引擎）。直接驱动「这个窗口」即可——

  · window.evaluate_js(js)       在真实渲染的 DOM 上派发事件 / 读取状态（无需写 JS 文件）
  · window.evaluate_js + html2canvas 可选截图留证

零额外浏览器、零 websockets、零浏览器授权。

步骤格式（JSON 或内置 demo）
-----------------------------
每步是一个字典，含 action 与参数：

  action          参数                          说明
  ──────────────────────────────────────────────────────
  click           selector                      派发真实 click 事件
  type            selector, text                清空并输入文本（input/textarea）
  wait            seconds                       等待
  assert_visible  selector                      断言元素存在且可见（display!=none, visibility!=hidden）
  assert_text     selector, text                断言元素文本包含指定字符串（部分匹配）
  assert_attr     selector, attr, value         断言元素属性等于指定值
  assert_not      selector                      断言元素不存在或不可见
  assert_count_gt selector, min_count           断言选择器匹配数 > min_count
  snapshot        name                         记录当前 DOM 状态快照（供后续断言引用）
  navigate        url                           重新加载到指定 URL

用法
----
  # 内置 demo 模式（针对 Hermes Desktop 示例，无需 JSON 文件）
  python scripts/ui_automate.py --url http://127.0.0.1:5001 --demo

  # 从 JSON 步骤文件运行
  python scripts/ui_automate.py --url http://127.0.0.1:5001 --steps my_steps.json

  # 调试时显示窗口
  python scripts/ui_automate.py --url http://127.0.0.1:5001 --demo --show

退出码
  0 = 全部通过
  1 = 存在失败断言
  2 = 环境/参数错误（未装 pywebview、URL 不可达等）
"""

import argparse
import json
import os
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


# ── 步骤执行器 ──

def _eval(window, js: str):
    """evaluate_js 包装，统一处理异常与返回值。"""
    try:
        return window.evaluate_js(js)
    except Exception as e:
        print(f"  [JS_ERROR] {e}", file=sys.stderr)
        return None


def _click(window, selector: str) -> bool:
    """派发真实 click 事件。"""
    js = ("(function(){var el=document.querySelector('" + selector +
           "');if(!el)return 'NOT_FOUND';el.click();return 'OK';})()")
    res = _eval(window, js)
    if res == "OK":
        return True
    print(f"  [FAIL] click({selector!r}) → {res!r}")
    return False


def _type_text(window, selector: str, text: str) -> bool:
    """清空 input/textarea 并输入文本，派发 input 事件。"""
    safe = text.replace("\\", "\\\\").replace("'", "\\'")
    js = ("(function(){var el=document.querySelector('" + selector +
           "');if(!el)return 'NOT_FOUND';el.value='" + safe + "';" +
           "el.dispatchEvent(new Event('input',{bubbles:true}));return 'OK';})()")
    res = _eval(window, js)
    if res == "OK":
        return True
    print(f"  [FAIL] type({selector!r}, {text!r}) → {res!r}")
    return False


def _assert_visible(window, selector: str) -> bool:
    """断言元素存在且可见。"""
    js = ("(function(){var el=document.querySelector('" + selector +
           "');if(!el)return {ok:false,reason:'not found'};" +
           "var s=getComputedStyle(el);" +
           "if(s.display==='none'||s.visibility==='hidden')" +
           "return {ok:false,reason:'hidden'};return {ok:true};})()")
    res = _eval(window, js)
    if isinstance(res, str):
        try:
            res = json.loads(res)
        except Exception:
            pass
    if isinstance(res, dict) and res.get("ok"):
        return True
    reason = res.get("reason", repr(res)) if isinstance(res, dict) else repr(res)
    print(f"  [FAIL] assert_visible({selector!r}) → {reason}")
    return False


def _assert_text(window, selector: str, expected: str) -> bool:
    """断言元素文本包含指定字符串（部分匹配）。input/textarea 读 value。"""
    js = ("(function(){var el=document.querySelector('" + selector +
           "');if(!el)return {ok:false,reason:'not found'};" +
           "var t=(el.value!==undefined&&el.value!==null)?el.value:(el.textContent||'').trim();" +
           "return {ok:t.indexOf('" + expected + "')>=0,text:String(t).slice(0,120)};})()")
    res = _eval(window, js)
    if isinstance(res, str):
        try:
            res = json.loads(res)
        except Exception:
            pass
    if isinstance(res, dict) and res.get("ok"):
        return True
    actual = res.get("text", "") if isinstance(res, dict) else ""
    print(f"  [FAIL] assert_text({selector!r}, {expected!r}) → 实际: {actual!r}")
    return False


def _assert_attr(window, selector: str, attr: str, value: str) -> bool:
    """断言元素属性等于指定值。"""
    safe_val = value.replace("\\", "\\\\").replace("'", "\\'")
    js = ("(function(){var el=document.querySelector('" + selector +
           "');if(!el)return {ok:false,reason:'not found'};" +
           "var v=el.getAttribute('" + attr + "')||'';" +
           "return {ok:v==='" + safe_val + "',actual:v};})()")
    res = _eval(window, js)
    if isinstance(res, str):
        try:
            res = json.loads(res)
        except Exception:
            pass
    if isinstance(res, dict) and res.get("ok"):
        return True
    actual = res.get("actual", "") if isinstance(res, dict) else ""
    print(f"  [FAIL] assert_attr({selector!r}, {attr}={value!r}) → 实际: {actual!r}")
    return False


def _assert_not(window, selector: str) -> bool:
    """断言元素不存在或不可见。"""
    js = ("(function(){var el=document.querySelector('" + selector +
           "');if(!el)return {ok:true};" +
           "var s=getComputedStyle(el);" +
           "if(s.display==='none'||s.visibility==='hidden')return {ok:true};" +
           "return {ok:false,reason:'visible'};})()")
    res = _eval(window, js)
    if isinstance(res, str):
        try:
            res = json.loads(res)
        except Exception:
            pass
    if isinstance(res, dict) and res.get("ok"):
        return True
    reason = res.get("reason", repr(res)) if isinstance(res, dict) else repr(res)
    print(f"  [FAIL] assert_not({selector!r}) → {reason}")
    return False


def _assert_count_gt(window, selector: str, min_count: int) -> bool:
    """断言选择器匹配数 > min_count。"""
    js = ("(function(){var els=document.querySelectorAll('" + selector +
           "');return {count:els.length, ok:els.length>" + str(min_count) + "};})()")
    res = _eval(window, js)
    if isinstance(res, str):
        try:
            res = json.loads(res)
        except Exception:
            pass
    if isinstance(res, dict) and res.get("ok"):
        return True
    count = res.get("count", "?") if isinstance(res, dict) else "?"
    print(f"  [FAIL] assert_count_gt({selector!r}, >{min_count}) → 实际: {count}")
    return False


# ── 步骤调度器 ──

_STEP_HANDLERS = {
    "click": lambda w, s: _click(w, s["selector"]),
    "type": lambda w, s: _type_text(w, s["selector"], s.get("text", "")),
    "wait": lambda w, s: (time.sleep(float(s.get("seconds", 1))), True)[-1],
    "assert_visible": lambda w, s: _assert_visible(w, s["selector"]),
    "assert_text": lambda w, s: _assert_text(w, s["selector"], s.get("text", "")),
    "assert_attr": lambda w, s: _assert_attr(w, s["selector"], s.get("attr", ""), s.get("value", "")),
    "assert_not": lambda w, s: _assert_not(w, s["selector"]),
    "assert_count_gt": lambda w, s: _assert_count_gt(w, s["selector"], int(s.get("min_count", 0))),
}


def run_steps(window, steps: list[dict], snapshots: dict) -> tuple[int, list[str]]:
    """逐步执行，返回 (passed_count, failed_messages)。"""
    passed = 0
    failures = []
    for i, step in enumerate(steps):
        action = step.get("action", "")
        desc = step.get("desc", "")
        label = f"[{i+1}/{len(steps)}] {action}"
        if desc:
            label += f" ({desc})"
        print(f"  执行 {label} ...", end=" ", flush=True)

        # snapshot / navigate 特殊处理（优先于通用 handler 查找）
        if action == "snapshot":
            name = step.get("name", f"snap_{i}")
            snap_js = ("JSON.stringify({rootTheme:document.documentElement.getAttribute('data-theme')," +
                       "sideCls:(document.getElementById('sidebar')||{}).className," +
                       "promptVal:(document.getElementById('prompt')||{}).value," +
                       "convCount:(document.getElementById('convList')||{children:[]}).children.length," +
                       "bodyLen:document.body?document.body.innerText.length:0})")
            snap_data = _eval(window, snap_js)
            snapshots[name] = snap_data
            print(f"SNAP({name})")
            passed += 1
            continue

        if action == "navigate":
            url = step.get("url", "")
            window.load_url(url)
            time.sleep(1.5)
            print(f"NAVIGATE({url})")
            passed += 1
            continue

        handler = _STEP_HANDLERS.get(action)
        if not handler:
            print(f"SKIP（未知动作: {action}）")
            failures.append(f"步骤{i+1}: 未知动作 '{action}'")
            continue
            window.load_url(url)
            time.sleep(1.5)
            print(f"NAVIGATE({url})")
            passed += 1
            continue

        ok = handler(window, step)
        if ok:
            print("PASS")
            passed += 1
        else:
            print("FAIL")
            failures.append(f"步骤{i+1}: {label}")

        # 步骤间短暂等待（让 htmx/动画有时间响应）
        if action in ("click", "type", "navigate"):
            time.sleep(0.4)

    return passed, failures


# ── 内置 demo 流程（Hermes Desktop 验证） ──

DEMO_STEPS = [
    {"action": "assert_visible", "selector": "#sidebar",
     "desc": "侧边栏存在且可见"},
    {"action": "snapshot", "name": "init"},
    {"action": "click", "selector": "#btnTheme",
     "desc": "切换主题为深色"},
    {"action": "wait", "seconds": 0.6},
    {"action": "assert_attr", "selector": "html", "attr": "data-theme", "value": "dark",
     "desc": "data-theme 变为 dark"},
    {"action": "click", "selector": "#btnTheme",
     "desc": "切回浅色主题"},
    {"action": "wait", "seconds": 0.6},
    {"action": "assert_attr", "selector": "html", "attr": "data-theme", "value": "light",
     "desc": "data-theme 回到 light"},
    {"action": "click", "selector": "#btnToggleSide",
     "desc": "折叠侧边栏"},
    {"action": "wait", "seconds": 0.4},
    {"action": "assert_attr", "selector": "#sidebar", "attr": "class", "value": "sidebar collapsed",
     "desc": "侧边栏获得 collapsed 类"},
    {"action": "click", "selector": "#btnToggleSide",
     "desc": "展开侧边栏"},
    {"action": "wait", "seconds": 0.4},
    {"action": "assert_not", "selector": "#sidebar.collapsed",
     "desc": "collapsed 类已移除"},
    {"action": "type", "selector": "#prompt", "text": "自动化测试输入",
     "desc": "在对话输入框输入文字"},
    {"action": "assert_text", "selector": "#prompt", "text": "自动化测试输入",
     "desc": "确认输入框值正确"},
    {"action": "snapshot", "name": "before_new_conv"},
    {"action": "click", "selector": "#btnNew",
     "desc": "创建新对话"},
    {"action": "wait", "seconds": 0.6},
    {"action": "assert_count_gt", "selector": "#convList > *", "min_count": 5,
     "desc": "对话列表有内容（>5项）"},
]


# ── 主流程 ──

def health_check(url: str, timeout: float = 3.0, retries: int = 12) -> bool:
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.status == 200
        except Exception:
            if i < retries - 1:
                time.sleep(1.0)
    return False


def run_automation(window, steps: list[dict]):
    """在 pywebview 工作线程中执行自动化步骤，结果写入 _AUTO_STATE。"""
    import threading as _threading
    loaded_ev = _threading.Event()
    window.events.loaded += lambda: loaded_ev.set()
    try:
        if not loaded_ev.wait(timeout=25):
            _AUTO_STATE["failures"] = ["窗口加载超时（25s 内未收到 loaded 事件）"]
            _AUTO_STATE["exit"] = 2
            window.destroy()
            return

        time.sleep(2.0)  # 等 SPA 初始化完成
        snapshots = {}
        passed, failures = run_steps(window, steps, snapshots)
        if snapshots:
            print("\n  快照记录:")
            for k, v in snapshots.items():
                print(f"    {k}: {v}")
        _AUTO_STATE["passed"] = passed
        _AUTO_STATE["failures"] = failures
        _AUTO_STATE["exit"] = 1 if failures else 0
        try:
            window.destroy()
        except Exception:
            pass
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        _AUTO_STATE["failures"] = [f"自动化执行异常: {e}\n{tb}"]
        _AUTO_STATE["exit"] = 2
        try:
            window.destroy()
        except Exception:
            pass


# 跨线程共享的结果容器
_AUTO_STATE = {"passed": 0, "failures": [], "exit": 0}


def main() -> int:
    ap = argparse.ArgumentParser(description="pywebview 原生 UI 自动化")
    ap.add_argument("--url", required=True, help="运行中应用 URL")
    ap.add_argument("--steps", default=None, help="JSON 步骤文件路径（不指定则需 --demo）")
    ap.add_argument("--demo", action="store_true", help="运行内置 demo 流程（Hermes Desktop 验证）")
    ap.add_argument("--show", action="store_true", help="显示窗口（默认隐藏）")
    ap.add_argument("--width", type=int, default=1280, help="自动化窗口宽度（默认 1280，模拟标准桌面视口）")
    ap.add_argument("--height", type=int, default=800, help="自动化窗口高度（默认 800）")
    args = ap.parse_args()

    # 确定步骤来源
    if args.steps:
        sp = Path(args.steps)
        if not sp.exists():
            print(f"[ERROR] 步骤文件不存在: {sp}", file=sys.stderr)
            return 2
        try:
            steps = json.loads(sp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ERROR] 步骤文件解析失败: {e}", file=sys.stderr)
            return 2
    elif args.demo:
        steps = DEMO_STEPS
    else:
        print("[ERROR] 请指定 --steps <file.json> 或 --demo", file=sys.stderr)
        return 2

    try:
        import webview
    except Exception as e:
        print(f"[ERROR] 未安装 pywebview: {e}", file=sys.stderr)
        return 2

    if not health_check(args.url, timeout=3.0, retries=12):
        print(f"[ERROR] 应用 URL 不可达: {args.url}", file=sys.stderr)
        return 2

    try:
        window = webview.create_window("UI 自动化（原生窗口）", url=args.url,
                                      hidden=not args.show,
                                      width=args.width, height=args.height)
        webview.start(run_automation, (window, steps))
    except Exception as e:
        msg = str(e)
        if "display" in msg.lower() or "gui" in msg.lower():
            print(f"[ERROR] 无法创建原生窗口（无 GUI 会话？）：{msg}", file=sys.stderr)
        else:
            print(f"[ERROR] 自动化初始化失败: {msg}", file=sys.stderr)
        return 2

    # webview.start 返回后，从 _AUTO_STATE 取结果并打印报告
    passed = _AUTO_STATE.get("passed", 0)
    failures = _AUTO_STATE.get("failures", [])
    exit_code = _AUTO_STATE.get("exit", 2)
    total = len(DEMO_STEPS if args.demo else steps)

    print("\n" + "=" * 56)
    print("  UI 自动化报告（pywebview 原生）")
    print("=" * 56)
    print(f"  通过: {passed}/{total}   失败: {len(failures)}")
    if failures:
        for f in failures:
            print(f"  ❌ {f}")
    else:
        print("  ✅ 全部通过")
    print("=" * 56)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
