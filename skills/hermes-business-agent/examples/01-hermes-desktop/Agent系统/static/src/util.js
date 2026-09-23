// @ts-check
/* =====================================================================
 * util.js — 纯工具函数（叶子模块，无 DOM / 无状态，完全可单测）
 * 导出：convDateGroup / estimateTokens / formatUsage / relTime /
 *       toolIcon / extractFilePath
 * 依赖：无
 * ===================================================================== */

const CONTEXT_CAP = 128000; // 估算上下文窗口

/**
 * 把 unix 秒级时间戳归入「今天 / 昨天 / 更早」分组。
 * @param {number} [ts]
 * @returns {"今天"|"昨天"|"更早"}
 */
export function convDateGroup(ts) {
  if (!ts) return "更早";
  const d = new Date(ts * 1000), now = new Date();
  const sod = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const day = 86400000;
  if (ts * 1000 >= sod) return "今天";
  if (ts * 1000 >= sod - day) return "昨天";
  return "更早";
}

/**
 * 按「字符数/4」估算 token 数（进程内路线无网关计费，仅做近似）。
 * @param {string} [s]
 * @returns {number}
 */
export function estimateTokens(s) {
  return Math.ceil((s || "").length / 4);
}

/**
 * 由 {input,output} 估算总量与人民币成本（固定费率，非账单）。
 * @param {{input:number,output:number}} usage
 * @returns {{total:number, cny:number}}
 */
export function formatUsage(usage) {
  const total = (usage.input || 0) + (usage.output || 0);
  const COST_PER_1K_IN = 0.0001;   // USD / 1K 输入 token
  const COST_PER_1K_OUT = 0.0002;  // USD / 1K 输出 token
  const USD_TO_CNY = 7.2;
  const usd = (usage.input / 1000) * COST_PER_1K_IN + (usage.output / 1000) * COST_PER_1K_OUT;
  return { total, cny: usd * USD_TO_CNY };
}

/**
 * 相对时间显示（刚刚 / N分钟前 / N小时前 / N天前）。
 * @param {number} tsSec unix 秒
 * @returns {string}
 */
export function relTime(tsSec) {
  const sec = Math.floor((Date.now() / 1000) - tsSec);
  if (sec < 60) return "刚刚";
  if (sec < 3600) return Math.floor(sec / 60) + "分钟前";
  if (sec < 86400) return Math.floor(sec / 3600) + "小时前";
  return Math.floor(sec / 86400) + "天前";
}

/**
 * 工具图标映射：按名称包含的关键字匹配 emoji。
 * @param {string} name
 * @returns {string}
 */
export function toolIcon(name) {
  const m = {
    file: "📄", write: "✍", patch: "🩹", search: "🔍", python: "🐍",
    browser: "🌐", web: "🔎", memory: "🧠", skill: "🛠", shell: "⌨",
    delegate: "🤝", todo: "📋", kanban: "🗂", image: "🖼", video: "🎞",
  };
  for (const k of Object.keys(m)) if (name.toLowerCase().includes(k)) return m[k];
  return "⚙";
}

/**
 * 从工具结果抽取可预览的文件路径（优先 dict.path，其次字符串里的绝对/盘符路径）。
 * @param {any} res
 * @returns {string|null}
 */
export function extractFilePath(res) {
  if (res && typeof res === "object") {
    const p = res.path || res.file_path || res.filename;
    if (typeof p === "string" && p.trim()) return p.trim();
  }
  if (typeof res === "string") {
    const m = res.match(/(?:[A-Za-z]:[\\/]|\/)[^\s"'<>]+(?:\.[A-Za-z0-9]+)/);
    if (m) return m[0];
  }
  return null;
}

export { CONTEXT_CAP };
