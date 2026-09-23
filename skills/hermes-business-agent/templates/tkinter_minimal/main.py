"""
tkinter_minimal/main.py — Hermes 桌面集成「最小空壳」（Tkinter + worker 线程）

铁律：先跑通空壳再加业务。这个骨架只有「一句话进、一句话出、流式可见」。
确认能对话后，再升级成 examples/01-hermes-desktop/agent_runtime.py 的完整版
（加工具卡片、思考折叠区、审批等）。

运行：
    pip install -r requirements.txt
    set HERMES_API_KEY=sk-...            # Windows
    # macOS / Linux: export HERMES_API_KEY=sk-...
    python main.py
"""
from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

if getattr(sys, "frozen", False):
    os.environ.setdefault(
        "HERMES_HOME", os.path.join(os.path.dirname(sys.executable), "hermes_data")
    )

from run_agent import AIAgent


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hermes 最小骨架")
        self.q: "queue.Queue[dict]" = queue.Queue()
        self.busy = False

        self.log = scrolledtext.ScrolledText(self, wrap=tk.WORD, state=tk.DISABLED)
        self.log.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, padx=8, pady=8)
        self.entry = ttk.Entry(bar)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(bar, text="发送", command=self.send).pack(side=tk.LEFT, padx=4)
        self.entry.bind("<Return>", lambda e: self.send())

        self.after(50, self.drain)   # 主线程轮询队列

    def send(self):
        if self.busy:
            return
        msg = self.entry.get().strip()
        if not msg:
            return
        self.entry.delete(0, tk.END)
        self._append("你", msg)
        self.busy = True
        threading.Thread(target=self.worker, args=(msg,), daemon=True).start()

    def worker(self, prompt: str):
        def on_delta(text: str):
            self.q.put({"type": "delta", "text": text})

        try:
            agent = AIAgent(
                quiet_mode=True,
                disabled_toolsets=["terminal"],
                max_iterations=20,
            )
            agent.run_conversation(user_message=prompt, stream_callback=on_delta)
        except Exception as e:
            self.q.put({"type": "error", "message": str(e)})
        finally:
            self.q.put({"type": "end"})

    def drain(self):
        try:
            while True:
                self._render(self.q.get_nowait())
        except queue.Empty:
            pass
        self.after(50, self.drain)

    def _render(self, it: dict):
        if it["type"] == "delta":
            self._append("Hermes", it["text"], stream=True)
        elif it["type"] == "error":
            self._append("⚠️", it["message"])
        elif it["type"] == "end":
            self.busy = False

    def _append(self, who: str, text: str, stream: bool = False):
        self.log.configure(state=tk.NORMAL)
        if stream:
            try:
                last_char = self.log.get("end-2c", "end-1c")
            except tk.TclError:
                # 空 / 极短 Text 时 "end-2c" 跨过起始索引，部分 Tk 版本抛 TclError
                last_char = ""
            if last_char != "\n":
                self.log.insert(tk.END, text)
            else:
                self.log.insert(tk.END, f"\n{who}: {text}")
        else:
            self.log.insert(tk.END, f"\n{who}: {text}")
        self.log.configure(state=tk.DISABLED)
        self.log.see(tk.END)


if __name__ == "__main__":
    App().mainloop()
