// @ts-check
/* =====================================================================
 * skills.js — skills 面板子模块（技能商店）
 * ===================================================================== */
import { el } from "../dom.js";

export async function renderSkillsPanel(body) {
  body.innerHTML = "";
  const sroot = el("div", { id: "skillStoreRoot", class: "skill-store" });
  body.appendChild(sroot);
  if (window.initSkillStore) window.initSkillStore("skillStoreRoot");
}
