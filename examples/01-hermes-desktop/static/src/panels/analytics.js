// @ts-check
/* =====================================================================
 * analytics.js — analytics 面板子模块
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { getJSON, postJSON, delJSON, parseSSE } from "../api.js";
// ------------------------------------------------------------------ 用量分析
export async function openAnalytics() {
  $("#analyticsMask").classList.remove("hidden");
  const body = $("#analyticsBody");
  body.innerHTML = '<div class="muted">加载中…</div>';
  const data = await getJSON("/api/analytics?days=30");
  if (!data || !data.ok) { body.innerHTML = '<div class="muted">加载失败</div>'; return; }
  renderAnalytics(body, data);
}
export function closeAnalytics() { $("#analyticsMask").classList.add("hidden"); }

export function renderAnalytics(body, d) {
  const t = d.totals || { input: 0, output: 0, total: 0, cost_cny: 0 };
  // 导出 CSV 按钮
  const exportBtn = el("button", { class: "btn ghost sm", style: "float:right;margin-bottom:8px;",
    text: "📊 导出 CSV", onclick: () => exportAnalyticsCSV(d) });
  body.appendChild(exportBtn);
  const html = [];
  html.push('<div class="stat-grid">');
  html.push(statCard(t.total.toLocaleString(), "总 token（估算）"));
  html.push(statCard("¥" + (t.cost_cny || 0).toFixed(4), "估算成本"));
  html.push(statCard(String(d.sessions || 0), "有用量会话"));
  html.push(statCard(String(d.active_days || 0), "活跃天数（近30日）"));
  html.push('</div>');
  html.push('<div class="muted small">' + (d.cost_note || "") + '</div>');

  const series = d.by_day || [];
  const maxDay = Math.max(1, ...series.map((s) => s.total));
  html.push('<h3 class="an-h">近 30 日 token 趋势</h3>');
  html.push('<div class="bars day-bars">');
  for (const s of series) {
    const pct = Math.round((s.total / maxDay) * 100);
    html.push('<div class="bar-row" title="' + s.date + " · " + s.total.toLocaleString() + ' tok">'
      + '<span class="bar-label">' + s.date.slice(5) + '</span>'
      + '<span class="bar-track"><span class="bar-fill" style="width:' + pct + '%"></span></span>'
      + '<span class="bar-val">' + (s.total ? s.total.toLocaleString() : "·") + '</span>'
      + '</div>');
  }
  html.push('</div>');

  const models = d.by_model || [];
  if (models.length) {
    const maxM = Math.max(1, ...models.map((m) => m.total));
    html.push('<h3 class="an-h">按模型分布</h3>');
    html.push('<div class="bars model-bars">');
    for (const m of models) {
      const pct = Math.round((m.total / maxM) * 100);
      html.push('<div class="bar-row">'
        + '<span class="bar-label">' + escapeHtml(m.model) + '</span>'
        + '<span class="bar-track"><span class="bar-fill alt" style="width:' + pct + '%"></span></span>'
        + '<span class="bar-val">' + m.total.toLocaleString() + '</span>'
        + '</div>');
    }
    html.push('</div>');
  }
  body.innerHTML = html.join("");
}
function exportAnalyticsCSV(d) {
  const rows = [];
  const t = d.totals || {};
  rows.push("类别,指标,值");
  rows.push("总计,总 token," + (t.total || 0));
  rows.push("总计,输入 token," + (t.input || 0));
  rows.push("总计,输出 token," + (t.output || 0));
  rows.push("总计,估算成本," + (t.cost_cny || 0).toFixed(6));
  rows.push("总计,有用量会话," + (d.sessions || 0));
  rows.push("总计,活跃天数," + (d.active_days || 0));
  const series = d.by_day || [];
  for (const s of series) {
    rows.push("每日," + s.date + "," + (s.total || 0));
  }
  const models = d.by_model || [];
  for (const m of models) {
    rows.push("模型," + escapeCsv(m.model) + "," + (m.total || 0));
  }
  const csv = rows.join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = el("a", { href: url, download: "analytics-export-" + new Date().toISOString().slice(0, 10) + ".csv" });
  document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  toast("分析数据已导出", "ok");
}
function escapeCsv(v) {
  if (v == null) return "";
  const s = String(v);
  return s.includes(",") || s.includes('"') || s.includes("\n") ? '"' + s.replace(/"/g, '""') + '"' : s;
}
function statCard(value, label) {
  return '<div class="stat-card"><div class="stat-value">' + value + '</div><div class="stat-label">' + label + '</div></div>';
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

