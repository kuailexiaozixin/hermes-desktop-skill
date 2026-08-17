# 连接系统（三系统示例骨架）

> 三系统架构下的「连接系统」——**纯桥接，唯一装配耦合点**。

## 职责
- 把业务系统挂载到 Agent 底座（= 01 根代码），产出「Agent 对话 + 业务路由」融合 app。
- **唯一装配点**：所有「业务 ↔ Agent」的桥接收拢在 `fuse_business_into_agent()`：
  - 拿 Agent 底座 `server.app/rt` → `mount_rd_routes` 挂业务路由
  - 设 `BUSINESS_CONTEXT_HOOK` = 业务快照
  - 注册业务工具 / 安装业务技能（按需）
- **不承载可独立执行的业务功能**：连接系统不是独立应用，只做装配与启动。

## 使用（融合模式）
```bash
python main.py    # 启动融合模式（http://127.0.0.1:8800/dashboard，Agent 对话 /）
```

## 依赖方向
业务系统 → 连接系统 → Agent系统。业务系统不直连 Agent；底座可整体替换（见 `替换Agent系统.md`）。

> 完整理念见 `references/18-tristructure-architecture.md`。
