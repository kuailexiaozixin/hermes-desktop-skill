// @ts-check
/* =====================================================================
 * dom.js — 低层 DOM 工具（叶子模块，零业务依赖）
 * 导出：$ / $$ / el / esc / toast / addCodeCopyButtons /
 *       ensureMermaid / renderMermaid / postProcessBubble
 * 依赖：state.js（仅 mermaid 主题跟随需要 State.theme，函数体内访问，无加载期耦合）
 * ===================================================================== */
import { State } from "./state.js";

/**
 * @typedef {Object} ElAttrs
 * @property {string} [class]
 * @property {string} [html]
 * @property {string} [text]
 * @property {string} [id]
 * @property {Record<string,string>} [dataset]
 * @property {Record<string, (ev: Event) => void>} [on*]
 */

/** 单元素查询（自定义 querySelector 简写，非 jQuery） */
export const $ = (sel, root = document) => root.querySelector(sel);
/** 多元素查询，返回真数组 */
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

/**
 * 轻量元素构造器：attrs 支持 class/html/text/id/dataset/事件(on*)/普通属性。
 * @param {string} tag
 * @param {Record<string, any>} [attrs]
 * @param {(Node|string|null|undefined)[]|Node|string} [children]
 * @returns {HTMLElement}
 */
export function el(tag, attrs = {}, children = []) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null) continue;
    if (k === "class") e.className = v;
    else if (k === "html") e.innerHTML = v;
    else if (k === "text") e.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") e.addEventListener(k.slice(2), v);
    else if (k === "dataset") Object.assign(e.dataset, v);
    else e.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null) continue;
    e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return e;
}

/** HTML 转义（与后端 esc 等价，前端渲染纯文本/属性时使用） */
export function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

let toastTimer = null;
/** 右下角轻提示 */
export function toast(msg, kind = "") {
  const box = $("#toasts");
  const t = el("div", { class: "toast " + kind, text: msg });
  box.appendChild(t);
  setTimeout(() => t.remove(), 2600);
}

// ------------------------------------------------------------------ 气泡后处理：代码复制 + Mermaid
/** 为所有 <pre> 挂「复制」按钮（幂等） */
export function addCodeCopyButtons(root) {
  $$("pre", root).forEach((pre) => {
    if (pre.querySelector(".code-copy")) return;
    const btn = el("button", { class: "code-copy", text: "复制", onclick: async () => {
      const code = pre.querySelector("code");
      const txt = code ? code.textContent : pre.textContent;
      try { await navigator.clipboard.writeText(txt); btn.textContent = "已复制"; setTimeout(() => (btn.textContent = "复制"), 1200); }
      catch (_) {
        // fallback：textarea + execCommand
        try {
          const ta = document.createElement("textarea");
          ta.value = txt;
          ta.style.position = "fixed"; ta.style.left = "-9999px";
          document.body.appendChild(ta);
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);
          btn.textContent = "已复制"; setTimeout(() => (btn.textContent = "复制"), 1200);
        } catch (_2) { btn.textContent = "失败"; }
      }
    } });
    pre.appendChild(btn);
  });
}

let _mermaidLoading = null, _mermaidSeq = 0;
/** 懒加载 mermaid（CDN 不可达时静默失败，保留原始代码块） */
export function ensureMermaid() {
  if (window.mermaid) return Promise.resolve();
  if (_mermaidLoading) return _mermaidLoading;
  _mermaidLoading = new Promise((resolve) => {
    const s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js";
    s.onload = () => { try { window.mermaid.initialize({ startOnLoad: false, theme: State.theme === "dark" ? "dark" : "default" }); } catch (_) {} resolve(); };
    s.onerror = () => { _mermaidLoading = null; resolve(); };
    document.head.appendChild(s);
  });
  return _mermaidLoading;
}

/** 把 ```mermaid 代码块渲染为 SVG（失败则保留文本） */
export async function renderMermaid(root) {
  const blocks = $$("pre code.language-mermaid", root);
  if (!blocks.length) return;
  await ensureMermaid();
  if (!window.mermaid) return;
  for (const code of blocks) {
    const pre = code.parentElement;
    const src = code.textContent;
    const box = el("div", { class: "mermaid-block" });
    pre.replaceWith(box);
    try {
      const id = "mmd-" + (++_mermaidSeq);
      const { svg } = await window.mermaid.render(id, src);
      box.innerHTML = svg;
    } catch (e) {
      box.className = "mermaid-block error";
      box.textContent = "Mermaid 渲染失败：" + ((e && e.message) || e);
    }
  }
}

/** 单条消息气泡的后处理：代码复制按钮 + Mermaid 渲染 */
export function postProcessBubble(bubble) {
  if (!bubble) return;
  addCodeCopyButtons(bubble);
  renderMermaid(bubble);
}
