"""
fasthtml_minimal/main.py — Hermes 桌面集成「最小空壳」（FastHTML + SSE）

铁律：先跑通空壳再加业务。这个骨架只有「一句话进、一句话出、流式可见」。
确认它能对话后，再往 agent_runtime 里加工具/回调/业务（见 references/04-rendering-frameworks.md、references/05-tooling.md#tools、references/05-tooling.md#office）。

运行：
    pip install -r requirements.txt
    set HERMES_API_KEY=sk-...            # Windows
    # macOS / Linux: export HERMES_API_KEY=sk-...
    python main.py        # http://localhost:5001
"""
from __future__ import annotations

import json
import os
import queue
import sys
import threading

if getattr(sys, "frozen", False):
    os.environ.setdefault(
        "HERMES_HOME", os.path.join(os.path.dirname(sys.executable), "hermes_data")
    )

from fasthtml.common import *
from run_agent import AIAgent


app, rt = fast_app(title="Hermes 最小骨架")


def stream_worker(prompt: str, out: "queue.Queue[dict]"):
    # 文本增量 = run_conversation 的方法参数；工具/推理回调按需再加（见 references/02-callbacks-and-streaming.md）
    def on_delta(text: str):
        out.put({"type": "delta", "text": text})

    agent = AIAgent(
        quiet_mode=True,
        disabled_toolsets=["terminal"],   # 进程内必禁
        max_iterations=20,
    )
    try:
        agent.run_conversation(user_message=prompt, stream_callback=on_delta)
        out.put({"type": "done"})
    except Exception as e:
        out.put({"type": "error", "message": str(e)})
    finally:
        out.put({"type": "end"})


@rt("/")
def index():
    return Titled(
        "Hermes 最小骨架",
        Div(id="chat", style="white-space:pre-wrap;padding:16px"),
        Form(id="f")(Input(id="p", placeholder="问点什么…"), Button("发送")),
        Script(JS),
    )


@rt("/chat/stream")
async def chat(prompt: str):
    out: "queue.Queue[dict]" = queue.Queue()
    threading.Thread(target=stream_worker, args=(prompt, out), daemon=True).start()

    async def gen():
        while True:
            it = out.get()
            yield ServerSentEvent(json.dumps(it, ensure_ascii=False))
            if it["type"] == "end":
                break

    return EventStream(gen)


JS = """
const chat = document.getElementById('chat');
let b = null;
document.getElementById('f').addEventListener('submit', (e)=>{
  e.preventDefault();
  const q = document.getElementById('p').value;
  document.getElementById('p').value = '';
  if(!q) return;
  if(!b){ b = document.createElement('div'); chat.appendChild(b); }
  const es = new EventSource('/chat/stream?prompt=' + encodeURIComponent(q));
  es.onmessage = (ev)=>{
    const it = JSON.parse(ev.data);
    if(it.type === 'delta') b.textContent += it.text;
    else if(it.type === 'error') b.textContent += '\\n⚠️ ' + it.message;
    else if(it.type === 'done' || it.type === 'end') es.close();
  };
  es.onerror = ()=> es.close();
});
"""
# ── 启动：浏览器模式（默认）或 pywebview 桌面模式（--desktop）──
HOST = "127.0.0.1"
PORT = 5001
APP_NAME = "Hermes 最小骨架"
WIN_W, WIN_H = 1100, 800


def _wait_port(host: str, port: int, timeout: float = 20) -> bool:
    import socket
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _serve() -> None:
    # 后台线程跑 FastHTML 服务（供 pywebview 窗口加载）
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def _open_browser() -> int:
    # 默认：前台 uvicorn，浏览器访问 http://localhost:5001
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
    return 0


def _open_desktop() -> int:
    # pywebview 桌面模式：后台 uvicorn + 原生窗口，失败回退默认浏览器
    import threading
    import time
    import webbrowser

    server = threading.Thread(target=_serve, daemon=True)
    server.start()
    if not _wait_port(HOST, PORT):
        print("❌ 本地服务启动失败（端口 %d 未就绪）" % PORT, file=sys.stderr)
        return 1
    try:
        import webview
        webview.create_window(APP_NAME, f"http://{HOST}:{PORT}", width=WIN_W, height=WIN_H)
        webview.start()
    except Exception as e:  # WebView2 缺失等
        print(f"⚠️ pywebview 启动失败（{e}），回退到默认浏览器。", file=sys.stderr)
        webbrowser.open(f"http://{HOST}:{PORT}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    return 0


def main() -> int:
    if "--desktop" in sys.argv[1:]:
        return _open_desktop()
    return _open_browser()


if __name__ == "__main__":
    sys.exit(main())
