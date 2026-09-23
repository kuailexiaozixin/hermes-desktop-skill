"""业务系统 app.py — 纯业务，不依赖 Agent 系统

三系统架构下，业务系统职责（高内聚低耦合）：
- **纯业务逻辑与界面**：build_app() 自建 FastHTML app，只处理业务，不含 Agent。
- **可挂载能力**：mount_rd_routes(app, rt) 把业务路由挂到「任意 app」——
  独立模式挂到自建 app，融合模式由连接系统把它挂到 Agent 底座 app 上。
- **业务快照**：get_business_snapshot() 向 Agent 对话提供业务数据快照（供注入上下文）。

🔒 铁律：业务系统**绝不 import 任何 Agent 系统模块**
（server / routes / agent_runtime / tools / hermes_config / app_tools …）。
依赖方向：业务系统 → 连接系统 → Agent系统。装配全部由连接系统承担。
"""
from fasthtml.common import *


def build_app():
    """构建纯业务 FastHTML app（独立模式 / 业务独立 EXE 用）。"""
    _a, _rt = fast_app(pico=False, htmx=False, live=False, title="业务系统")
    return _a, _rt


def mount_rd_routes(_a, _rt):
    """把业务路由挂载到指定 app/rt（融合模式由连接系统传入 Agent 底座 app/rt）。"""
    @_rt("/dashboard")
    def dashboard():
        return Title("业务仪表盘"), H1("业务系统"), P("纯业务页面，不含 Agent 逻辑。")

    @_rt("/biz-list")
    def biz_list():
        return H2("业务数据列表"), Ul([Li(f"业务条目 {i}") for i in range(3)])

    # …… 其余业务路由（费用 / 项目 / 报表等）……

    # 静态资源（如需）：_a.mount 或 fasthtml 静态配置


def get_business_snapshot() -> str:
    """生成业务数据快照（融合模式下由连接系统注入 Agent 对话上下文）。"""
    return (
        "## 业务数据快照\n"
        "- 业务条目数：3\n"
        "- 示例业务指标：……"
    )


# 独立运行（biz_main / 独立 EXE）时自建纯业务 app；融合模式由连接系统 bridge 装配。
app, rt = build_app()
mount_rd_routes(app, rt)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8810)
