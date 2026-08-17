# 业务系统（三系统示例骨架）

> 三系统架构下的「业务系统」——**纯业务，不依赖 Agent**。

## 职责
- 纯业务逻辑与界面，不含 Agent 逻辑。
- 通过三个纯业务接口与连接系统协作（不 import Agent）：
  - `build_app()` —— 自建纯业务 FastHTML app（独立模式）
  - `mount_rd_routes(app, rt)` —— 把业务路由挂到任意 app（融合模式由连接系统传入 Agent app）
  - `get_business_snapshot()` —— 业务数据快照（供 Agent 对话注入上下文）

## 铁律
- **绝不 import Agent 系统模块**（`server`/`routes`/`agent_runtime`/`tools`/`hermes_*`）。
- 依赖方向：业务系统 → 连接系统 → Agent系统。
- 可独立运行（`启动.bat`）与独立打包（EXE），不与 Agent 绑定。

## 使用
```bash
python app.py            # 独立运行（http://127.0.0.1:8810/dashboard）
# 或双击 启动.bat
```

## 融合模式
业务系统自身不负责融合；融合装配由**连接系统** `fuse_business_into_agent()` 完成
（把本系统的 `mount_rd_routes`/`get_business_snapshot` 挂到 Agent 底座）。

> 完整理念见 `references/18-tristructure-architecture.md`。
