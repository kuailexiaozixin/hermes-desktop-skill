// @ts-check
/* =====================================================================
 * wiki.js — wiki 面板子模块
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { State } from "../state.js";
import { getJSON, postJSON, delJSON, parseSSE } from "../api.js";
import * as Views from "../views.js";
export function wikiModal(mode, data) {
  const ov = el("div", { class: "ov" });
  const box = el("div", { class: "ov-box" });
  box.appendChild(el("div", { class: "section-title", text: mode === "create" ? "新建 Wiki 页面" : "编辑 Wiki 页面" }));
  const ti = el("input", { class: "form-input" });
  ti.value = (data && data.title) || "";
  const ty = el("select", { class: "form-input" }, [
    el("option", { value: "summary", text: "综述 summary" }),
    el("option", { value: "entity", text: "实体 entity" }),
    el("option", { value: "concept", text: "概念 concept" }),
    el("option", { value: "comparison", text: "对比 comparison" }),
    el("option", { value: "query", text: "问答 query" }),
  ]);
  ty.value = (data && data.type) || "summary";
  const ca = el("input", { class: "form-input" });
  ca.value = (data && data.category) || "通用";
  const tg = el("input", { class: "form-input" });
  tg.value = ((data && data.tags) || []).join(",");
  const sr = el("input", { class: "form-input", placeholder: "溯源 raw 名（逗号分隔，可选）" });
  sr.value = ((data && data.sources) || []).join(",");
  const cf = el("select", { class: "form-input" }, [
    el("option", { value: "", text: "置信度（可选）" }),
    el("option", { value: "high", text: "high" }),
    el("option", { value: "medium", text: "medium" }),
    el("option", { value: "low", text: "low" }),
  ]);
  cf.value = (data && data.confidence) || "";
  const ta = el("textarea", { class: "editor", rows: 14, placeholder: "正文（Markdown）。用 [[slug]] 互联其它页面，如 [[concepts/attention]]" });
  ta.value = (data && data.body) || "";
  box.appendChild(el("div", { class: "field" }, [el("label", { text: "标题" }), ti]));
  box.appendChild(el("div", { class: "field" }, [el("label", { text: "类型 type（决定落盘目录）" }), ty]));
  box.appendChild(el("div", { class: "field" }, [el("label", { text: "分类 category（兼容旧字段）" }), ca]));
  box.appendChild(el("div", { class: "field" }, [el("label", { text: "标签（逗号分隔）" }), tg]));
  box.appendChild(el("div", { class: "field" }, [el("label", { text: "溯源 sources" }), sr]));
  box.appendChild(el("div", { class: "field" }, [el("label", { text: "置信度 confidence" }), cf]));
  box.appendChild(el("div", { class: "field" }, [el("label", { text: "正文（Markdown，支持 [[wikilinks]]）" }), ta]));
  // 反向链接栏（编辑态显示）
  if (data && (data.inbound || []).length) {
    const bl = el("div", { class: "wiki-backlinks" });
    bl.appendChild(el("div", { class: "wiki-bl-title", text: "反向链接（" + data.inbound.length + "）" }));
    for (const s of data.inbound) bl.appendChild(el("div", { class: "wiki-bl-item", text: s, onclick: () => { ov.remove(); wikiReaderPublic(s); } }));
    box.appendChild(bl);
  }
  // wikilink 自动补全
  const ac = el("div", { class: "wiki-ac hidden" });
  box.appendChild(ac);
  let _slugs = null;
  async function ensureSlugs() {
    if (_slugs) return _slugs;
    const r = await getJSON("/api/wiki").catch(() => ({ ok: false }));
    _slugs = (r.ok && (r.items || []).map((x) => x.slug)) || [];
    return _slugs;
  }
  ta.addEventListener("input", async () => {
    const pos = ta.selectionStart;
    const before = ta.value.slice(0, pos);
    const m = before.match(/\[\[([^\]\n]*)$/);
    if (!m) { ac.classList.add("hidden"); return; }
    const q = m[1].toLowerCase();
    const slugs = await ensureSlugs();
    const hits = slugs.filter((s) => s.toLowerCase().includes(q)).slice(0, 8);
    if (!hits.length) { ac.classList.add("hidden"); return; }
    ac.innerHTML = "";
    hits.forEach((s) => ac.appendChild(el("div", { class: "wiki-ac-item", text: s, onclick: () => {
      const pre = ta.value.slice(0, pos - m[1].length);
      const post = ta.value.slice(pos);
      ta.value = pre + "[[" + s + "]]" + post;
      ac.classList.add("hidden");
      ta.focus();
    } })));
    ac.classList.remove("hidden");
  });
  box.appendChild(el("div", { class: "actions-row" }, [
    el("button", { class: "btn primary", text: "保存", onclick: async () => {
      const payload = {
        title: ti.value.trim(), category: ca.value.trim() || "通用",
        tags: tg.value.split(",").map(s => s.trim()).filter(Boolean),
        type: ty.value, sources: sr.value.split(",").map(s => s.trim()).filter(Boolean),
        confidence: cf.value, text: ta.value,
      };
      if (mode === "edit" && data && data.slug) payload.name = data.slug + ".md";
      const r = await postJSON("/api/wiki", payload).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast("已保存", "ok"); ov.remove(); Views.renderWikiView(); } else toast("保存失败：" + (r.error || ""), "err");
    } }),
    el("button", { class: "btn ghost", text: "取消", onclick: () => ov.remove() }),
  ]));
  ov.appendChild(box);
  ov.addEventListener("click", e => { if (e.target === ov) ov.remove(); });
  document.body.appendChild(ov);
}

// wikiReader 暴露给 panels（反链点击跳转）
function wikiReaderPublic(slug) { if (window.__wikiReader) window.__wikiReader(slug); }

export async function openConfigDialog() {
  const ov = el("div", { class: "ov" });
  const box = el("div", { class: "ov-box", style: "max-width:500px;" });
  box.appendChild(el("div", { class: "section-title", text: "⚙ 配置管理" }));
  box.appendChild(el("div", { class: "muted small", text: "导出或导入配置（模型、技能、MCP）。导入会覆盖当前配置。" }));
  const btnRow = el("div", { style: "display:flex;gap:8px;margin:12px 0;" });
  const exportBtn = el("button", { class: "btn primary", text: "⭳ 导出配置", onclick: async () => {
    try {
      const r = await getJSON("/api/config/export");
      if (!r.ok) { toast("导出失败：" + (r.error || ""), "err"); return; }
      const blob = new Blob([JSON.stringify(r.config, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = el("a", { href: url, download: "hermes-config-export-" + new Date().toISOString().slice(0, 10) + ".json" });
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      toast("配置已导出", "ok");
    } catch (e) { toast("导出失败：" + e.message, "err"); }
  } });
  const importInp = el("input", { type: "file", accept: ".json,application/json", style: "display:none;",
    onchange: async () => {
      const f = importInp.files[0]; if (!f) return;
      try {
        const cfg = JSON.parse(await f.text());
        const r = await postJSON("/api/config/import", { config: cfg });
        if (r.ok) { toast("配置已导入，部分配置可能需要重启生效", "ok"); ov.remove(); }
        else toast("导入失败：" + (r.error || ""), "err");
      } catch (e) { toast("导入失败：" + e.message, "err"); }
      importInp.value = "";
    } });
  const importBtn = el("button", { class: "btn ghost", text: "📥 导入配置", onclick: () => importInp.click() });
  btnRow.appendChild(exportBtn);
  btnRow.appendChild(importBtn);
  box.appendChild(btnRow);
  box.appendChild(importInp);
  box.appendChild(el("button", { class: "btn ghost", style: "margin-top:8px;", text: "关闭",
    onclick: () => ov.remove() }));
  ov.appendChild(box);
  ov.addEventListener("click", (e) => { if (e.target === ov) ov.remove(); });
  document.body.appendChild(ov);
}



export async function fullExport() {
  try {
    const resp = await fetch("/api/export/full");
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: "HTTP " + resp.status }));
      toast("导出失败：" + (err.error || ""), "err");
      return;
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = el("a", { href: url, download: "hermes-export-" + new Date().toISOString().slice(0, 10) + ".zip" });
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    toast("全量数据已导出", "ok");
  } catch (e) { toast("导出失败：" + e.message, "err"); }
}

