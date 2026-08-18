// @ts-check
/* =====================================================================
 * panels.js — 面板 barrel 入口（重导出 panels/ 子模块）
 * ===================================================================== */

// 共享工具
export { escapeHtml, panelTabs, statCard, escapeCsv } from "./panels/utils.js";

// 产物抽屉
export { openArtifacts, previewArtifact } from "./panels/artifacts.js";

// 用量分析
export { openAnalytics, closeAnalytics, renderAnalytics } from "./panels/analytics.js";

// 模型面板
export { renderModelsPanel } from "./panels/models.js";

// 工具集成面板
export { renderToolsPanel, openToolsetConfig, openToolsetTest, openToolsetTrial } from "./panels/tools.js";

// 工具调用信息面板（对话区右上角「工具调用信息」按钮）
export { openToolCalls, closeToolCalls, clearToolCalls } from "./panels/toolcalls.js";

// 技能面板（技能商店）
export { renderSkillsPanel } from "./panels/skills.js";

// MCP 面板（服务器信息 + 客户端商店）
export { renderMcpPanel } from "./panels/mcp.js";

// 循环面板
export { renderLoopsPanel } from "./panels/loops.js";

// 插件面板
export { renderPluginsPanel } from "./panels/plugins.js";

// 日志面板（只读查看 Hermes 日志，对齐 `hermes logs`）
export { renderLogsPanel } from "./panels/logs.js";

// 结构化输出面板（触发 host-owned 结构化补全 + 离线 JSON Schema 校验，对齐 Hermes Library）
export { renderStructuredPanel } from "./panels/structured.js";

// 工具清单面板（只读列出 Hermes registry 中全部工具，对齐 tools.registry）
export { renderToolsCatalogPanel } from "./panels/toolscatalog.js";

// 委派面板
export { renderDelegationPanel } from "./panels/delegation.js";

// 定时任务面板
export { renderCronPanel } from "./panels/cron.js";

// Wiki / 配置
export { wikiModal, openConfigDialog, fullExport } from "./panels/wiki.js";

// 工作区文件浏览器
export { renderWorkspacePanel, wsBindContext } from "./panels/workspace.js";

// 其他面板
export {
  renderGoalsPanel,
  renderCheckpointsPanel,
  renderMoaPanel,
  renderProjectsPanel,
  renderBundlesPanel,
  renderSecurityPanel,
  renderBlueprintsPanel,
  renderBatchPanel,
  renderJourneyPanel,
  renderBackupPanel,
  renderSnapshotsPanel,
  renderProfilesPanel,
  renderCuratorPanel,
  renderRoutingPanel,
} from "./panels/other.js";
