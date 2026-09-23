// @ts-check
/* =====================================================================
 * utils — utils 面板子模块
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
export function escapeCsv(v) {
  if (v == null) return "";
  const s = String(v);
  return s.includes(",") || s.includes('"') || s.includes("\n") ? '"' + s.replace(/"/g, '""') + '"' : s;
}
export function statCard(value, label) {
  return '<div class="stat-card"><div class="stat-value">' + value + '</div><div class="stat-label">' + label + '</div></div>';
}
export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ------------------------------------------------------------------ 通用：双 Tab 容器
export function panelTabs(body, tabs) {
  const bar = el("div", { class: "tabbar" });
  const content = el("div", { class: "tab-content" });
  function select(idx) {
    Array.from(bar.children).forEach((b, i) => b.classList.toggle("active", i === idx));
    content.innerHTML = "";
    try { tabs[idx].render(content); } catch (e) { content.appendChild(el("div", { class: "muted", text: "渲染失败：" + e.message })); }
  }
  tabs.forEach((t, i) => {
    bar.appendChild(el("button", { class: "tab" + (i === 0 ? " active" : ""), text: t.label, onclick: () => select(i) }));
  });
  body.appendChild(bar);
  body.appendChild(content);
  select(0);
}

