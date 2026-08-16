// @ts-check
/* =====================================================================
 * loops.js — loops 面板子模块
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { State } from "../state.js";
import { getJSON, postJSON, delJSON, parseSSE } from "../api.js";
import * as Views from "../views.js";
// ------------------------------------------------------------------ 循环面板
let _loopRunHistory = []; // 运行历史 [{id, name, status, result, error, finished_at}]

export async function renderLoopsPanel(body) {
  const data = await getJSON("/api/loops");
  const wrap = el("div", { class: "panel" });
  const sum = data.summary || {};
  const flags = data.flags || {};
  const mi = data.max_iterations ?? 90;

  // ── 状态概览 ──
  const builtins = data.builtins || [];
  const customs = data.custom || [];
  const runnableCount = builtins.filter(b => b.runnable === true).length;
  const switchCount = builtins.filter(b => b.status === "switch").length;
  const runningCount = _loopRunHistory.filter(r => r.status === "running").length;
  const doneCount = _loopRunHistory.filter(r => r.status === "done").length;
  const errCount = _loopRunHistory.filter(r => r.status === "error").length;

  const stats = el("div", { class: "loop-stats" }, [
    el("span", { class: "loop-stat-item", text: `🔄 内置 ${builtins.length} 个（开关 ${switchCount} · 可运行 ${runnableCount}）` }),
    el("span", { class: "loop-stat-item", text: `📋 自定义 ${customs.length} 个` }),
    runningCount > 0 ? el("span", { class: "loop-stat-item loop-stat-running", text: `🟢 运行中 ${runningCount}` }) : null,
    doneCount > 0 ? el("span", { class: "loop-stat-item loop-stat-done", text: `✅ 已完成 ${doneCount}` }) : null,
    errCount > 0 ? el("span", { class: "loop-stat-item loop-stat-err", text: `❌ 失败 ${errCount}` }) : null,
  ].filter(Boolean));
  wrap.appendChild(stats);

  // 搜索框
  let _loopFilter = "";
  const loopSearch = el("input", { class: "form-input", style: "margin-bottom:10px;", placeholder: "搜索循环名称/描述…",
    oninput: () => { _loopFilter = loopSearch.value.trim().toLowerCase(); applyLoopFilter(); } });
  wrap.appendChild(loopSearch);
  function applyLoopFilter() {
    for (const section of wrap.querySelectorAll(".loop-section")) {
      const cards = section.querySelectorAll(".card-row");
      let secVisible = false;
      for (const card of cards) {
        const txt = (card.dataset.search || "").toLowerCase();
        const match = !_loopFilter || txt.includes(_loopFilter);
        card.style.display = match ? "" : "none";
        if (match) secVisible = true;
      }
      section.style.display = secVisible ? "" : "none";
    }
    // 无结果提示
    let noResult = wrap.querySelector(".loop-no-result");
    const hasVisible = wrap.querySelectorAll('.loop-section .card-row[style*="display"]:not([style*="display: none"])').length > 0
      || !_loopFilter;
    if (!hasVisible && _loopFilter) {
      if (!noResult) {
        noResult = el("div", { class: "muted loop-no-result", style: "padding:14px;text-align:center;", text: "未找到匹配的循环" });
        wrap.appendChild(noResult);
      }
      noResult.style.display = "";
    } else if (noResult) {
      noResult.style.display = "none";
    }
  }

  // ── 全局设置 ──
  wrap.appendChild(el("div", { class: "section-title", text: "全局设置" }));
  const setCard = el("div", { class: "panel", style: "margin-bottom:14px;" });

  const miRow = el("div", { class: "field-inline" }, [
    el("label", { text: "最大迭代次数" }),
    el("input", { type: "number", min: 1, max: 200, value: mi,
      style: "width:80px;", id: "loopMaxIters" }),
    el("span", { class: "muted small", text: "（1-200，单轮对话中模型最多可连续调用工具的次数）" }),
  ]);
  setCard.appendChild(miRow);

  // 从后端动态获取可编辑参数（不再硬编码 memory_enabled/goal_enabled）
  const editableParams = [];
  for (const b of builtins) {
    if (!b.params) continue;
    for (const p of b.params) {
      if (p.editable && p.key && !editableParams.find(ep => ep.key === p.key)) {
        editableParams.push({ ...p, builtinName: b.name });
      }
    }
  }
  for (const param of editableParams) {
    const isOn = param.value === true || param.value === "true";
    const sw = el("label", { class: "switch" }, [
      el("input", { type: "checkbox", ...(isOn ? { checked: "checked" } : {}),
        onchange: async (ev) => {
          const r = await postJSON("/api/loops/settings", { [param.key]: ev.target.checked }).catch((e) => ({ ok: false, error: e.message }));
          if (r.ok) toast(param.label + "已" + (ev.target.checked ? "启用" : "关闭") + "，新会话生效", "ok");
          else toast("保存失败：" + (r.error || ""), "err");
        } }),
      el("span", { class: "slider" }),
    ]);
    setCard.appendChild(el("div", { class: "field-inline" }, [
      el("span", { text: param.builtinName + "：" + param.label }),
      sw,
      el("span", { class: "muted small", text: "（新会话生效）" }),
    ]));
  }

  const saveBtn = el("button", { class: "btn primary", text: "保存设置", onclick: async () => {
    const v = parseInt($("#loopMaxIters").value, 10) || 90;
    const r = await postJSON("/api/loops/settings", { max_iterations: v }).catch((e) => ({ ok: false, error: e.message }));
    if (r.ok) toast("已保存，新会话生效", "ok"); else toast("保存失败：" + (r.error || ""), "err");
  } });
  setCard.appendChild(el("div", { class: "actions-row", style: "margin-top:8px;" }, [saveBtn]));
  wrap.appendChild(setCard);

  // ── 运行历史（折叠） ──
  if (_loopRunHistory.length > 0) {
    const historySection = el("div", { class: "loop-history" });
    const histTitle = el("div", { class: "loop-history-title", onclick: () => {
      const body = historySection.querySelector(".loop-history-body");
      const arrow = histTitle.querySelector(".loop-arrow");
      if (body) {
        body.classList.toggle("collapsed");
        if (arrow) arrow.textContent = body.classList.contains("collapsed") ? "▶" : "▼";
      }
    }}, [
      el("span", { class: "loop-arrow", text: "▼" }),
      el("span", { text: "运行历史" }),
      el("span", { class: "badge", text: _loopRunHistory.length + " 条" }),
    ]);
    historySection.appendChild(histTitle);

    const histBody = el("div", { class: "loop-history-body" });
    // 从新到旧显示
    const reversed = [..._loopRunHistory].reverse();
    for (const h of reversed) {
      const statusIcon = h.status === "done" ? "✅" : h.status === "error" ? "❌" : "⏳";
      const statusClass = h.status === "done" ? "loop-h-done" : h.status === "error" ? "loop-h-err" : "loop-h-running";
      const card = el("div", { class: "loop-h-card " + statusClass }, [
        el("div", { class: "loop-h-head" }, [
          el("span", { class: "loop-h-icon", text: statusIcon }),
          el("span", { class: "loop-h-name", text: h.name }),
          el("span", { class: "badge", text: h.status }),
          h.finished_at ? el("span", { class: "muted small", text: h.finished_at }) : null,
        ]),
        h.result ? el("pre", { class: "loop-h-result", text: h.result }) : null,
        h.error ? el("pre", { class: "loop-h-result loop-h-err-text", text: h.error }) : null,
      ]);
      histBody.appendChild(card);
    }
    historySection.appendChild(histBody);
    wrap.appendChild(historySection);
  }

  // ── 运行结果回调 ──
  let _pollTimers = [];

  function showRunResult(runId, loopName) {
    // 添加"运行中"记录到历史
    _loopRunHistory.push({ id: runId, name: loopName, status: "running", result: "", error: "", finished_at: "" });
    // 重新渲染（刷新运行历史区域）
    Views.refreshPanels();

    // 轮询（最多 120 次 = 3 分钟）
    let pollCount = 0;
    const MAX_POLL = 120;
    const poll = setInterval(async () => {
      pollCount++;
      if (pollCount > MAX_POLL) {
        clearInterval(poll);
        // 更新历史状态为超时
        const entry = _loopRunHistory.find(h => h.id === runId);
        if (entry && entry.status === "running") {
          entry.status = "error";
          entry.error = "超时未完成";
          Views.refreshPanels();
        }
        return;
      }
      const r = await getJSON("/api/loops/run/" + runId).catch(() => null);
      if (!r || !r.ok || !r.run) return;
      const ru = r.run;
      if (ru.status === "running") return;
      clearInterval(poll);
      // 更新历史记录
      const entry = _loopRunHistory.find(h => h.id === runId);
      if (entry) {
        entry.status = ru.status === "done" ? "done" : "error";
        entry.result = ru.result || "";
        entry.error = ru.error || "";
        entry.finished_at = ru.finished_at || "";
        Views.refreshPanels();
      }
    }, 1500);
    _pollTimers.push(poll);
  }

  // 清理旧轮询
  wrap._cleanup = () => {
    for (const t of _pollTimers) { clearInterval(t); }
    _pollTimers = [];
  };

  // ── 内置循环 ──
  const switchLoops = builtins.filter(b => b.status === "switch");
  const runnableLoops = builtins.filter(b => b.runnable === true);
  const otherLoops = builtins.filter(b => b.status !== "switch" && b.runnable !== true);

  if (switchLoops.length > 0) {
    wrap.appendChild(el("div", { class: "section-title loop-section", text: "开关型循环" }));
    const slist = el("div", { class: "card-list" });
    for (const b of switchLoops) {
      slist.appendChild(renderLoopCard(b, showRunResult));
    }
    wrap.appendChild(slist);
  }

  if (runnableLoops.length > 0) {
    wrap.appendChild(el("div", { class: "section-title loop-section", text: "可运行循环" }));
    const rlist = el("div", { class: "card-list" });
    for (const b of runnableLoops) {
      rlist.appendChild(renderLoopCard(b, showRunResult));
    }
    wrap.appendChild(rlist);
  }

  if (otherLoops.length > 0) {
    wrap.appendChild(el("div", { class: "section-title loop-section", text: "其他循环" }));
    const olist = el("div", { class: "card-list" });
    for (const b of otherLoops) {
      olist.appendChild(renderLoopCard(b, showRunResult));
    }
    wrap.appendChild(olist);
  }

  // ── 自定义循环 ──
  wrap.appendChild(el("div", { class: "section-title loop-section", text: "自定义循环" }));
  const clist = el("div", { class: "card-list" });
  for (const c of customs) {
    clist.appendChild(renderCustomLoopCard(c, showRunResult));
  }
  if (!customs.length) {
    clist.appendChild(el("div", { class: "muted", style: "padding:12px;text-align:center;", text: "暂无自定义循环" }));
  }
  wrap.appendChild(clist);

  // ── 新增自定义循环 ──
  wrap.appendChild(el("div", { class: "section-title", text: "新增自定义循环" }));
  const form = createLoopForm(null, () => { Views.refreshPanels(); });
  wrap.appendChild(form);

  body.appendChild(wrap);
}

// 渲染单个循环卡片
function renderLoopCard(b, showRunResult) {
  const statusBadge = b.status_label || b.status;
  const statusClass = b.status === "active" ? "on" : b.status === "switch" ? "warn" : "";
  const card = el("div", { class: "card-row", "data-search": (b.name || "") + " " + (b.desc || "") }, [
    el("div", { class: "cr-main" }, [
      el("div", { class: "cr-title" }, [
        el("span", { text: b.name }),
        el("span", { class: "badge " + statusClass, text: statusBadge }),
        b.scale ? el("span", { class: "badge", text: b.scale }) : null,
      ]),
      b.desc ? el("div", { class: "cr-desc", text: b.desc }) : null,
      b.steps && b.steps.length ? el("ul", { class: "loop-steps" }, b.steps.map((s) => el("li", { text: s }))) : null,
      b.runnable === true ? el("button", { class: "btn ghost", text: "▶ 运行", style: "margin-top:8px;align-self:flex-start;",
        onclick: async () => {
          const r = await postJSON("/api/loops/run/" + encodeURIComponent(b.id), {}).catch((e) => ({ ok: false, error: e.message }));
          if (r.ok && r.run && r.run.run_id) showRunResult(r.run.run_id, b.name);
          else toast("启动失败：" + (r.error || ""), "err");
        } }) : null,
    ]),
  ]);
  return card;
}

// 渲染自定义循环卡片（含编辑/删除/运行）
function renderCustomLoopCard(c, showRunResult) {
  const card = el("div", { class: "card-row" }, [
    el("div", { class: "cr-main" }, [
      el("div", { class: "cr-title" }, [
        el("span", { text: c.name }),
        el("span", { class: "badge", text: "max " + (c.max_iterations || 30) }),
      ]),
      c.prompt ? el("div", { class: "cr-desc", text: c.prompt }) : null,
    ]),
    el("div", { style: "display:flex;gap:6px;flex-direction:column;align-items:flex-end;" }, [
      el("button", { class: "btn ghost", text: "▶ 运行", onclick: async () => {
        const r = await postJSON("/api/loops/run/" + encodeURIComponent(c.id), {}).catch((e) => ({ ok: false, error: e.message }));
        if (r.ok && r.run && r.run.run_id) showRunResult(r.run.run_id, c.name);
        else toast("启动失败：" + (r.error || ""), "err");
      } }),
      el("button", { class: "btn sm", text: "编辑", onclick: () => openEditLoopForm(c) }),
      el("button", { class: "btn ghost", text: "删除", onclick: async () => {
        if (!confirm("删除循环 " + c.name + "？")) return;
        await delJSON("/api/loops/custom/" + encodeURIComponent(c.id)).catch(() => {});
        Views.refreshPanels();
      } }),
    ]),
  ]);
  return card;
}

// 创建自定义循环表单（新建/编辑共用）
function createLoopForm(editData, onSaved) {
  const isEdit = editData !== null;
  const form = el("div", { class: "panel" });
  const cn = el("input", { placeholder: "循环名（必填）", value: editData ? editData.name : "" });
  const cp = el("textarea", { placeholder: "目标提示词（prompt）", value: editData ? (editData.prompt || "") : "" });
  const cmi = el("input", { type: "number", min: 1, max: 500, placeholder: "最大迭代（默认 30）", value: editData ? (editData.max_iterations || 30) : "30" });
  const errMsg = el("div", { class: "muted", style: "color:var(--danger);display:none;margin-bottom:8px;" });

  form.appendChild(el("div", { class: "field" }, [el("label", { text: "名称" }), cn]));
  form.appendChild(el("div", { class: "field" }, [el("label", { text: "目标" }), cp]));
  form.appendChild(el("div", { class: "field" }, [el("label", { text: "迭代" }), cmi]));
  form.appendChild(errMsg);

  const btnText = isEdit ? "保存修改" : "保存循环";
  const btn = el("button", { class: "btn primary", text: btnText, onclick: async () => {
    errMsg.style.display = "none";
    if (!cn.value.trim()) {
      errMsg.textContent = "请填写循环名";
      errMsg.style.display = "";
      cn.focus();
      return;
    }
    if (!cp.value.trim()) {
      errMsg.textContent = "请填写目标提示词";
      errMsg.style.display = "";
      cp.focus();
      return;
    }
    const body = {
      name: cn.value.trim(),
      prompt: cp.value.trim(),
      max_iterations: parseInt(cmi.value || "30", 10),
    };
    let r;
    if (isEdit) {
      r = await fetch("/api/loops/custom/" + encodeURIComponent(editData.id), {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(res => res.json()).catch(e => ({ ok: false, error: e.message }));
    } else {
      r = await postJSON("/api/loops/custom", body).catch(e => ({ ok: false, error: e.message }));
    }
    if (r.ok) {
      toast(isEdit ? "已修改" : "已保存", "ok");
      // 清空表单
      if (!isEdit) { cn.value = ""; cp.value = ""; cmi.value = "30"; }
      if (onSaved) onSaved();
    } else {
      toast("保存失败：" + (r.error || ""), "err");
    }
  } });
  form.appendChild(el("div", { class: "actions-row", style: "margin-top:8px;" }, [btn]));
  return form;
}

// 编辑弹窗
function openEditLoopForm(c) {
  const overlay = el("div", { class: "ss-edit-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });
  const modal = el("div", { class: "ss-edit-modal" });
  modal.appendChild(el("h3", { text: "编辑循环：" + c.name }));
  const form = createLoopForm(c, () => { overlay.remove(); Views.refreshPanels(); });
  modal.appendChild(form);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}
