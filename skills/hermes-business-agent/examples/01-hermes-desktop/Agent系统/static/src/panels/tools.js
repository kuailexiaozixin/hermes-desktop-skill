// @ts-check
/* =====================================================================
 * tools.js — 统一工具面板（方案 B 重构：三层渐进披露）
 *   第一层：分类折叠组（组头摘要「启用 x/y · 就绪 m」，默认折叠无启用无就绪的组）
 *   第二层：工具集卡片（状态徽标 + 智能主按钮 + ⋯ 全动作菜单 + 开关）
 *   第三层：卡片内「工具明细」展开区（只读——内核 0.19.0 仅支持工具集级启停）
 *   懒渲染：清单 Tab 默认渲染；管理 Tab 首次激活才请求 /api/toolsets。
 *   徽章逻辑统一为 stateBadge()，消除重构前的双份复读。
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { State } from "../state.js";
import { getJSON, postJSON, delJSON, parseSSE } from "../api.js";
import * as Views from "../views.js";
import * as Chat from "../chat.js";
import { renderToolsCatalogPanel } from "./toolscatalog.js";

// ── 统一徽章判定（原初始渲染/开关回调两处的 5 分支复读合并于此）──────────
function stateBadge(ts) {
  if (ts.arch_disabled) return { label: "禁用", cls: "off" };
  if (ts.disabled) return { label: "已禁用", cls: "off" };
  if (ts.available && ts.configured) return { label: "已配置", cls: "on" };
  if (ts.available && !ts.configured) return { label: "部分配置", cls: "warn" };
  return { label: "未就绪", cls: "warn" };
}

function relTime(tsSec) {
  const sec = Math.floor((Date.now() / 1000) - tsSec);
  if (sec < 60) return "刚刚";
  if (sec < 3600) return Math.floor(sec / 60) + "分钟前";
  if (sec < 86400) return Math.floor(sec / 3600) + "小时前";
  return Math.floor(sec / 86400) + "天前";
}

// 智能主按钮：未配置→配置；已配置未测过→测试；测过且可用→试用
function primaryAction(ts) {
  if (!ts.available || !ts.configured) return { text: "⚙ 配置并检测", act: "config" };
  if (ts.last_test && ts.last_test.available) return { text: "▶ 试用", act: "trial" };
  return { text: "🧪 测试", act: "test" };
}

// ── ⋯ 溢出菜单（全局单例监听，防止重复绑定）─────────────────────────────
let _openMenuEl = null;
if (!window._toolMenuListenerBound) {
  window._toolMenuListenerBound = true;
  document.addEventListener("click", (e) => {
    if (_openMenuEl && !_openMenuEl.contains(e.target)) {
      _openMenuEl.classList.remove("open");
      _openMenuEl = null;
    }
  });
}

function runAction(act, ts) {
  if (act === "config") return openToolsetConfig(ts);
  if (act === "test") return openToolsetTest(ts);
  if (act === "trial") return openToolsetTrial(ts);
}

// ── 工具明细缓存（/api/tools-catalog 全局面板共享）────────────────────────
async function getCatalogCache() {
  if (window.__toolsCatalogCache) return window.__toolsCatalogCache;
  try {
    const d = await getJSON("/api/tools-catalog");
    if (d && d.ok) window.__toolsCatalogCache = d;
  } catch (_) { /* 静默：明细描述缺失不影响展示工具名 */ }
  return window.__toolsCatalogCache || null;
}

// ------------------------------------------------------------------ 工具管理子面板
export async function renderToolsManagePanel(body) {
  let data;
  try { data = await getJSON("/api/toolsets"); }
  catch (e) { body.appendChild(el("div", { class: "muted", text: "工具矩阵不可用：" + e.message })); return; }
  if (!data.ok) {
    body.appendChild(el("div", { class: "muted", text: "工具矩阵不可用：" + (data.hint || data.error || "") }));
    return;
  }
  const items = data.items || [];
  const categoryOrder = data.category_order || [];

  async function build() {
    body.innerHTML = "";
    const wrap = el("div", { class: "panel" });
    wrap.appendChild(el("div", { class: "muted", text: `架构默认禁用：${(data.disabled_toolsets || []).join(", ") || "无"}；自动化工具集：${(data.automation || []).join(", ") || "无"}` }));

    // ── 控制条：搜索 + 场景预设 + 排序 + 全部检测/启用/禁用 ──
    if (window._toolSearchQuery === undefined) window._toolSearchQuery = "";
    const searchRow = el("div", { class: "tool-search-row" });
    const searchInput = el("input", { class: "form-input", placeholder: "🔍 搜索工具集名称/用途…",
      value: window._toolSearchQuery || "",
      oninput: () => { window._toolSearchQuery = searchInput.value; applyFilter(); } });

    const profSel = el("select", { class: "form-input tool-profile-select", title: "场景预设：一键批量启停工具集" });
    profSel.appendChild(el("option", { value: "", text: "场景预设…", disabled: "disabled" }));

    const sortSelect = el("select", { class: "tool-sort",
      onchange: () => { window._toolSortQuery = sortSelect.value; build(); } });
    if (window._toolSortQuery) sortSelect.value = window._toolSortQuery;
    if (!sortSelect.value || sortSelect.selectedIndex < 0) sortSelect.value = "name";
    sortSelect.appendChild(el("option", { value: "name", text: "名称↑" }));
    sortSelect.appendChild(el("option", { value: "name_desc", text: "名称↓" }));
    sortSelect.appendChild(el("option", { value: "state", text: "状态↑" }));
    sortSelect.appendChild(el("option", { value: "state_desc", text: "状态↓" }));
    if (window._toolSortQuery) sortSelect.value = window._toolSortQuery;

    const testAll = el("button", { class: "btn ghost sm", text: "🔍 全部检测", onclick: async () => {
      testAll.disabled = true; testAll.textContent = "检测中…";
      const r = await postJSON("/api/toolsets/test-all", {}).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) {
        const avail = Object.values(r.results).filter(v => v.available).length;
        toast(`全部检测完成：${avail}/${r.total} 可用`, "ok");
        Views.refreshPanels();
      } else { toast("检测失败：" + (r.error || ""), "err"); testAll.disabled = false; testAll.textContent = "🔍 全部检测"; }
    } });
    const batchAll = el("button", { class: "btn ghost sm", text: "全部启用", onclick: async () => {
      const names = items.filter(t => !t.arch_disabled).map(t => t.name);
      const unconf = items.filter(t => !t.arch_disabled && !t.configured).length;
      if (unconf > 0 && !confirm(`有 ${unconf} 个工具集未配置依赖，启用后仍不可用。确定继续？`)) return;
      const r = await postJSON("/api/toolsets/batch", { names, disabled: false }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast("已全部启用", "ok"); Views.refreshPanels(); } else toast("操作失败：" + (r.error || ""), "err");
    } });
    const batchNone = el("button", { class: "btn ghost sm", text: "全部禁用", onclick: async () => {
      const enabled = items.filter(t => !t.arch_disabled && t.enabled);
      if (!enabled.length) { toast("已全部禁用", "ok"); return; }
      const names = enabled.map(t => t.name);
      if (!confirm(`确定禁用 ${enabled.length} 个已启用的工具集？`)) return;
      if (!confirm(`⚠ 二次确认：这将禁用 ${enabled.map(t=>t.label||t.name).join("、")} 等 ${enabled.length} 个工具集，包括可用能力。确定继续？`)) return;
      const r = await postJSON("/api/toolsets/batch", { names, disabled: true }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast("已全部禁用", "ok"); Views.refreshPanels(); } else toast("操作失败：" + (r.error || ""), "err");
    } });

    // 场景预设下拉（方案 C）
    try {
      const pd = await getJSON("/api/toolsets/profiles");
      if (pd && pd.ok) {
        for (const p of pd.profiles || []) {
          const opt = el("option", { value: p.key, text: "🎛 " + p.name });
          opt.title = p.desc || "";
          profSel.appendChild(opt);
        }
        profSel.value = (pd.current && pd.current !== "custom") ? pd.current : "";
        profSel.onchange = async () => {
          const key = profSel.value;
          if (!key) return;
          const p = (pd.profiles || []).find(x => x.key === key);
          const willDisable = key === "full" ? 0 :
            items.filter(t => !t.arch_disabled && !(new Set((p && p.enabled) || [])).has(t.name) && t.enabled).length;
          const tip = key === "full"
            ? "将启用除架构禁用外的全部工具集。"
            : `「${p ? p.name : key}」预设：${(p && p.desc) || ""}。当前将额外禁用 ${willDisable} 个已启用工具集。`;
          if (!confirm(tip + "\n确定应用？")) { profSel.value = (pd.current && pd.current !== "custom") ? pd.current : ""; return; }
          const r = await postJSON("/api/toolsets/profile", { key }).catch(e => ({ ok: false, error: e.message }));
          if (r.ok) { toast(`已应用预设「${p ? p.name : key}」`, "ok"); Views.refreshPanels(); }
          else { toast("应用预设失败：" + (r.error || ""), "err"); }
        };
      }
    } catch (_) { /* 预设不可用时控制条其余部分照常 */ }

    searchRow.appendChild(searchInput);
    searchRow.appendChild(profSel);
    searchRow.appendChild(sortSelect);
    searchRow.appendChild(testAll);
    searchRow.appendChild(batchAll);
    searchRow.appendChild(batchNone);
    wrap.appendChild(searchRow);

    // ── 第一层：分类折叠组 ──
    const groupsBox = el("div", { class: "tools-groups" });
    const groupState = window._toolGroupState || (window._toolGroupState = {});

    // 组内排序
    const sortMode = window._toolSortQuery || "name";
    function sortRows(arr) {
      const a = arr.slice();
      a.sort((x, y) => {
        const xn = x.label || x.name, yn = y.label || y.name;
        const xs = stateBadge(x).label, ys = stateBadge(y).label;
        if (sortMode === "name") return xn.localeCompare(yn);
        if (sortMode === "name_desc") return yn.localeCompare(xn);
        if (sortMode === "state") return xs.localeCompare(ys);
        if (sortMode === "state_desc") return ys.localeCompare(xs);
        return 0;
      });
      return a;
    }
    // 分类分组（按后端 category_order 排序，未登记分类置底）
    const byCat = new Map();
    for (const ts of items) {
      const c = ts.category || "🔧 其他";
      if (!byCat.has(c)) byCat.set(c, []);
      byCat.get(c).push(ts);
    }
    const orderedCats = [];
    for (const c of categoryOrder) if (byCat.has(c)) orderedCats.push(c);
    for (const c of byCat.keys()) if (!orderedCats.includes(c)) orderedCats.push(c);

    for (const cat of orderedCats) {
      const catItems = sortRows(byCat.get(cat));
      const enabledCnt = catItems.filter(t => t.enabled).length;
      const readyCnt = catItems.filter(t => t.available && t.configured).length;
      const defaultClosed = groupState[cat] !== undefined
        ? groupState[cat]
        : (enabledCnt === 0 && readyCnt === 0);

      const gBody = el("div", { class: "tools-group-body" });
      const group = el("div", { class: "tools-group" + (defaultClosed ? " closed" : "") });
      const gHead = el("div", { class: "tools-group-head", onclick: () => {
        group.classList.toggle("closed");
        groupState[cat] = group.classList.contains("closed");
      } }, [
        el("span", { class: "gg-name", text: cat }),
        el("span", { class: "gg-summary", text: `启用 ${enabledCnt}/${catItems.length} · 就绪 ${readyCnt}` }),
        el("span", { class: "gg-chev", text: "▾" }),
      ]);
      for (const ts of catItems) gBody.appendChild(buildToolsetCard(ts));
      group.appendChild(gHead);
      group.appendChild(gBody);
      groupsBox.appendChild(group);
    }
    wrap.appendChild(groupsBox);
    body.appendChild(wrap);

    // 搜索过滤（对行 + 空组隐藏；搜索中强制展开组体便于命中可见）
    function applyFilter() {
      const q = searchInput.value.trim().toLowerCase();
      wrap.classList.toggle("tools-searching", !!q);
      for (const group of groupsBox.children) {
        let visible = 0;
        for (const row of group.querySelectorAll(".card-row")) {
          const txt = (row.dataset.search || "").toLowerCase();
          const show = (!q || txt.includes(q));
          row.style.display = show ? "" : "none";
          if (show) visible++;
        }
        group.style.display = visible ? "" : "none";
      }
    }
  }

  await build();
}

// ------------------------------------------------------------------ 第二层：工具集卡片
function buildToolsetCard(ts) {
  const archDisabled = !!ts.arch_disabled;
  const badge = stateBadge(ts);

  const sw = el("label", { class: "switch" + (archDisabled ? " muted" : "") }, [
    el("input", { type: "checkbox", ...(ts.enabled ? { checked: "checked" } : {}),
      ...(archDisabled ? { disabled: "disabled" } : {}),
      onchange: async (ev) => {
        ev.target.disabled = true;
        const r = await postJSON("/api/toolsets/toggle", { name: ts.name, disabled: !ev.target.checked }).catch((e) => ({ ok: false, error: e.message }));
        if (!r.ok) { toast("切换失败：" + (r.error || ""), "err"); ev.target.checked = ts.enabled; ev.target.disabled = false; }
        else {
          ev.target.disabled = false;
          ts.enabled = ev.target.checked;
          ts.disabled = !ev.target.checked;
          const card = ev.target.closest(".card-row");
          if (card) {
            const b2 = stateBadge(ts);
            const badgeEl = card.querySelector(".badge.state");
            if (badgeEl) { badgeEl.textContent = b2.label; badgeEl.className = "badge state " + b2.cls; }
            card.dataset.state = b2.label;
          }
        }
      } }),
    el("span", { class: "slider" }),
  ]);

  const actions = el("div", { class: "cr-actions" });
  if (!archDisabled) {
    const pa = primaryAction(ts);
    actions.appendChild(el("button", { class: "btn ghost sm", text: pa.text, onclick: () => runAction(pa.act, ts) }));
    // ⋯ 溢出菜单：配置/测试/试用全动作保留
    const menuWrap = el("div", { class: "cr-actions-overflow" });
    const menuBtn = el("button", { class: "btn ghost sm", text: "⋯", title: "更多操作" });
    const menu = el("div", { class: "cr-menu" }, [
      el("button", { text: "⚙ 配置", onclick: (e) => { e.stopPropagation(); menu.classList.remove("open"); _openMenuEl = null; openToolsetConfig(ts); } }),
      el("button", { text: "🧪 测试", onclick: (e) => { e.stopPropagation(); menu.classList.remove("open"); _openMenuEl = null; openToolsetTest(ts); } }),
      el("button", { text: "▶ 试用", onclick: (e) => { e.stopPropagation(); menu.classList.remove("open"); _openMenuEl = null; openToolsetTrial(ts); } }),
    ]);
    menuBtn.onclick = (e) => {
      e.stopPropagation();
      if (_openMenuEl && _openMenuEl !== menu) _openMenuEl.classList.remove("open");
      menu.classList.toggle("open");
      _openMenuEl = menu.classList.contains("open") ? menu : null;
    };
    menuWrap.appendChild(menuBtn);
    menuWrap.appendChild(menu);
    actions.appendChild(menuWrap);
  }

  const title = el("div", { class: "cr-title" }, [
    el("span", { text: ts.label || ts.name }),
    el("span", { class: "badge state " + badge.cls, text: badge.label }),
    actions,
  ]);

  const desc = el("div", { class: "cr-desc" });
  const purposeText = ts.configured ? (ts.purpose || "").replace(/\s*（需配置）\s*$/, "") : (ts.purpose || "");
  desc.appendChild(el("span", { text: purposeText }));
  if (ts.requirements && ts.requirements.length)
    desc.appendChild(el("div", { class: "muted", text: "需要：" + ts.requirements.join(", ") }));
  if (ts.runtime_hint && !ts.configured) {
    const simpleHint = ts.requirements && ts.requirements.length ? "需要配置 API 密钥" : "需要安装依赖";
    desc.appendChild(el("div", { class: "muted ts-hint", text: "💡 " + simpleHint }));
  }
  if (ts.reason)
    desc.appendChild(el("div", { class: "muted ts-reason", text: ts.reason }));
  if (ts.last_test) {
    const lt = ts.last_test;
    const testBadge = lt.available ? "✅" : "❌";
    desc.appendChild(el("div", { class: "muted small", text: `测试 ${relTime(lt.ts)}：${testBadge} ${lt.reason || (lt.available ? "正常" : "异常")}` }));
  }

  // ── 第三层：工具明细展开区（只读；内核 0.19.0 仅支持工具集级启停）──
  if (ts.tools && ts.tools.length) {
    const exp = el("div", { class: "tool-expander", text: `▸ 工具明细（${ts.tools.length}，只读）` });
    const box = el("div", { class: "cr-tools" });
    let loaded = false;
    exp.onclick = async () => {
      const open = box.classList.toggle("open");
      exp.textContent = (open ? "▾" : "▸") + ` 工具明细（${ts.tools.length}，只读）`;
      if (open && !loaded) {
        loaded = true;
        const cat = await getCatalogCache();
        const byName = {};
        if (cat && cat.tools) for (const t of cat.tools) byName[t.name] = t;
        for (const tn of ts.tools) {
          const meta = byName[tn.name] || {};
          box.appendChild(el("div", { class: "cr-tools-row" }, [
            el("span", { class: "tname", text: tn.name }),
            tn.disabled ? el("span", { class: "badge off", text: "已停用" }) : null,
            el("span", { class: "muted small tdesc", text: (meta.description || "").slice(0, 80) }),
          ]));
        }
        box.appendChild(el("div", { class: "muted small", style: "margin-top:6px",
          text: "ℹ " + (ts.tools_readonly_note || "内核 0.19.0 仅支持工具集级启停，工具明细为只读展示") }));
      }
    };
    desc.appendChild(exp);
    desc.appendChild(box);
  }

  const row = el("div", { class: "card-row" }, [
    el("div", { class: "cr-main" }, [title, desc]),
    sw,
  ]);
  row.dataset.search = (ts.label || ts.name) + " " + (ts.purpose || "") + " " + (ts.reason || "");
  row.dataset.name = ts.label || ts.name;
  row.dataset.toolset = ts.name;
  row.dataset.state = badge.label;
  return row;
}

// ------------------------------------------------------------------ 统一工具面板（懒渲染）
export async function renderToolsPanel(body) {
  body.innerHTML = "";
  const wrap = el("div", { class: "tools-unified" });

  // ── 顶部子面板切换 Tab ──
  const tabs = el("div", { class: "tools-tabs" });
  const tabCatalog = el("button", { class: "tools-tab active",
    text: "📋 工具清单（只读）", title: "列出 Hermes 注册表中全部工具（name / 工具集 / 入参 / 来源）" });
  const tabManage = el("button", { class: "tools-tab",
    text: "⚙ 工具管理（可操作）", title: "启用 / 配置 / 测试 / 试用工具集" });
  tabs.appendChild(tabCatalog);
  tabs.appendChild(tabManage);
  wrap.appendChild(tabs);

  // ── 两个子面板容器 ──
  const catalogSub = el("div", { class: "tools-subpanel", id: "toolsCatalogSub" });
  const manageSub = el("div", { class: "tools-subpanel hidden", id: "toolsManageSub" });
  wrap.appendChild(catalogSub);
  wrap.appendChild(manageSub);
  body.appendChild(wrap);

  // 懒渲染：默认（清单）Tab 立即渲染；管理 Tab 首次激活才请求 /api/toolsets
  try { await renderToolsCatalogPanel(catalogSub); } catch (e) { catalogSub.appendChild(el("div", { class: "muted", text: "工具清单加载失败：" + e.message })); }
  let manageLoaded = false;
  async function ensureManage() {
    if (manageLoaded) return;
    manageLoaded = true;
    try { await renderToolsManagePanel(manageSub); } catch (e) { manageSub.appendChild(el("div", { class: "muted", text: "工具管理加载失败：" + e.message })); }
  }

  async function switchTab(which) {
    const isCat = which === "catalog";
    tabCatalog.classList.toggle("active", isCat);
    tabManage.classList.toggle("active", !isCat);
    catalogSub.classList.toggle("hidden", !isCat);
    manageSub.classList.toggle("hidden", isCat);
    if (!isCat) await ensureManage();
  }
  tabCatalog.addEventListener("click", () => { switchTab("catalog"); });
  tabManage.addEventListener("click", () => { switchTab("manage"); });
  window.__showToolsTab = (which) => { switchTab(which || "catalog"); };

  // 工具清单 → 工具管理「一键直达」
  window.__gotoToolsManage = async (toolsetName) => {
    await switchTab("manage");
    if (!toolsetName) return;
    setTimeout(() => {
      const panel = document.getElementById("view-tools");
      if (!panel) return;
      let target = null;
      try { target = panel.querySelector('.card-row[data-toolset="' + (window.CSS && CSS.escape ? CSS.escape(toolsetName) : toolsetName) + '"]'); } catch (_) { target = null; }
      if (!target) {
        const rows = panel.querySelectorAll(".card-row");
        for (const r of rows) { if ((r.dataset.name || "").toLowerCase().includes(String(toolsetName).toLowerCase())) { target = r; break; } }
      }
      if (!target) { toast("该工具集不可在「工具管理」中配置", "info"); return; }
      // 若在折叠组内，先展开组
      const grp = target.closest(".tools-group");
      if (grp && grp.classList.contains("closed")) grp.classList.remove("closed");
      try { target.scrollIntoView({ block: "center", behavior: "smooth" }); } catch (_) {}
      target.classList.add("highlight-flash");
      setTimeout(() => { try { target.classList.remove("highlight-flash"); } catch (_) {} }, 1600);
    }, 60);
  };
}

// ------------------------------------------------------------------ 工具集成：配置弹窗
export function openToolsetConfig(ts) {
  const reqs = ts.requirements || [];
  // 单例：先关闭已打开的同类型对话框，避免多次点击叠加
  document.querySelectorAll(".toolcfg-mask").forEach((m) => m.remove());
  const mask = el("div", { class: "toolcfg-mask" });
  const box = el("div", { class: "toolcfg" });
  box.appendChild(el("div", { class: "toolcfg-head" }, [
    el("b", { text: "配置 " + (ts.label || ts.name) }),
    el("button", { class: "btn icon", text: "×", "data-x": "1" }),
  ]));
  const body = el("div", { class: "toolcfg-body" });
  if (!reqs.length) {
    body.appendChild(el("div", { class: "muted", style: "margin-bottom:10px", text: "此工具需要安装依赖后才能使用，点击下方按钮自动完成。" }));
    const status = el("div", { id: "install-status", class: "muted small", style: "margin:8px 0" });
    body.appendChild(status);
    const installBtn = el("button", { class: "btn primary", style: "font-size:15px;padding:8px 20px", text: "🔄 一键检测安装" });
    installBtn.onclick = async () => {
      installBtn.disabled = true; installBtn.textContent = "安装中…"; status.textContent = "正在检测环境…";
      const testR = await postJSON("/api/toolsets/test", { name: ts.name }).catch(e => ({ ok: false, error: e.message }));
      if (!testR.ok) { status.textContent = "❌ 检测失败：" + (testR.error || ""); installBtn.disabled = false; installBtn.textContent = "🔄 重试"; return; }
      if (testR.available) { status.textContent = "✅ 环境已就绪，无需安装！"; installBtn.textContent = "✅ 已完成"; toast("工具已就绪", "ok"); Views.refreshPanels(); return; }
      status.textContent = "正在安装缺失组件…";
      const installR = await postJSON("/api/toolsets/install-deps", { name: ts.name }).catch(e => ({ ok: false, error: e.message }));
      if (!installR.ok) {
        if (installR.error && installR.error.includes("暂不支持一键安装")) {
          status.textContent = "❌ 此工具暂不支持自动安装，请手动完成。";
        } else {
          status.textContent = "❌ 安装失败：" + (installR.error || "");
        }
        installBtn.disabled = false; installBtn.textContent = "🔄 重试";
        return;
      }
      status.textContent = "✅ 安装成功！正在重新检测…";
      const reTest = await postJSON("/api/toolsets/test", { name: ts.name }).catch(e => ({ ok: false, error: e.message }));
      if (reTest.ok && reTest.available) {
        status.textContent = "🎉 安装成功，工具已就绪！";
        installBtn.textContent = "✅ 已完成";
        toast("工具已就绪", "ok");
        Views.refreshPanels();
      } else {
        status.textContent = "⚠ 安装成功但环境检测未通过，请尝试重启应用。";
        installBtn.textContent = "✅ 已安装";
      }
    };
    body.appendChild(installBtn);
    const testBtn = el("button", { class: "btn ghost", style: "margin-top:6px", text: "🧪 检测环境" });
    testBtn.onclick = () => { mask.remove(); openToolsetTest(ts); };
    body.appendChild(testBtn);
  } else {
    const hasVal = ts.configured_env || [];
    box.appendChild(el("div", { class: "toolcfg-sub muted", text: "填写下列环境变量（留空并保存则移除该配置项）。保存后即时生效并重新检测连通性。" }));
    box.appendChild(el("div", { class: "toolcfg-sub muted", style: "font-size:11px;color:var(--warn);margin-top:4px", text: "⚠ 密钥以明文存储在 config.yaml 中，请确保运行环境安全。" }));
    if (reqs.length > 5) {
      body.appendChild(el("div", { class: "muted small", style: "margin:4px 0 8px 0", text: `共 ${reqs.length} 项配置，填写主要项即可。` }));
    }
    for (const r of reqs) {
      const row = el("label", { class: "toolcfg-row" });
      row.appendChild(el("span", { class: "toolcfg-key", text: r }));
      const inpWrap = el("div", { class: "toolcfg-inp-wrap" });
      const inp = el("input", { type: "password",
        placeholder: hasVal.includes(r) ? "已配置（留空保持不变）" : r });
      if (hasVal.includes(r)) {
        inp.placeholder = "已配置（输入新值覆盖，留空保持不变）";
        inp.dataset.has = "1";
        // 不设置 value="••••••••"——后端不回传明文，塞假值只会让眼睛按钮形同虚设
        // 留空输入框，用户填入新值后眼睛按钮可正常切换明文/密文
      }
      inpWrap.appendChild(inp);
      // 统一按钮：已配置字段点击后从后端取真实值，未配置字段切换明文/密文
      const btn = el("button", { class: "btn icon", type: "button", text: "👁",
        title: "点击切换明文/密文；已配置字段首次点击从后端读取真实值",
        onclick: async (e) => {
          e.preventDefault();
          if (inp.dataset.has && inp.dataset.has !== "0") {
            // 已配置但未显示：从后端获取真实值
            btn.disabled = true; btn.textContent = "…";
            const r = await postJSON("/api/toolsets/env-values", { name: ts.name }).catch(e => ({ ok: false, error: e.message }));
            if (!r.ok || !r.env_values) { btn.disabled = false; btn.textContent = "👁"; return; }
            const key = inp.closest(".toolcfg-row").querySelector(".toolcfg-key").textContent;
            const val = r.env_values[key];
            if (val) {
              inp.value = val;
              inp.dataset.has = "0";  // 已填入真实值，保存时不再跳过
              inp.type = "text";
              btn.textContent = "👁‍🗨";
              btn.title = "已显示真实值，再次点击切换明文/密文";
            } else {
              btn.disabled = false; btn.textContent = "👁";
            }
          } else {
            // 未配置字段 或 已显示真实值：切换明文/密文
            const isPassword = inp.getAttribute("type") === "password";
            inp.setAttribute("type", isPassword ? "text" : "password");
            btn.textContent = isPassword ? "👁‍🗨" : "👁";
          }
        } });
      inpWrap.appendChild(btn);
      row.appendChild(inpWrap);
      body.appendChild(row);
    }
    // browser-cdp 专用：自动检测按钮
    if (ts.name === "browser-cdp") {
      const detectRow = el("div", { style: "margin-top:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;" });
      const detectBtn = el("button", { class: "btn primary", style: "font-size:13px;", text: "🔍 自动检测 Edge CDP 端点" });
      const detectStatus = el("span", { class: "muted small", style: "margin-left:4px;" });
      detectBtn.onclick = async () => {
        detectBtn.disabled = true; detectBtn.textContent = "检测中…"; detectStatus.textContent = "";
        const r = await postJSON("/api/toolsets/browser-cdp/detect", {}).catch(e => ({ ok: false, error: e.message }));
        if (!r.ok) { detectStatus.textContent = "❌ " + (r.error || "检测失败"); detectBtn.disabled = false; detectBtn.textContent = "🔍 重试"; return; }
        if (r.cdp_url) {
          detectStatus.textContent = "✅ " + r.message;
          // 自动填入输入框
          const inp = body.querySelector(".toolcfg-key");
          if (inp && inp.textContent === "BROWSER_CDP_URL") {
            const input = inp.closest(".toolcfg-row").querySelector("input");
            if (input) { input.value = r.cdp_url; input.dataset.has = "0"; }
          }
          detectBtn.textContent = "✅ 已检测";
        } else {
          detectStatus.textContent = "⚠️ " + r.message;
          detectBtn.disabled = false; detectBtn.textContent = "🔍 重试";
        }
      };
      detectRow.appendChild(detectBtn);
      detectRow.appendChild(detectStatus);
      // 操作说明
      const guide = el("div", { class: "muted small", style: "margin-top:8px;padding:8px 10px;background:var(--bg-sunken);border-radius:6px;line-height:1.6;" });
      guide.innerHTML = `
<b>使用步骤：</b><br>
1. 关闭所有 Edge 窗口<br>
2. 按 Win+R，输入以下命令启动 Edge（开启远程调试）：<br>
<code style="background:var(--bg);padding:2px 6px;border-radius:3px;font-size:11px;">
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222
</code><br>
3. 保持 Edge 运行，回到此页面<br>
4. 点击上方「自动检测」按钮，系统会自动发现 CDP 端点并填入
      `;
      body.appendChild(detectRow);
      body.appendChild(guide);
    }
  }
  box.appendChild(body);
  if (reqs.length) {
    const foot = el("div", { class: "toolcfg-foot" });
    const save = el("button", { class: "btn primary", text: "保存并检测" });
    save.onclick = async () => {
      save.disabled = true; save.textContent = "保存中…";
      const values = {};
      Array.from(body.querySelectorAll(".toolcfg-row")).forEach((row) => {
        const key = row.querySelector(".toolcfg-key").textContent;
        const inp = row.querySelector("input");
        const val = inp.value.trim();
        // dataset.has="1" 且留空 → 用户未修改，跳过（后端不回传明文，留空表示保持原值）
        if (inp.dataset.has === "1" && !val) return;
        values[key] = val;
      });
      const r = await postJSON("/api/toolsets/configure", { name: ts.name, values }).catch((e) => ({ ok: false, error: e.message }));
      if (r.ok) { toast("已保存并重新检测", "ok"); mask.remove(); Views.refreshPanels(); }
      else { toast("保存失败：" + (r.error || ""), "err"); save.disabled = false; save.textContent = "保存并检测"; }
    };
    foot.appendChild(save);
    box.appendChild(foot);
  } else {
    const foot = el("div", { class: "toolcfg-foot" });
    const doneBtn = el("button", { class: "btn ghost", text: "✔ 完成" });
    doneBtn.onclick = () => { mask.remove(); Views.refreshPanels(); };
    foot.appendChild(doneBtn);
    const trialBtn = el("button", { class: "btn primary", text: "▶ 试用此工具" });
    trialBtn.onclick = () => { mask.remove(); openToolsetTrial(ts); };
    foot.appendChild(trialBtn);
    box.appendChild(foot);
  }
  let dirty = false;
  body.querySelectorAll("input").forEach(inp => {
    inp.addEventListener("input", () => { dirty = true; });
  });
  function safeClose() {
    if (dirty && !confirm("有未保存的更改，确定关闭？")) return;
    mask.remove();
  }
  mask.appendChild(box);
  document.body.appendChild(mask);
  mask.addEventListener("click", (e) => { if (e.target === mask || e.target.dataset.x) safeClose(); });
}

// ------------------------------------------------------------------ 工具集成：详细诊断测试
export async function openToolsetTest(ts) {
  // 单例：先关闭已打开的同类型对话框，避免多次点击叠加
  document.querySelectorAll(".toolcfg-mask").forEach((m) => m.remove());
  const mask = el("div", { class: "toolcfg-mask" });
  const box = el("div", { class: "toolcfg" });
  box.appendChild(el("div", { class: "toolcfg-head" }, [
    el("b", { text: "测试 " + (ts.label || ts.name) }),
    el("button", { class: "btn icon", text: "×", "data-x": "1" }),
  ]));
  const state = el("div", { class: "toolcfg-sub muted", text: "诊断中…" });
  box.appendChild(state);
  const body = el("div", { class: "toolcfg-body" });
  box.appendChild(body);
  const foot = el("div", { class: "toolcfg-foot" });
  const close = el("button", { class: "btn ghost", text: "关闭", "data-x": "1" });
  foot.appendChild(close);
  box.appendChild(foot);
  mask.appendChild(box);
  document.body.appendChild(mask);
  mask.addEventListener("click", (e) => { if (e.target === mask || e.target.dataset.x) mask.remove(); });

  const r = await postJSON("/api/toolsets/test", { name: ts.name }).catch((e) => ({ ok: false, error: e.message }));
  if (!r.ok) { state.textContent = "测试失败：" + (r.error || ""); return; }
  state.textContent = (r.available ? "✅ 可用" : "❌ " + (r.reason || "未就绪")) + "（" + (ts.label || ts.name) + "）";
  for (const c of r.checks || []) {
    const line = el("div", { class: "trial-line" });
    line.appendChild(el("span", { class: "trial-k", text: c.var }));
    line.appendChild(el("span", { class: "badge " + (c.set ? "on" : "off"), text: c.set ? "已设置" : "未设置" }));
    if (c.value) line.appendChild(el("span", { class: "muted small", style: "margin-left:6px", text: "· " + c.value }));
    body.appendChild(line);
  }
  if (r.detail) body.appendChild(el("div", { class: "trial-detail", text: r.detail }));
  if (!r.available) {
    const installBtn = el("button", { class: "btn primary", text: "🔄 一键安装缺失组件" });
    installBtn.onclick = async () => {
      installBtn.disabled = true; installBtn.textContent = "安装中…";
      const ir = await postJSON("/api/toolsets/install-deps", { name: ts.name }).catch(e => ({ ok: false, error: e.message }));
      if (!ir.ok) {
        state.textContent = "❌ " + (ir.error || "安装失败");
        installBtn.textContent = "🔄 重试"; installBtn.disabled = false;
        return;
      }
      state.textContent = "✅ 安装成功！重新检测…";
      const reTest = await postJSON("/api/toolsets/test", { name: ts.name }).catch(e => ({ ok: false, error: e.message }));
      if (reTest.ok && reTest.available) {
        state.textContent = "🎉 安装成功，工具已就绪！";
        installBtn.textContent = "✅ 已完成";
        Views.refreshPanels();
      } else {
        state.textContent = "⚠ 安装成功，但环境未就绪，请重启应用后重试。";
        installBtn.textContent = "✅ 已安装";
      }
    };
    foot.insertBefore(installBtn, close);
    const go = el("button", { class: "btn ghost", text: "▶ 试用实际调用" });
    go.onclick = () => { mask.remove(); openToolsetTrial(ts); };
    foot.insertBefore(go, close);
  }
}

// ------------------------------------------------------------------ 工具集成：实际试用（SSE）
export function openToolsetTrial(ts) {
  // 单例：先关闭已打开的同类型对话框，避免多次点击叠加
  document.querySelectorAll(".toolcfg-mask").forEach((m) => m.remove());
  const mask = el("div", { class: "toolcfg-mask" });
  const box = el("div", { class: "toolcfg trial-w" });
  box.appendChild(el("div", { class: "toolcfg-head" }, [
    el("b", { text: "试用 " + (ts.label || ts.name) }),
    el("span", { class: "muted small", text: "（超时120s，关闭即停止）" }),
    el("button", { class: "btn icon", text: "×", "data-x": "1" }),
  ]));
  if (ts.dangerous) {
    const warn = el("div", { class: "trial-warn", text: "⚠ 注意：该工具集会实际写入数据（文件/记忆/待办等），试用后请手动清理。" });
    box.appendChild(warn);
  }
  const costWarn = el("div", { class: "trial-warn", style: "border-left-color:var(--accent);margin-top:4px", text: "💸 试用会调用真实 AI 模型，消耗 API 额度。连续试用多个工具集会增加费用。" });
  box.appendChild(costWarn);
  const ta = el("textarea", { class: "trial-input", rows: 2, placeholder: "输入指令后回车，或直接点「自动试用」…" });
  const run = el("button", { class: "btn primary", text: "▶ 自动试用" });
  const send = el("button", { class: "btn ghost", text: "发送" });
  const stop = el("button", { class: "btn ghost", text: "■ 停止", style: "display:none" });
  const bar = el("div", { class: "trial-bar" }, [ta, run, send, stop]);
  const log = el("div", { class: "trial-log" });
  box.appendChild(bar);
  box.appendChild(log);
  mask.appendChild(box);
  document.body.appendChild(mask);

  let streaming = false;
  let abortController = null;

  function closeTrial() {
    if (abortController) { abortController.abort(); abortController = null; }
    mask.remove();
  }
  mask.addEventListener("click", (e) => { if (e.target === mask || e.target.dataset.x) closeTrial(); });

  async function runTrial(text) {
    if (streaming) return;
    streaming = true;
    abortController = new AbortController();
    run.disabled = send.disabled = true;
    stop.style.display = "";
    log.innerHTML = "";
    const line = el("div", { class: "trial-line muted", text: "▸ " + (text || "（自动试用）") });
    log.appendChild(line);
    const out = el("div", { class: "trial-out" });
    log.appendChild(out);
    let acc = "";
    const toolCalls = {};
    const timeoutId = setTimeout(() => {
      if (abortController) { abortController.abort(); abortController = null; }
      out.appendChild(el("div", { class: "muted", text: "⚠ 超时（120s），已自动终止" }));
    }, 120000);
    try {
      const resp = await fetch("/api/toolsets/trial", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: ts.name, text, timeout: 120, confirmed: ts.dangerous }),
        signal: abortController.signal,
      });
      if (!resp.ok) { const e = await resp.json().catch(() => ({})); throw new Error(e.error || "HTTP " + resp.status); }
      const reader = resp.body.getReader(); const dec = new TextDecoder(); let buf = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const { events, rest } = parseSSE(buf);
        buf = rest;
        for (const obj of events) {
          if (obj.type === "reasoning") { if (!toolCalls._th) { toolCalls._th = el("div", { class: "trial-th" }); log.appendChild(toolCalls._th); } toolCalls._th.textContent = "💭 " + (toolCalls._th.textContent.replace(/^💭 /, "") || "") + (obj.text || ""); }
          else if (obj.type === "action") { const t = el("div", { class: "trial-tool" }); t.textContent = "🔧 调用工具：" + (obj.tool || "") + (obj.preview ? " ｜ " + obj.preview : ""); t.dataset.tool = obj.tool; log.appendChild(t); toolCalls[obj.tool] = t; }
          else if (obj.type === "action_result") { const t = toolCalls[obj.tool] || el("div", { class: "trial-tool" }); t.textContent = (t.textContent || "") + "\n   ✅ 返回：" + (typeof obj.result === "string" ? obj.result.slice(0, 400) : JSON.stringify(obj.result).slice(0, 400)); log.appendChild(t); }
          else if (obj.choices && obj.choices[0] && obj.choices[0].delta) { acc += obj.choices[0].delta.content || ""; out.textContent = acc; }
          else if (obj.type === "done" && obj.final != null) { out.textContent = obj.final; }
          else if (obj.type === "error") { out.appendChild(el("div", { class: "muted", text: "⚠ " + (obj.message || "错误") })); }
        }
      }
      if (!acc) out.appendChild(el("div", { class: "muted", text: "（未产生文本输出）" }));
    } catch (e) {
      if (e.name === "AbortError") { out.appendChild(el("div", { class: "muted", text: "（已手动停止）" })); }
      else { out.appendChild(el("div", { class: "muted", text: "⚠ " + e.message })); }
    }
    finally {
      clearTimeout(timeoutId);
      streaming = false; abortController = null;
      run.disabled = send.disabled = false;
      stop.style.display = "none";
    }
  }
  stop.onclick = () => { if (abortController) { abortController.abort(); abortController = null; } };
  run.onclick = () => runTrial("");
  send.onclick = () => { const v = ta.value.trim(); if (v) runTrial(v); };
  ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send.onclick(); } });
}
