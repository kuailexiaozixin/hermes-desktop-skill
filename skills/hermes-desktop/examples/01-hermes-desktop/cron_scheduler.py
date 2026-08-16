"""cron_scheduler.py — 定时任务后台调度（复用 Hermes 原生 cron 调度器）。

在进程内 Library / FastHTML 架构下，用 Hermes 核心自带的 cron 调度能力补齐
「定时任务中心」的执行层：不再自研 croniter 与任务存储，而是——

  * **存储/解析**：hermes_config.list_jobs / add_job / ... 已桥接到 cron.jobs
    （读写 HERMES_HOME/cron/jobs.json，schedule 支持自然语言与 cron 表达式）；
  * **调度**：本模块启动一个 daemon 后台线程，每 60s 调用 cron.scheduler.tick()，
    与 Hermes 官方网关驱动定时任务的方式完全一致（gateway 也是每 60s tick 一次）；
  * **手动运行**：run_job_now 用后台线程调 cron.scheduler.run_one_job(job)，其内部
    经 claim_dispatch 做并发防重。

依赖：cron（Hermes 官方库，随 hermes-agent 一起安装）。
"""
from __future__ import annotations

import threading

from cron import scheduler as _sched

# 调度节拍（秒）：与 Hermes 网关一致，每 60s 扫描一次到期任务。
_TICK = 60

_scheduler_thread: threading.Thread | None = None
_stop_event: threading.Event | None = None
_run_lock = threading.Lock()


def run_job_now(job_id: str) -> dict:
    """手动「立即运行」：后台线程执行一次任务（run_one_job 内部 claim 防并发）。"""
    from cron import jobs as _cj
    job = _cj.get_job(job_id)
    if not job:
        return {"ok": False, "error": "任务不存在"}

    def worker() -> None:
        try:
            _sched.run_one_job(job)
        except Exception as _e:  # noqa: BLE001
            try:
                _cj.mark_job_run(job_id, False, error=str(_e)[:200])
            except Exception:
                pass

    threading.Thread(target=worker, daemon=True).start()
    return {"ok": True, "message": "已在后台触发执行"}


def _tick_loop(stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            _sched.tick()
        except Exception:  # noqa: BLE001
            # 调度绝不能因单轮异常退出
            pass
        stop.wait(_TICK)


def start_scheduler() -> bool:
    """启动后台调度线程（幂等）。返回是否本次新启动。"""
    global _scheduler_thread, _stop_event
    if _scheduler_thread and _scheduler_thread.is_alive():
        return False
    _stop_event = threading.Event()
    _scheduler_thread = threading.Thread(target=_tick_loop,
                                         args=(_stop_event,), daemon=True)
    _scheduler_thread.start()
    return True


def scheduler_alive() -> bool:
    return bool(_scheduler_thread and _scheduler_thread.is_alive())
