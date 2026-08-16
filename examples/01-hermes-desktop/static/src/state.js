// @ts-check
/* =====================================================================
 * state.js — 全局状态 + 主题 / 皮肤（叶子模块）
 * 导出：State / SKINS / applyTheme / toggleTheme / applySkin / openSkinMenu
 * 依赖：dom.js（仅 $ / el，函数体内访问，无加载期耦合）
 * ===================================================================== */
import { $, el } from "./dom.js";

/** 全局运行时状态（被所有视图/交互共享、可变） */
export const State = {
  conv_id: null,
  model_id: null,
  model_label: "默认模型",
  web_search: true,
  deep_think: false,
  attachments: [],                 // 本轮上传的附件（上传后注入上下文）
  context_folder: null,            // 当前会话绑定的固定文件夹上下文（每轮自动注入；{root,rel,display}）
  skill_id: null,                  // 当前对话指定的技能（发送时注入）
  usage: { input: 0, output: 0 },   // 当前会话 token 估算（进程内路线无 provider 账单）
  theme: localStorage.getItem("hermes_theme") || "light",
  skin: localStorage.getItem("hermes_skin") || "default",
  streaming: false,
  activeStreams: new Map(),  // conv_id -> true（所有活跃流，含后台）
  cancel: null,
  replace_index: null,    // B1：重生成/编辑时，被替换用户消息在 user 序列中的序号
  commands: null,        // 原生指令缓存
  model_cache: null,
  currentView: "chat",    // 主区当前视图：chat | skills | models | cron
  selectedConvs: new Set(),   // 会话列表勾选集合（批量操作用）
  visibleConvIds: [],         // 当前列表可见会话 id（全选用）
};

/** 主题皮肤清单（对标 hermes-webui skins） */
export const SKINS = [
  ["default", "默认", "#6d5efc"],
  ["ares", "Ares", "#e5484d"],
  ["mono", "Mono", "#2b2f36"],
  ["slate", "Slate", "#3b82f6"],
  ["poseidon", "Poseidon", "#0ea5a4"],
  ["charizard", "Charizard", "#f97316"],
  ["sienna", "Sienna", "#b45309"],
  ["catppuccin", "Catppuccin", "#c780e8"],
  ["nous", "Nous", "#6d5efc"],
];

/** 应用主题到 <html data-theme> 并同步按钮/Mermaid */
export function applyTheme() {
  document.documentElement.setAttribute("data-theme", State.theme);
  const _ic = document.getElementById("themeIcon");
  if (_ic) _ic.textContent = State.theme === "dark" ? "☀" : "🌗";
  if (window.mermaid) { try { window.mermaid.initialize({ startOnLoad: false, theme: State.theme === "dark" ? "dark" : "default" }); } catch (_) {} }
}

/** 切换明暗主题 */
export function toggleTheme() {
  State.theme = State.theme === "dark" ? "light" : "dark";
  localStorage.setItem("hermes_theme", State.theme);
  applyTheme();
}

/** 应用皮肤到 <html data-skin> */
export function applySkin() {
  document.documentElement.setAttribute("data-skin", State.skin);
}

/** 弹出皮肤选择浮层 */
export function openSkinMenu() {
  const old = $("#skinMenu");
  if (old) { old.remove(); return; }
  const pop = el("div", { class: "skin-pop", id: "skinMenu" }, [
    el("div", { class: "sp-title", text: "主题皮肤" }),
  ]);
  const grid = el("div", { class: "skin-grid" });
  for (const [id, label, color] of SKINS) {
    grid.appendChild(el("div", {
      class: "skin-swatch" + (State.skin === id ? " active" : ""),
      onclick: () => {
        State.skin = id;
        localStorage.setItem("hermes_skin", id);
        applySkin();
        pop.remove();
      },
    }, [
      el("div", { class: "sw-dot", style: `background:${color}` }),
      el("div", { text: label }),
    ]));
  }
  pop.appendChild(grid);
  $(".topbar").appendChild(pop);
  setTimeout(() => document.addEventListener("click", function close(ev) {
    if (!pop.contains(ev.target) && ev.target.id !== "btnSkin") { pop.remove(); document.removeEventListener("click", close); }
  }), 0);
}
