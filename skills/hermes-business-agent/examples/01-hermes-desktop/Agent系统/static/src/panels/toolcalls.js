// @ts-check
/* =====================================================================
 * toolcalls.js — 工具调用信息面板子模块
 * 对话过程中的工具调用与参数配置，统一汇总到「工具调用信息」抽屉，
 * 不再内联在对话区。抽屉内的卡片由 chat.js 实时写入 #toolCallsList。
 * ===================================================================== */
import { $ } from "../dom.js";
import * as Chat from "../chat.js";

// 打开抽屉
export function openToolCalls() {
  const d = $("#toolCallsDrawer");
  if (d) d.classList.remove("hidden");
  Chat.updateToolCallsEmpty();
}

// 关闭抽屉
export function closeToolCalls() {
  const d = $("#toolCallsDrawer");
  if (d) d.classList.add("hidden");
}

// 清空本对话的工具调用记录（委托 chat.js 重置 FIFO 队列与计数）
export function clearToolCalls() {
  Chat.clearToolCallsPanel();
}
