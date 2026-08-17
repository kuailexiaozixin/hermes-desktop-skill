"""连接系统 bridge.py — 纯桥接，唯一装配耦合点

三系统架构下，连接系统职责（高内聚低耦合）：
- **唯一装配点**：所有「业务 ↔ Agent」的桥接全部收拢在 fuse_business_into_agent()：
  - 拿 Agent 底座 app/rt → mount_rd_routes 挂业务路由
  - 设 BUSINESS_CONTEXT_HOOK = 业务快照（让 Agent 对话感知业务数据）
  - 注册业务工具到 tools.registry / 安装业务技能到 HERMES_HOME/skills
- **绝不承载可独立执行的业务功能**：连接系统不是独立应用，只做装配。
- 依赖方向：业务系统 → 连接系统 → Agent系统。
"""
import sys
from pathlib import Path


def _project_root() -> Path:
    """三系统根目录（= examples/01-hermes-desktop，Agent 底座所在）。"""
    return Path(__file__).resolve().parent.parent


def ensure_syspath() -> None:
    """把三系统目录加入 sys.path（Agent 底座=01 根 + 业务系统 + 连接系统）。"""
    base = _project_root()
    for _p in (base, base / "业务系统", base / "连接系统"):
        _s = str(_p)
        if _s not in sys.path:
            sys.path.insert(0, _s)


def fuse_business_into_agent():
    """融合装配：把业务系统挂载到 Agent 底座，返回「Agent 对话 + 业务路由」融合 app。

    流程：
      1. 从 Agent 底座导入 server.app/rt（01 根代码即 Agent系统）
      2. 调业务系统 mount_rd_routes(app, rt) 挂业务路由
      3. 把业务 get_business_snapshot 设为 Agent 底座 routes.chat 的 BUSINESS_CONTEXT_HOOK
      4. 注册业务工具 / 安装业务技能（按需）
      5. 包装 stream_agent_chat 使 Agent 对话感知业务数据
    返回融合 app。Agent 底座不可用则回退业务系统自建纯业务 app。
    """
    ensure_syspath()
    try:
        # ① Agent 底座（01 根代码）
        from server import app as _agent_app, rt as _agent_rt
        # ② 业务系统纯业务接口（不 import Agent）
        from 业务系统.app import mount_rd_routes, get_business_snapshot

        # ③ 挂业务路由到 Agent app
        mount_rd_routes(_agent_app, _agent_rt)

        # ④ 业务快照 HOOK（让 Agent 对话感知业务数据）
        try:
            from routes import chat as _chat
            _chat.BUSINESS_CONTEXT_HOOK = get_business_snapshot
        except Exception as _e:
            print(f"[连接系统] 业务快照 HOOK 设置失败（降级）：{_e}")

        # ⑤ 注册业务工具 / 安装业务技能（示例，按需实现）
        #    register_biz_tools();  install_biz_skills();

        print("[连接系统] 融合装配完成：业务路由已挂载到 Agent 底座")
        return _agent_app
    except Exception as _e:
        print(f"[连接系统] 融合装配失败，回退业务自建 app：{type(_e).__name__}: {_e}")
        try:
            from 业务系统.app import app as _biz_app
            return _biz_app
        except Exception:
            return None
