// @ts-check
/* =====================================================================
 * cron.js — cron 面板子模块
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { State } from "../state.js";
import { getJSON, postJSON, delJSON, parseSSE } from "../api.js";
import * as Views from "../views.js";
let _cronActiveTab = "tasks";

export async function renderCronPanel(body) {
  const data = await getJSON("/api/cron");
  const jobs = data.items || [];
  const execData = await getJSON("/api/cron/executions").catch(() => ({ items: [] }));
  const execs = execData.items || [];
  const wrap = el("div", { class: "panel" });

  // 统计信息
  const activeCount = jobs.filter(j => j.status === "active").length;
  const maxJobs = 5;
  wrap.appendChild(el("div", { class: "cron-stats" }, [
    el("span", { class: "cron-stat-item", text: "\u23f0 \u5b9a\u65f6\u4efb\u52a1" }),
    el("span", { class: "cron-stat-item", text: `\u2705 \u5df2\u542f\u7528 ${activeCount}/${maxJobs}` }),
    el("span", { class: "cron-stat-item muted small", text: "\u5728\u672c\u5730\u6309\u8ba1\u5212\u81ea\u52a8\u6267\u884c\u534f\u4f5c\u4efb\u52a1\uff0c\u5e76\u67e5\u770b\u8fd0\u884c\u8bb0\u5f55" }),
  ]));

  // 标签页
  const tabBar = el("div", { class: "cron-tabs" }, [
    el("button", { class: "cron-tab" + (_cronActiveTab === "tasks" ? " active" : ""), text: "\u5b9a\u65f6\u4efb\u52a1",
      onclick: () => { _cronActiveTab = "tasks"; Views.refreshPanels(); } }),
    el("button", { class: "cron-tab" + (_cronActiveTab === "history" ? " active" : ""), text: "\u6267\u884c\u8bb0\u5f55",
      onclick: () => { _cronActiveTab = "history"; Views.refreshPanels(); } }),
  ]);
  wrap.appendChild(tabBar);

  if (_cronActiveTab === "tasks") {
    renderTasksTab(wrap, jobs, activeCount, maxJobs);
  } else {
    renderHistoryTab(wrap, execs);
  }

  body.appendChild(wrap);
}

let _cronSelected = new Set();
let _cronBatchMode = false;

function renderTasksTab(wrap, jobs, activeCount, maxJobs) {
  if (jobs.length === 0) {
    renderEmptyState(wrap, activeCount, maxJobs);
    return;
  }

  // 批操作栏
  const batchBar = el("div", { class: "cron-batch-bar" });
  const batchCount = el("span", { class: "batch-count", text: "0" });
  batchBar.appendChild(el("span", { text: "\u5df2\u9009\u62e9 " }));
  batchBar.appendChild(batchCount);
  batchBar.appendChild(el("span", { text: " \u4e2a\u4efb\u52a1" }));
  const batchToggle = el("button", { class: "btn ghost", text: "\u6279\u91cf\u542f\u7528",
    onclick: async () => { await batchCronAction("active"); } });
  const batchPause = el("button", { class: "btn ghost", text: "\u6279\u91cf\u6682\u505c",
    onclick: async () => { await batchCronAction("paused"); } });
  const batchDel = el("button", { class: "btn ghost", style: "color:var(--danger);", text: "\u6279\u91cf\u5220\u9664",
    onclick: async () => { await batchCronAction("delete"); } });
  batchBar.appendChild(batchToggle);
  batchBar.appendChild(batchPause);
  batchBar.appendChild(batchDel);
  wrap.appendChild(batchBar);

  // 搜索框
  const cronSearch = el("input", { class: "form-input", style: "margin-bottom:8px;", placeholder: "搜索任务名称/描述…",
    oninput: () => { applyCronFilter(cronSearch.value.trim().toLowerCase()); } });
  wrap.appendChild(cronSearch);
  function applyCronFilter(q) {
    for (const card of wrap.querySelectorAll(".cron-task-card")) {
      const txt = (card.dataset.search || "").toLowerCase();
      card.style.display = !q || txt.includes(q) ? "" : "none";
    }
    let noResult = wrap.querySelector(".cron-no-result");
    const visible = wrap.querySelectorAll('.cron-task-card[style*="display"]:not([style*="display: none"])').length > 0
      || !q;
    if (!visible && q) {
      if (!noResult) {
        noResult = el("div", { class: "muted cron-no-result", style: "padding:14px;text-align:center;", text: "未找到匹配的定时任务" });
        wrap.appendChild(noResult);
      }
      noResult.style.display = "";
    } else if (noResult) {
      noResult.style.display = "none";
    }
  }

  // 全选复选框
  const selectAllWrap = el("div", { style: "display:flex;align-items:center;gap:8px;margin-bottom:8px;" });
  const selectAllCb = el("input", { type: "checkbox", class: "cron-cb", title: "\u5168\u9009" });
  selectAllCb.onclick = () => {
    const checked = selectAllCb.checked;
    _cronSelected.clear();
    if (checked) jobs.forEach(j => _cronSelected.add(j.id));
    updateBatchBar(batchBar, batchCount);
    document.querySelectorAll(".cron-task-card").forEach(c => c.classList.toggle("selected", checked));
  };
  selectAllWrap.appendChild(selectAllCb);
  selectAllWrap.appendChild(el("span", { class: "muted small", text: "\u5168\u9009 / \u53d6\u6d88\u5168\u9009" }));
  wrap.appendChild(selectAllWrap);

  // 任务列表
  const list = el("div", { class: "card-list", style: "display:flex;flex-direction:column;gap:8px;" });
  for (const j of jobs) {
    const isActive = j.status === "active";
    const isDone = j.status === "done" || j.job_type === "once" && j.last_status === "success";
    const isArchived = j.status === "archived";

    // 运行信息
    const runInfo = [];
    if (j.last_run_at) runInfo.push("\u4e0a\u6b21\uff1a" + new Date(j.last_run_at).toLocaleString());
    else runInfo.push("\u672a\u6267\u884c");
    if (j.last_status) {
      const st = j.last_status === "success" ? "\u6210\u529f" : (j.last_status === "error" ? "\u5931\u8d25" : (j.last_status || "\u8fd0\u884c\u4e2d"));
      runInfo.push("\u7ed3\u679c\uff1a" + st);
    }
    if (j.next_run_at && isActive) runInfo.push("\u4e0b\u6b21\uff1a" + new Date(j.next_run_at).toLocaleString());
    else if (isActive && !j.next_run_at) runInfo.push("\u4e0b\u6b21\uff1a\u5f85\u8ba1\u7b97");

    const card = el("div", { class: "cron-task-card" + (isDone ? " cron-tc-done" : "") + (isArchived ? " cron-tc-done" : ""), "data-search": (j.name || "") + " " + (j.prompt || "") + " " + (j.schedule || "") });

    // 复选框
    const cb = el("input", { type: "checkbox", class: "cron-cb" });
    cb.onclick = () => {
      if (cb.checked) _cronSelected.add(j.id); else _cronSelected.delete(j.id);
      card.classList.toggle("selected", cb.checked);
      updateBatchBar(batchBar, batchCount);
    };
    card.appendChild(cb);

    // 主体
    const body = el("div", { class: "cron-tc-body" });
    const top = el("div", { class: "cron-tc-top" });
    top.appendChild(el("span", { class: "cron-tc-name", text: (j.name || j.id) + (isDone ? " (\u5df2\u5b8c\u6210)" : "") }));
    top.appendChild(el("span", { class: "cron-tc-sched", text: j.schedule || "" }));

    // 开关（toggle switch）
    const toggleLabel = el("label", { class: "cron-toggle" });
    const toggleInput = el("input", { type: "checkbox" });
    toggleInput.checked = isActive;
    toggleInput.onchange = async () => {
      const newStatus = toggleInput.checked ? "active" : "paused";
      await postJSON("/api/cron/" + encodeURIComponent(j.id) + "/status", { status: newStatus }).catch(() => {});
      toast(newStatus === "active" ? "\u5df2\u542f\u7528" : "\u5df2\u6682\u505c", "ok");
      Views.refreshPanels();
    };
    toggleLabel.appendChild(toggleInput);
    toggleLabel.appendChild(el("span", { class: "toggle-track" }));
    toggleLabel.appendChild(el("span", { class: "toggle-label", text: isActive ? "\u542f\u7528" : "\u6682\u505c" }));
    top.appendChild(toggleLabel);
    body.appendChild(top);

    if (j.prompt) body.appendChild(el("div", { class: "cron-tc-desc", text: j.prompt }));
    body.appendChild(el("div", { class: "cron-tc-meta" }, runInfo.map(t => el("span", { text: t }))));
    card.appendChild(body);

    // 操作按钮
    const actions = el("div", { class: "cron-tc-actions" });
    actions.appendChild(el("button", { class: "btn ghost", text: "\u25b6",
      title: "\u7acb\u5373\u8fd0\u884c", onclick: async () => {
        const r = await postJSON("/api/cron/" + encodeURIComponent(j.id) + "/run", {}).catch((e) => ({ ok: false, error: e.message }));
        if (r.ok) toast("\u5df2\u89e6\u53d1\u6267\u884c", "ok"); else toast("\u5931\u8d25\uff1a" + (r.error || ""), "err");
        Views.refreshPanels();
      } }));
    actions.appendChild(el("button", { class: "btn ghost", text: "\u270f\ufe0f",
      title: "\u7f16\u8f91", onclick: () => openCronEditForm(j) }));
    if (!isArchived) {
      actions.appendChild(el("button", { class: "btn ghost", text: "\ud83d\udcc1",
        title: "\u5f52\u6863", onclick: async () => {
          if (!confirm("\u5f52\u6863\u4efb\u52a1\uff1a" + (j.name || j.id) + "\uff1f")) return;
          await postJSON("/api/cron/" + encodeURIComponent(j.id) + "/status", { status: "archived" }).catch(() => {});
          Views.refreshPanels();
        } }));
    }
    actions.appendChild(el("button", { class: "btn danger-ghost", text: "\u2716",
      title: "\u5220\u9664", onclick: async () => {
        if (!confirm("\u5220\u9664\u5b9a\u65f6\u4efb\u52a1\uff1a" + (j.name || j.id) + "\uff1f")) return;
        await delJSON("/api/cron/" + encodeURIComponent(j.id)).catch(() => {});
        Views.refreshPanels();
      } }));
    card.appendChild(actions);
    list.appendChild(card);
  }
  wrap.appendChild(list);

  // 新建按钮
  wrap.appendChild(el("div", { style: "margin-top:14px;display:flex;gap:10px;align-items:center;" }, [
    el("button", { class: "btn primary", text: "+ \u65b0\u5efa\u5b9a\u65f6\u4efb\u52a1",
      onclick: () => openCronCreateForm() }),
    el("button", { class: "btn", text: "\ud83d\udccb \u4ece\u6a21\u677f\u6dfb\u52a0",
      onclick: () => showCronTemplates() }),
  ]));

  // 模板推荐
  wrap.appendChild(el("div", { class: "section-title", style: "margin-top:18px;", text: "\u6a21\u677f\u63a8\u8350" }));
  renderTemplateGrid(wrap, activeCount, maxJobs);
}

function updateBatchBar(bar, countEl) {
  const n = _cronSelected.size;
  countEl.textContent = n;
  bar.classList.toggle("visible", n > 0);
}

async function batchCronAction(action) {
  if (_cronSelected.size === 0) return;
  const ids = Array.from(_cronSelected);
  if (action === "delete") {
    if (!confirm("\u786e\u5b9a\u5220\u9664\u9009\u4e2d\u7684 " + ids.length + " \u4e2a\u4efb\u52a1\uff1f")) return;
  }
  let ok = 0, fail = 0;
  for (const id of ids) {
    try {
      if (action === "delete") {
        await delJSON("/api/cron/" + encodeURIComponent(id));
      } else {
        await postJSON("/api/cron/" + encodeURIComponent(id) + "/status", { status: action });
      }
      ok++;
    } catch (e) { fail++; }
  }
  _cronSelected.clear();
  toast("\u6279\u91cf\u64cd\u4f5c\u5b8c\u6210\uff1a" + ok + " \u6210\u529f" + (fail ? "\uff0c" + fail + " \u5931\u8d25" : ""), fail ? "err" : "ok");
  Views.refreshPanels();
}

function renderEmptyState(wrap, activeCount, maxJobs) {
  const empty = el("div", { class: "cron-empty" }, [
    el("div", { class: "cron-empty-icon", text: "\u23f0" }),
    el("div", { class: "cron-empty-title", text: "\u8fd8\u6ca1\u6709\u5b9a\u65f6\u4efb\u52a1" }),
    el("div", { class: "cron-empty-desc", text: "\u8bd5\u8bd5\u4e0b\u65b9\u7684\u63a8\u8350\u6a21\u677f\u5feb\u901f\u5f00\u59cb\uff0c\u6216\u70b9\u51fb\u53f3\u4e0a\u89d2\u65b0\u5efa\u4e00\u4e2a\u81ea\u5b9a\u4e49\u4efb\u52a1\u3002\u6700\u591a\u53ef\u540c\u65f6\u542f\u7528" + maxJobs + "\u4e2a\u4efb\u52a1\u3002" }),
  ]);
  wrap.appendChild(empty);

  wrap.appendChild(el("div", { class: "section-title", text: "\u63a8\u8350\u6a21\u677f" }));
  renderTemplateGrid(wrap, activeCount, maxJobs);
}

function renderTemplateGrid(wrap, activeCount, maxJobs) {
  // 预设模板
  const _TEMPLATES = [
    { name: "\u6bcf\u65e5\u65b0\u95fb", desc: "\u5173\u6ce8\u5f53\u5929\u56fd\u9645\u653f\u6cbb\u9886\u57df\u7684\u91cd\u8981\u52a8\u6001\uff0c\u4fa7\u91cd\u5730\u7f18\u51b2\u7a81\uff0c\u539f\u6cb9\u4ef7\u683c\uff0c\u7b5b\u90093-5\u6761\u6709\u4ef7\u503c\u7684\u65b0\u95fb\u5e76\u751f\u6210\u6458\u8981\u3002", schedule: "0 9 * * *", label: "09:00 \u00b7 \u6bcf\u5929", icon: "\ud83d\udcf0" },
    { name: "\u7761\u524d\u6545\u4e8b", desc: "\u5199\u4e00\u4e2a\u9002\u5408\u513f\u7ae5\u7684\u7761\u524d\u6545\u4e8b\uff0c\u8bed\u8a00\u6e29\u548c\u6613\u61c2\uff0c\u9605\u8bfb\u65f6\u957f\u7ea63-5\u5206\u949f\u3002\u6545\u4e8b\u9700\u6709\u5b8c\u6574\u7684\u60c5\u8282\u548c\u79ef\u6781\u7684\u4e3b\u9898\u3002", schedule: "30 21 * * *", label: "21:30 \u00b7 \u6bcf\u5929", icon: "\ud83d\udcd6" },
    { name: "\u5386\u53f2\u4e0a\u7684\u4eca\u5929", desc: "\u5386\u53f2\u4e0a\u7684\u4eca\u5929\u53d1\u751f\u8fc7\u4ec0\u4e48\u6709\u8da3\u7684\u4e8b\uff1f\u4ece\u79d1\u6280\u3001\u7535\u5f71\u3001\u97f3\u4e50\u7b49\u9886\u57df\u4e2d\u6311\u4e00\u4e2a\uff0c\u8bb2\u8bb2\u5b83\u7684\u6545\u4e8b\u548c\u5f71\u54cd\u3002", schedule: "30 9 * * *", label: "09:30 \u00b7 \u6bcf\u5929", icon: "\ud83d\udcc5" },
    { name: "\u4f53\u68c0\u9884\u7ea6\u63d0\u9192", desc: "\u63d0\u9192\u6211\u786e\u8ba4\u4f53\u68c0\u65f6\u95f4\u3001\u51c6\u5907\u8bc1\u4ef6\uff0c\u63d0\u524d\u7a7a\u8179\u5e76\u7559\u610f\u6ce8\u610f\u4e8b\u9879\u3002", schedule: "0 7 10 8 *", label: "07:00 \u00b7 2026/08/10", icon: "\u2695\ufe0f" },
    { name: "\u5de5\u4f5c\u5468\u62a5", desc: "\u68b3\u7406\u684c\u9762\u4e0a\u7684\u5de5\u4f5c\u76f8\u5173\u6587\u4ef6\uff0c\u8f93\u51fa\u4e00\u4efd\u5468\u62a5\uff0c\u6db5\u76d6\u672c\u5468\u9879\u76ee\u7684\u4e3b\u8981\u8fdb\u5c55\u3001\u5173\u952e\u53d8\u66f4\u548c\u4e0b\u5468\u8ba1\u5212\u3002", schedule: "0 17 * * 5", label: "17:00 \u00b7 \u5468\u4e94", icon: "\ud83d\udcca" },
    { name: "\u9762\u8bd5\u51c6\u5907", desc: "\u6bcf\u4e2a\u5de5\u4f5c\u65e5\u4e3a\u6211\u6536\u96c6\u5927\u6a21\u578b\u7684\u9879\u76ee\u4eae\u70b9\u3001\u6280\u672f\u96be\u70b9\u3001\u5e38\u89c1\u95ee\u7b54\u76f8\u5173\u4fe1\u606f\uff0c\u5e76\u751f\u62103\u4e2a\u9762\u8bd5\u7ec3\u4e60\u9898\u76ee\u3002", schedule: "0 9 * * 1-5", label: "09:00 \u00b7 \u5de5\u4f5c\u65e5", icon: "\ud83c\udf93" },
  ];

  const grid = el("div", { class: "cron-template-grid" });
  for (const t of _TEMPLATES) {
    const card = el("div", { class: "cron-template-card" }, [
      el("div", { class: "cron-tmpl-icon", text: t.icon }),
      el("div", { class: "cron-tmpl-body" }, [
        el("div", { class: "cron-tmpl-name", text: t.name }),
        el("div", { class: "cron-tmpl-desc", text: t.desc }),
        el("div", { class: "cron-tmpl-sched", text: t.label }),
      ]),
      el("button", { class: "btn sm", text: "+ \u6dfb\u52a0",
        onclick: async () => {
          if (activeCount >= maxJobs) {
            toast("\u5df2\u8fbe\u5230\u6700\u5927\u542f\u7528\u6570\uff08" + maxJobs + "\u4e2a\uff09\uff0c\u8bf7\u5148\u6682\u505c\u5176\u4ed6\u4efb\u52a1", "err");
            return;
          }
          const r = await postJSON("/api/cron", { name: t.name, prompt: t.desc, schedule: t.schedule }).catch((e) => ({ ok: false, error: e.message }));
          if (r.ok) { toast("\u5df2\u6dfb\u52a0\u6a21\u677f\uff1a" + t.name, "ok"); Views.refreshPanels(); }
          else toast("\u6dfb\u52a0\u5931\u8d25\uff1a" + (r.error || ""), "err");
        } }),
    ]);
    grid.appendChild(card);
  }
  wrap.appendChild(grid);
}

function renderHistoryTab(wrap, execs) {
  if (execs.length === 0) {
    wrap.appendChild(el("div", { class: "cron-empty", style: "margin-top:20px;" }, [
      el("div", { class: "cron-empty-icon", text: "\ud83d\udcc4" }),
      el("div", { class: "cron-empty-title", text: "\u6682\u65e0\u6267\u884c\u8bb0\u5f55" }),
      el("div", { class: "cron-empty-desc", text: "\u4efb\u52a1\u8fd0\u884c\u540e\uff0c\u5c06\u5728\u6b64\u5c55\u793a\u5386\u53f2\u8bb0\u5f55\u3002" }),
      el("button", { class: "btn primary", style: "margin-top:12px;", text: "+ \u65b0\u5efa\u5b9a\u65f6\u4efb\u52a1",
        onclick: () => { _cronActiveTab = "tasks"; Views.refreshPanels(); } }),
    ]));
    return;
  }

  // 清空历史按钮
  const topBar = el("div", { style: "display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;" });
  topBar.appendChild(el("span", { class: "muted small", text: "\u5171 " + execs.length + " \u6761\u8bb0\u5f55" }));
  topBar.appendChild(el("button", { class: "cron-clear-history", text: "\u6e05\u7a7a\u5168\u90e8",
    onclick: async () => {
      if (!confirm("\u786e\u5b9a\u6e05\u7a7a\u5168\u90e8\u6267\u884c\u8bb0\u5f55\uff1f")) return;
      await postJSON("/api/cron/executions/clear", {}).catch(() => {});
      Views.refreshPanels();
    } }));
  wrap.appendChild(topBar);

  const table = el("div", { class: "cron-history-table" });
  // 表头
  const thead = el("div", { class: "cron-ht-head" }, [
    el("span", { class: "cron-ht-cell cron-ht-col-task", text: "\u4efb\u52a1" }),
    el("span", { class: "cron-ht-cell cron-ht-col-time", text: "\u65f6\u95f4" }),
    el("span", { class: "cron-ht-cell cron-ht-col-status", text: "\u72b6\u6001" }),
    el("span", { class: "cron-ht-cell cron-ht-col-result", text: "\u6267\u884c\u7ed3\u679c" }),
  ]);
  table.appendChild(thead);

  for (const e of execs) {
    const statusIcon = e.status === "success" || e.status === "done" ? "\u2705" : e.status === "error" ? "\u274c" : "\u23f3";
    const statusClass = e.status === "success" || e.status === "done" ? "cron-h-done" : e.status === "error" ? "cron-h-err" : "cron-h-run";
    const row = el("div", { class: "cron-ht-row " + statusClass });
    row.appendChild(el("span", { class: "cron-ht-cell cron-ht-col-task", text: e.job_name || e.job_id || "-" }));
    row.appendChild(el("span", { class: "cron-ht-cell cron-ht-col-time", text: e.time || "-" }));
    row.appendChild(el("span", { class: "cron-ht-cell cron-ht-col-status" }, [
      el("span", { text: statusIcon + " " + (e.status === "success" || e.status === "done" ? "\u6210\u529f" : e.status === "error" ? "\u5931\u8d25" : "\u8fd0\u884c\u4e2d") }),
    ]));
    row.appendChild(el("span", { class: "cron-ht-cell cron-ht-col-result", text: e.result || e.error || "-" }));

    // 详情展开行
    const detail = el("div", { class: "cron-ht-detail" });
    if (e.error) detail.appendChild(el("div", {}, [
      el("span", { class: "detail-label", text: "\u9519\u8bef\u8be6\u60c5\uff1a" }),
      el("span", { class: "detail-error", text: e.error }),
    ]));
    if (e.result && e.result.length > 50) detail.appendChild(el("div", { style: "margin-top:4px;" }, [
      el("span", { class: "detail-label", text: "\u6267\u884c\u7ed3\u679c\uff1a" }),
      el("span", { class: "detail-result", text: e.result }),
    ]));
    if (!detail.hasChildNodes()) {
      detail.appendChild(el("div", { class: "muted small", text: "\u65e0\u8be6\u7ec6\u4fe1\u606f" }));
    }

    row.onclick = () => {
      detail.classList.toggle("open");
    };
    table.appendChild(row);
    table.appendChild(detail);
  }
  wrap.appendChild(table);
}

// 新建定时任务弹窗
function openCronCreateForm() {
  const overlay = el("div", { class: "ss-edit-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });
  const modal = el("div", { class: "ss-edit-modal" });
  modal.appendChild(el("h3", { text: "\u65b0\u589e\u5b9a\u65f6\u4efb\u52a1" }));
  modal.appendChild(createCronForm(null, () => { overlay.remove(); Views.refreshPanels(); }));
  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}

// 编辑定时任务弹窗
function openCronEditForm(j) {
  const overlay = el("div", { class: "ss-edit-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });
  const modal = el("div", { class: "ss-edit-modal" });
  modal.appendChild(el("h3", { text: "\u7f16\u8f91\u5b9a\u65f6\u4efb\u52a1\uff1a" + (j.name || j.id) }));
  modal.appendChild(createCronForm(j, () => { overlay.remove(); Views.refreshPanels(); }));
  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}

// 模板选择弹窗
function showCronTemplates() {
  const overlay = el("div", { class: "ss-edit-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });
  const modal = el("div", { class: "ss-edit-modal", style: "width:min(750px,92vw);" });
  modal.appendChild(el("h3", { text: "\u4ece\u6a21\u677f\u6dfb\u52a0" }));
  const grid = el("div", { class: "cron-template-grid", style: "margin-top:12px;" });
  const _TEMPLATES = [
    { name: "\u6bcf\u65e5\u65b0\u95fb", desc: "\u5173\u6ce8\u5f53\u5929\u56fd\u9645\u653f\u6cbb\u9886\u57df\u7684\u91cd\u8981\u52a8\u6001\uff0c\u4fa7\u91cd\u5730\u7f18\u51b2\u7a81\uff0c\u539f\u6cb9\u4ef7\u683c\uff0c\u7b5b\u90093-5\u6761\u6709\u4ef7\u503c\u7684\u65b0\u95fb\u5e76\u751f\u6210\u6458\u8981\u3002", schedule: "0 9 * * *", label: "09:00 \u00b7 \u6bcf\u5929", icon: "\ud83d\udcf0" },
    { name: "\u7761\u524d\u6545\u4e8b", desc: "\u5199\u4e00\u4e2a\u9002\u5408\u513f\u7ae5\u7684\u7761\u524d\u6545\u4e8b\uff0c\u8bed\u8a00\u6e29\u548c\u6613\u61c2\uff0c\u9605\u8bfb\u65f6\u957f\u7ea63-5\u5206\u949f\u3002\u6545\u4e8b\u9700\u6709\u5b8c\u6574\u7684\u60c5\u8282\u548c\u79ef\u6781\u7684\u4e3b\u9898\u3002", schedule: "30 21 * * *", label: "21:30 \u00b7 \u6bcf\u5929", icon: "\ud83d\udcd6" },
    { name: "\u5386\u53f2\u4e0a\u7684\u4eca\u5929", desc: "\u5386\u53f2\u4e0a\u7684\u4eca\u5929\u53d1\u751f\u8fc7\u4ec0\u4e48\u6709\u8da3\u7684\u4e8b\uff1f\u4ece\u79d1\u6280\u3001\u7535\u5f71\u3001\u97f3\u4e50\u7b49\u9886\u57df\u4e2d\u6311\u4e00\u4e2a\uff0c\u8bb2\u8bb2\u5b83\u7684\u6545\u4e8b\u548c\u5f71\u54cd\u3002", schedule: "30 9 * * *", label: "09:30 \u00b7 \u6bcf\u5929", icon: "\ud83d\udcc5" },
    { name: "\u4f53\u68c0\u9884\u7ea6\u63d0\u9192", desc: "\u63d0\u9192\u6211\u786e\u8ba4\u4f53\u68c0\u65f6\u95f4\u3001\u51c6\u5907\u8bc1\u4ef6\uff0c\u63d0\u524d\u7a7a\u8179\u5e76\u7559\u610f\u6ce8\u610f\u4e8b\u9879\u3002", schedule: "0 7 10 8 *", label: "07:00 \u00b7 2026/08/10", icon: "\u2695\ufe0f" },
    { name: "\u5de5\u4f5c\u5468\u62a5", desc: "\u68b3\u7406\u684c\u9762\u4e0a\u7684\u5de5\u4f5c\u76f8\u5173\u6587\u4ef6\uff0c\u8f93\u51fa\u4e00\u4efd\u5468\u62a5\uff0c\u6db5\u76d6\u672c\u5468\u9879\u76ee\u7684\u4e3b\u8981\u8fdb\u5c55\u3001\u5173\u952e\u53d8\u66f4\u548c\u4e0b\u5468\u8ba1\u5212\u3002", schedule: "0 17 * * 5", label: "17:00 \u00b7 \u5468\u4e94", icon: "\ud83d\udcca" },
    { name: "\u9762\u8bd5\u51c6\u5907", desc: "\u6bcf\u4e2a\u5de5\u4f5c\u65e5\u4e3a\u6211\u6536\u96c6\u5927\u6a21\u578b\u7684\u9879\u76ee\u4eae\u70b9\u3001\u6280\u672f\u96be\u70b9\u3001\u5e38\u89c1\u95ee\u7b54\u76f8\u5173\u4fe1\u606f\uff0c\u5e76\u751f\u62103\u4e2a\u9762\u8bd5\u7ec3\u4e60\u9898\u76ee\u3002", schedule: "0 9 * * 1-5", label: "09:00 \u00b7 \u5de5\u4f5c\u65e5", icon: "\ud83c\udf93" },
  ];
  for (const t of _TEMPLATES) {
    const card = el("div", { class: "cron-template-card" }, [
      el("div", { class: "cron-tmpl-icon", text: t.icon }),
      el("div", { class: "cron-tmpl-body" }, [
        el("div", { class: "cron-tmpl-name", text: t.name }),
        el("div", { class: "cron-tmpl-desc", text: t.desc }),
        el("div", { class: "cron-tmpl-sched", text: t.label }),
      ]),
      el("button", { class: "btn sm", text: "+ \u6dfb\u52a0",
        onclick: async () => {
          const r = await postJSON("/api/cron", { name: t.name, prompt: t.desc, schedule: t.schedule }).catch((e) => ({ ok: false, error: e.message }));
          if (r.ok) { toast("\u5df2\u6dfb\u52a0\u6a21\u677f\uff1a" + t.name, "ok"); overlay.remove(); Views.refreshPanels(); }
          else toast("\u6dfb\u52a0\u5931\u8d25\uff1a" + (r.error || ""), "err");
        } }),
    ]);
    grid.appendChild(card);
  }
  modal.appendChild(grid);
  modal.appendChild(el("div", { style: "text-align:right;margin-top:12px;" }, [
    el("button", { class: "btn", text: "\u53d6\u6d88", onclick: () => overlay.remove() }),
  ]));
  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}

// 定时任务表单（新建/编辑共用）
function createCronForm(editData, onSaved) {
  const isEdit = editData !== null;
  const form = el("div", { class: "panel" });
  const jn = el("input", { placeholder: "\u4efb\u52a1\u540d\uff08\u5fc5\u586b\uff09", value: editData ? editData.name || "" : "" });
  const jp = el("textarea", { placeholder: "\u4efb\u52a1\u63d0\u793a\uff08\u5fc5\u586b\uff09", value: editData ? editData.prompt || "" : "" });
  const js = el("input", { placeholder: "\u8c03\u5ea6\uff08cron \u6216\u81ea\u7136\u8bed\u8a00\uff0c\u5982 0 9 * * *\uff09", value: editData ? editData.schedule || "" : "" });
  const cronHelp = el("div", { class: "muted small", style: "margin-top:4px;line-height:1.7;", text: "\u683c\u5f0f\uff1a\u5206 \u65f6 \u65e5 \u6708 \u5468  \u4f8b\u5982\uff1a0 9 * * * = \u6bcf\u5929 9:00\uff0c30 21 * * * = \u6bcf\u5929 21:30\uff0c0 17 * * 5 = \u6bcf\u5468\u4e94 17:00\uff0c0 9 * * 1-5 = \u5de5\u4f5c\u65e5 9:00" });
  const errMsg = el("div", { class: "muted", style: "color:var(--danger);display:none;margin-bottom:8px;" });

  form.appendChild(el("div", { class: "field" }, [el("label", { text: "\u540d\u79f0" }), jn]));
  form.appendChild(el("div", { class: "field" }, [el("label", { text: "\u63d0\u793a\u8bcd" }), jp]));
  form.appendChild(el("div", { class: "field" }, [el("label", { text: "\u8c03\u5ea6" }), js, cronHelp]));

  // Cron 预设快捷按钮
  const presets = el("div", { class: "cron-presets" });
  const _PRESETS = [
    { label: "\u6bcf\u5929 9:00", cron: "0 9 * * *" },
    { label: "\u6bcf\u5929 21:30", cron: "30 21 * * *" },
    { label: "\u5de5\u4f5c\u65e5 9:00", cron: "0 9 * * 1-5" },
    { label: "\u6bcf\u5468\u4e94 17:00", cron: "0 17 * * 5" },
    { label: "\u6bcf\u5c0f\u65f6", cron: "0 * * * *" },
    { label: "\u6bcf30\u5206\u949f", cron: "*/30 * * * *" },
  ];
  for (const p of _PRESETS) {
    presets.appendChild(el("button", { class: "cron-preset-btn", text: p.label,
      onclick: () => { js.value = p.cron; } }));
  }
  form.appendChild(presets);

  form.appendChild(errMsg);

  const btnText = isEdit ? "\u4fdd\u5b58\u4fee\u6539" : "\u4fdd\u5b58\u4efb\u52a1";
  const btn = el("button", { class: "btn primary", text: btnText, onclick: async () => {
    errMsg.style.display = "none";
    if (!jn.value.trim()) {
      errMsg.textContent = "\u8bf7\u586b\u5199\u4efb\u52a1\u540d";
      errMsg.style.display = ""; jn.focus(); return;
    }
    if (!jp.value.trim()) {
      errMsg.textContent = "\u8bf7\u586b\u5199\u4efb\u52a1\u63d0\u793a\u8bcd";
      errMsg.style.display = ""; jp.focus(); return;
    }
    const body = { name: jn.value.trim(), prompt: jp.value.trim(), schedule: js.value.trim() };
    let r;
    if (isEdit) {
      r = await fetch("/api/cron/" + encodeURIComponent(editData.id), {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(res => res.json()).catch(e => ({ ok: false, error: e.message }));
    } else {
      r = await postJSON("/api/cron", body).catch(e => ({ ok: false, error: e.message }));
    }
    if (r && r.ok) {
      toast(isEdit ? "\u5df2\u4fee\u6539" : "\u5df2\u4fdd\u5b58", "ok");
      if (onSaved) onSaved();
    } else {
      toast("\u4fdd\u5b58\u5931\u8d25\uff1a" + ((r && r.error) || "\u672a\u77e5\u9519\u8bef"), "err");
    }
  } });
  form.appendChild(el("div", { class: "actions-row", style: "margin-top:8px;" }, [
    btn,
    el("button", { class: "btn ghost", text: "\u53d6\u6d88", onclick: () => {
      // 向上查找 overlay 并关闭
      let el = form.parentElement;
      while (el) {
        if (el.classList && el.classList.contains("ss-edit-overlay")) { el.remove(); break; }
        if (el.classList && el.classList.contains("ss-edit-modal")) { const ov = el.parentElement; if (ov) ov.remove(); break; }
        el = el.parentElement;
      }
    } }),
  ]));
  return form;
}
