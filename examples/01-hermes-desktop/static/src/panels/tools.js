// @ts-check
/* =====================================================================
 * tools.js — tools 面板子模块
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { State } from "../state.js";
import { getJSON, postJSON, delJSON, parseSSE } from "../api.js";
import * as Views from "../views.js";
import * as Chat from "../chat.js";
import { renderToolsCatalogPanel } from "./toolscatalog.js";
// ------------------------------------------------------------------ 工具集成面板（统一工具面板的「工具管理」子面板）
export async function renderToolsManagePanel(body) {
  let data;
  try { data = await getJSON("/api/toolsets"); }
  catch (e) { body.appendChild(el("div", { class: "muted", text: "工具矩阵不可用：" + e.message })); return; }
  if (!data.ok) {
    body.appendChild(el("div", { class: "muted", text: "工具矩阵不可用：" + (data.hint || data.error || "") }));
    return;
  }
  const wrap = el("div", { class: "panel" });
  wrap.appendChild(el("div", { class: "muted", text: `架构默认禁用：${(data.disabled_toolsets || []).join(", ") || "无"}；自动化工具集：${(data.automation || []).join(", ") || "无"}` }));

  if (window._toolSearchQuery === undefined) window._toolSearchQuery = "";
  const searchRow = el("div", { class: "tool-search-row" });
  const searchInput = el("input", { class: "form-input", placeholder: "🔍 搜索工具集名称/用途…",
    value: window._toolSearchQuery || "",
    oninput: () => { window._toolSearchQuery = searchInput.value; applyFilter(); } });
  const sortSelect = el("select", { class: "tool-sort",
    onchange: () => { window._toolSortQuery = sortSelect.value; sortList(sortSelect.value); } });
  if (window._toolSortQuery) sortSelect.value = window._toolSortQuery;
  sortSelect.appendChild(el("option", { value: "name", text: "名称↑" }));
  sortSelect.appendChild(el("option", { value: "name_desc", text: "名称↓" }));
  sortSelect.appendChild(el("option", { value: "state", text: "状态↑" }));
  sortSelect.appendChild(el("option", { value: "state_desc", text: "状态↓" }));
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
  searchRow.appendChild(searchInput);
  searchRow.appendChild(sortSelect);
  const testAll = el("button", { class: "btn ghost sm", text: "🔍 全部检测", onclick: async () => {
    testAll.disabled = true; testAll.textContent = "检测中…";
    const r = await postJSON("/api/toolsets/test-all", {}).catch(e => ({ ok: false, error: e.message }));
    if (r.ok) {
      const avail = Object.values(r.results).filter(v => v.available).length;
      toast(`全部检测完成：${avail}/${r.total} 可用`, "ok");
      Views.refreshPanels();
    } else { toast("检测失败：" + (r.error || ""), "err"); testAll.disabled = false; testAll.textContent = "🔍 全部检测"; }
  } });
  searchRow.appendChild(testAll);
  searchRow.appendChild(batchAll);
  searchRow.appendChild(batchNone);
  wrap.appendChild(searchRow);

  const items = data.items || [];
  const list = el("div", { class: "card-list" });

  function applyFilter() {
    const q = searchInput.value.trim().toLowerCase();
    for (const row of list.children) {
      const txt = (row.dataset.search || "").toLowerCase();
      row.style.display = (!q || txt.includes(q)) ? "" : "none";
    }
  }
  function sortList(mode) {
    const rows = Array.from(list.children);
    rows.sort((a, b) => {
      const an = a.dataset.name || "";
      const bn = b.dataset.name || "";
      const as = a.dataset.state || "";
      const bs = b.dataset.state || "";
      if (mode === "name") return an.localeCompare(bn);
      if (mode === "name_desc") return bn.localeCompare(an);
      if (mode === "state") return as.localeCompare(bs);
      if (mode === "state_desc") return bs.localeCompare(as);
      return 0;
    });
    rows.forEach(r => list.appendChild(r));
  }

  for (const ts of items) {
    const archDisabled = !!ts.arch_disabled;
    const nonInteractive = archDisabled;
    let stateLabel = "";
    let stateClass = "";
    if (archDisabled) { stateLabel = "禁用"; stateClass = "off"; }
    else if (ts.disabled) { stateLabel = "已禁用"; stateClass = "off"; }
    else if (ts.available && ts.configured) { stateLabel = "已配置"; stateClass = "on"; }
    else if (ts.available && !ts.configured) { stateLabel = "部分配置"; stateClass = "warn"; }
    else { stateLabel = "未就绪"; stateClass = "warn"; }

    const sw = el("label", { class: "switch" + (nonInteractive ? " muted" : "") }, [
      el("input", { type: "checkbox", ...(ts.enabled ? { checked: "checked" } : {}),
        ...(nonInteractive ? { disabled: "disabled" } : {}),
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
              const badge = card.querySelector(".badge:not(.cat)");
              if (badge) {
                const arch = !!ts.arch_disabled;
                let lbl, cls;
                if (arch) { lbl = "禁用"; cls = "off"; }
                else if (ts.disabled) { lbl = "已禁用"; cls = "off"; }
                else if (ts.available && ts.configured) { lbl = "已配置"; cls = "on"; }
                else if (ts.available && !ts.configured) { lbl = "部分配置"; cls = "warn"; }
                else { lbl = "未就绪"; cls = "warn"; }
                badge.textContent = lbl;
                badge.className = "badge " + cls;
              }
              card.dataset.state = lbl;
            }
          }
        } }),
      el("span", { class: "slider" }),
    ]);
    const title = el("div", { class: "cr-title" }, [
      el("span", { text: ts.label || ts.name }),
      ts.category ? el("span", { class: "badge cat", style: "font-weight:400;font-size:10px;margin-left:6px", text: ts.category }) : null,
      el("span", { class: "badge " + stateClass, text: stateLabel }),
      el("div", { class: "cr-actions" }, [
        !ts.arch_disabled ? el("button", { class: "btn ghost sm", text: "⚙ 配置", onclick: () => openToolsetConfig(ts) }) : null,
        !ts.arch_disabled ? el("button", { class: "btn ghost sm", text: "🧪 测试", onclick: () => openToolsetTest(ts) }) : null,
        !ts.arch_disabled ? el("button", { class: "btn ghost sm", text: "▶ 试用", onclick: () => openToolsetTrial(ts) }) : null,
      ]),
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
    function relTime(tsSec) {
      const sec = Math.floor((Date.now() / 1000) - tsSec);
      if (sec < 60) return "刚刚";
      if (sec < 3600) return Math.floor(sec / 60) + "分钟前";
      if (sec < 86400) return Math.floor(sec / 3600) + "小时前";
      return Math.floor(sec / 86400) + "天前";
    }
    if (ts.last_test) {
      const lt = ts.last_test;
      const testBadge = lt.available ? "✅" : "❌";
      desc.appendChild(el("div", { class: "muted small", text: `测试 ${relTime(lt.ts)}：${testBadge} ${lt.reason || (lt.available ? "正常" : "异常")}` }));
    }

    const row = el("div", { class: "card-row" }, [
      el("div", { class: "cr-main" }, [title, desc]),
      sw,
    ]);
    row.dataset.search = (ts.label || ts.name) + " " + (ts.purpose || "") + " " + (ts.reason || "");
    row.dataset.name = ts.label || ts.name;
    row.dataset.toolset = ts.name;
    row.dataset.state = stateLabel;
    list.appendChild(row);
  }
  wrap.appendChild(list);
  body.appendChild(wrap);
}

// ------------------------------------------------------------------ 统一工具面板：工具清单（只读）+ 工具管理（可操作）
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

  // 默认渲染两个子面板（清单只读、管理可操作）
  try { await renderToolsCatalogPanel(catalogSub); } catch (e) { catalogSub.appendChild(el("div", { class: "muted", text: "工具清单加载失败：" + e.message })); }
  try { await renderToolsManagePanel(manageSub); } catch (e) { manageSub.appendChild(el("div", { class: "muted", text: "工具管理加载失败：" + e.message })); }

  function switchTab(which) {
    const isCat = which === "catalog";
    tabCatalog.classList.toggle("active", isCat);
    tabManage.classList.toggle("active", !isCat);
    catalogSub.classList.toggle("hidden", !isCat);
    manageSub.classList.toggle("hidden", isCat);
  }
  tabCatalog.addEventListener("click", () => switchTab("catalog"));
  tabManage.addEventListener("click", () => switchTab("manage"));
  window.__showToolsTab = (which) => switchTab(which || "catalog");

  // 工具清单 → 工具管理「一键直达」：清单中点击工具集跳转到管理子面板对应位置
  window.__gotoToolsManage = (toolsetName) => {
    switchTab("manage");
    if (!toolsetName) return;
    setTimeout(() => {
      const panel = document.getElementById("view-tools");
      if (!panel) return;
      let target = null;
      try { target = panel.querySelector('.card-row[data-toolset="' + (window.CSS && CSS.escape ? CSS.escape(toolsetName) : toolsetName) + '"]'); } catch (_) { target = null; }
      if (!target) {
        // 兜底：按名称包含匹配
        const rows = panel.querySelectorAll(".card-row");
        for (const r of rows) { if ((r.dataset.name || "").toLowerCase().includes(String(toolsetName).toLowerCase())) { target = r; break; } }
      }
      if (!target) { toast("该工具集不可在「工具管理」中配置", "info"); return; }
      try { target.scrollIntoView({ block: "center", behavior: "smooth" }); } catch (_) {}
      target.classList.add("highlight-flash");
      setTimeout(() => { try { target.classList.remove("highlight-flash"); } catch (_) {} }, 1600);
    }, 360);
  };
}

// ------------------------------------------------------------------ 工具集成：配置弹窗
export function openToolsetConfig(ts) {
  const reqs = ts.requirements || [];
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

