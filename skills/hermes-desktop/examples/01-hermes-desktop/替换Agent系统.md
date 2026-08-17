# 替换 Agent 系统（底座三步替换法）

> Agent 系统是纯净 Hermes 底座（= 上游 `examples/01` 零差异），可**整体替换**而不影响业务系统与连接系统。
> 前提：业务/连接只通过稳定接口依赖 Agent（`server.app/rt`、`agent_runtime`、`tools.registry`、`routes.chat`），
> **不 import 其内部实现**；Agent 底座保持零差异、无业务痕迹。

## 三步替换法

```
① 删除旧的 Agent 系统代码（先备份运行时数据 HERMES_HOME）
② 复制上游最新 examples/01 作为新的 Agent 系统代码
③ 把原运行时数据（HERMES_HOME 等）粘贴回，业务/连接零改动
```

## 替换后验证（门禁）

- [ ] `verify_agent_same`：Agent 系统与上游 `examples/01` 代码零差异
- [ ] `verify_biz_no_agent_import`：业务系统无 `import server/routes/agent_runtime/tools/hermes_*`
- [ ] 融合装配：`fuse_business_into_agent()` 后业务路由 + Agent 对话 `/api/chat` 双 200
- [ ] 独立运行：业务系统独立启动，业务路由 200

> 详见 `references/18-tristructure-architecture.md` §6。
