// @ts-check
/* =====================================================================
 * api.js — HTTP 客户端 + SSE 解析（叶子模块，纯函数可单测）
 * 导出：api / getJSON / postJSON / delJSON / parseSSE
 * 依赖：无（纯标准 fetch + DOM 无关）
 * ===================================================================== */

/**
 * 统一请求客户端：GET/POST/DELETE，自动 JSON 编解码，非 2xx 抛错。
 * @param {string} method
 * @param {string} path
 * @param {any} [body]
 * @returns {Promise<any>}
 */
export async function api(method, path, body) {
  const opt = { method, headers: {} };
  if (body !== undefined) {
    opt.headers["Content-Type"] = "application/json";
    opt.body = JSON.stringify(body);
  }
  const res = await fetch(path, opt);
  let data = null;
  try { data = await res.json(); } catch (_) { /* no body */ }
  if (!res.ok) {
    const msg = (data && (data.error || data.message)) || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data || {};
}

export const getJSON = (p) => api("GET", p);
export const postJSON = (p, b) => api("POST", p, b || {});
export const delJSON = (p, b) => api("DELETE", p, b || {});

/**
 * 标准 SSE 累积器（纯函数，便于单测）。
 * 按 "\n\n" 切分事件；事件内逐行解析，跳过注释行（: 开头），
 * 提取所有 "data:" 行并用 "\n" 连接（兼容含换行的结果），JSON.parse 失败则跳过。
 *
 * 入参 text 为累积缓冲区（可能含未完成的尾部块），返回已解析事件数组 + 剩余尾部。
 * 注：与后端单 data 行协议兼容；多 data 行事件按 "\n" 拼接，覆盖 /api/chat 与
 *     /api/toolsets/trial 两种流（二者后端格式一致）。
 *
 * @param {string} text 累积缓冲区
 * @returns {{ events: any[], rest: string }}
 */
export function parseSSE(text) {
  const blocks = text.split("\n\n");
  const rest = blocks.pop() || "";
  const events = [];
  for (const block of blocks) {
    if (!block.trim()) continue;
    let data = "";
    for (const line of block.split("\n")) {
      if (line.startsWith(":")) continue;
      if (line.startsWith("data:")) {
        data += (data ? "\n" : "") + line.slice(5).replace(/^ /, "");
      }
    }
    if (!data) continue;
    try { events.push(JSON.parse(data)); } catch (_) { /* 跳过不可解析块 */ }
  }
  return { events, rest };
}
