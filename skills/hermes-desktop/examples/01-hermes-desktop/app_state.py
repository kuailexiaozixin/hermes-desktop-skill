"""app_state.py — 进程级共享状态（全局单例集中管理）

按 example01 独立性/耦合度批判报告建议 1、6：把原 `routes/__init__.py` 中的**全局单例**
抽到独立模块，各业务/路由模块显式 `from app_state import bridge`，不再经由
`routes` 命名空间总线隐式拉取，消除「改了 routes 全局就隐式影响所有子模块」的隐患；
并用**集中快照**统一暴露全局对象的可查询状态，明确所有权与锁边界。

**全局对象所有权清单**（谁创建、谁销毁、谁加锁）：
- `bridge`（ChannelBridge）：本模块创建；进程退出由 atexit 统一 shutdown；
  内部并发访问由 `bridge._lock` / `bridge._events_lock` 保护（见 channels/bridge.py）。
- `cron_sched`（cron_scheduler 模块级）：调度线程由 `cron_scheduler.start_scheduler()`
  启动（幂等），daemon 线程 + `_stop_event` 终止；手动运行并发由 `cron_scheduler._run_lock`
  与 Hermes 原生 claim 防重保护。
- `we`（wiki_engine）/`sessions`（sessions 模块）：均为无状态单例模块，按需 `import`，
  不在本模块实例化。

**规则**：新增全局可变对象必须在本文件登记并说明所有权；跨线程读写必须走对应锁。
"""
from __future__ import annotations

import atexit
import threading

from channels import ChannelBridge  # 进程内 IM 桥（替换外部 gateway 进程）

# ---------------------------------------------------------------------------
# 全局单例：连接管理 + 入站→进程内 Agent→出站
# ---------------------------------------------------------------------------
# 所有权：本模块创建，进程退出时由 atexit 统一 shutdown。
bridge = ChannelBridge()
atexit.register(bridge.shutdown)

# 全局状态快照锁（用于保护「读取多个全局对象状态」的复合操作不被并发写入打断）。
_state_snapshot_lock = threading.Lock()


def bridge_snapshot() -> dict:
    """线程安全地取 bridge 当前状态快照（连接渠道 + 接收器状态）。

    等价 `bridge.status()`，但明确声明「跨线程只读快照」语义：
    读取方不得持有快照做写操作；写操作仍走 bridge 内部锁。
    """
    with _state_snapshot_lock:
        return bridge.status()


def cron_snapshot() -> dict:
    """取定时调度器状态快照（调度线程是否存活）。"""
    import cron_scheduler as _cs
    return {
        "ok": True,
        "scheduler_alive": _cs.scheduler_alive(),
        "tick_seconds": 60,
    }
