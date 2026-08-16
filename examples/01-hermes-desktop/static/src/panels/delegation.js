// @ts-check
/* =====================================================================
 * delegation.js — delegation 面板子模块
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { State } from "../state.js";
import { getJSON, postJSON, delJSON, parseSSE } from "../api.js";
import * as Views from "../views.js";
// ------------------------------------------------------------------ 委派面板（三标签页：执行 / 运行中 / 历史）
let _delegActiveTab = "execute";
let _delegRefreshTimer = null;

export async function renderDelegationPanel(body) {
  if (_delegRefreshTimer) { clearInterval(_delegRefreshTimer); _delegRefreshTimer = null; }

  const data = await getJSON("/api/delegation");
  const cfg = data.config || {};
  const subagents = data.subagents || [];
  const running = data.running || [];
  const hasActive = subagents.length > 0 || running.some(r => r.status === "running" || r.status === "cancelling");
  const wrap = el("div", { class: "panel" });

  // 统计信息
  wrap.appendChild(el("div", { class: "deleg-stats" }, [
    el("span", { class: "deleg-stat-item", text: "\uD83D\uDC65 委派管理" }),
    el("span", { class: "deleg-stat-item", text: `\u26A1 活跃子智能体 ${subagents.length}` }),
    el("span", { class: "deleg-stat-item muted small", text: "将复杂目标拆解为并行的子任务，由多个子智能体协作完成" }),
  ]));

  // 标签页
  const tabBar = el("div", { class: "deleg-tabs" }, [
    el("button", { class: "deleg-tab" + (_delegActiveTab === "execute" ? " active" : ""), text: "\u25B6 执行",
      onclick: () => { _delegActiveTab = "execute"; Views.refreshPanels(); } }),
    el("button", { class: "deleg-tab" + (_delegActiveTab === "active" ? " active" : ""), text: `\u26A1 运行中 (${subagents.length})`,
      onclick: () => { _delegActiveTab = "active"; Views.refreshPanels(); } }),
    el("button", { class: "deleg-tab" + (_delegActiveTab === "history" ? " active" : ""), text: `\uD83D\uDCCB 历史 (${running.length})`,
      onclick: () => { _delegActiveTab = "history"; Views.refreshPanels(); } }),
  ]);
  wrap.appendChild(tabBar);

  if (_delegActiveTab === "execute") {
    renderDelegExecuteTab(wrap, cfg, hasActive);
  } else if (_delegActiveTab === "active") {
    renderDelegActiveTab(wrap, subagents);
    if (subagents.length > 0) {
      _delegRefreshTimer = setInterval(() => { Views.refreshPanels(); }, 10000);
    }
  } else {
    renderDelegHistoryTab(wrap, running);
  }

  body.appendChild(wrap);
}
function renderDelegExecuteTab(wrap, cfg, hasActive) {
  if (hasActive) {
    wrap.appendChild(el("div", { class: "deleg-banner", text: "\u26A0\uFE0F 已有正在运行的委派任务，提交新委派将并行执行" }));
  }
  const goal = el("textarea", { class: "deleg-goal-inp", placeholder: "输入一个需要拆解为多个子任务的复杂目标，例如：\n分别调研 Python 的 FastAPI、Flask、Django 三个框架的优缺点并对比" });
  wrap.appendChild(el("div", { class: "field" }, [el("label", { text: "委派目标" }), goal]));

  // 可折叠配置区
  const cfgToggle = el("span", { class: "deleg-cfg-toggle", text: "\u2699 委派参数配置" });
  const cfgBody = el("div", { class: "deleg-cfg-body hidden" });
  cfgToggle.onclick = () => { cfgBody.classList.toggle("hidden"); cfgToggle.classList.toggle("open"); };

  const childModel = el("input", { class: "form-input", placeholder: "子 agent 模型（留空=继承父模型）", value: cfg.child_model || "" });
  const depth = el("input", { class: "form-input", type: "number", min: "1", max: "5", value: String(cfg.max_spawn_depth ?? 1) });
  const conc = el("input", { class: "form-input", type: "number", min: "1", max: "12", value: String(cfg.max_concurrent_children ?? 3) });
  const to = el("input", { class: "form-input", type: "number", min: "30", step: "10", value: String(cfg.child_timeout_seconds ?? "") });
  const childProvider = el("input", { class: "form-input", placeholder: "子 agent provider（留空=继承父）", value: cfg.child_provider || "" });
  const childRole = el("select", { class: "form-input" }, [
    el("option", { value: "leaf", text: "leaf（默认，受限工具，不可再委派/询问/写记忆）", selected: (cfg.child_role || "leaf") === "leaf" }),
    el("option", { value: "orchestrator", text: "orchestrator（可再委派，受 max_spawn_depth 约束）", selected: (cfg.child_role || "leaf") === "orchestrator" }),
  ]);
  const inheritMcp = el("input", { class: "form-check", type: "checkbox", checked: !!cfg.inherit_mcp_toolsets });
  const autoApprove = el("input", { class: "form-check", type: "checkbox", checked: !!cfg.subagent_auto_approve });
  const expectedOutput = el("input", { class: "form-input", placeholder: "预期输出格式（可选），如：JSON 数组（并入子任务 context）", value: cfg.expected_output || "" });
  const contextShare = el("input", { class: "form-input", placeholder: "共享上下文文件路径（可选，逗号分隔，内容并入子任务 context）", value: Array.isArray(cfg.context_share) ? cfg.context_share.join(",") : "" });

  cfgBody.appendChild(el("div", { class: "deleg-cfg-grid" }, [
    el("div", { class: "deleg-cfg-item" }, [
      el("div", { class: "deleg-cfg-label", text: "子模型" }),
      el("div", { class: "deleg-cfg-desc muted small", text: "指定子 agent 使用的模型，留空则继承父模型" }),
      childModel,
    ]),
    el("div", { class: "deleg-cfg-item" }, [
      el("div", { class: "deleg-cfg-label", text: "最大派生深度" }),
      el("div", { class: "deleg-cfg-desc muted small", text: "1=扁平（子 agent 不能再委派），2+=允许嵌套" }),
      depth,
    ]),
    el("div", { class: "deleg-cfg-item" }, [
      el("div", { class: "deleg-cfg-label", text: "最大并发子数" }),
      el("div", { class: "deleg-cfg-desc muted small", text: "同时运行的子 agent 数量上限，默认 3" }),
      conc,
    ]),
    el("div", { class: "deleg-cfg-item" }, [
      el("div", { class: "deleg-cfg-label", text: "子超时(秒)" }),
      el("div", { class: "deleg-cfg-desc muted small", text: "单个子 agent 超时限制，留空=无硬超时" }),
      to,
    ]),
    el("div", { class: "deleg-cfg-item" }, [
      el("div", { class: "deleg-cfg-label", text: "子Provider" }),
      el("div", { class: "deleg-cfg-desc muted small", text: "子 agent 使用的 provider，留空则继承父" }),
      childProvider,
    ]),
    el("div", { class: "deleg-cfg-item" }, [
      el("div", { class: "deleg-cfg-label", text: "子角色" }),
      el("div", { class: "deleg-cfg-desc muted small", text: "leaf 受限工具；orchestrator 可再委派（防 runaway 委托链）" }),
      childRole,
    ]),
    el("div", { class: "deleg-cfg-item" }, [
      el("div", { class: "deleg-cfg-label", text: "继承MCP工具集" }),
      el("div", { class: "deleg-cfg-desc muted small", text: "子 agent 是否继承父的 MCP 工具集" }),
      inheritMcp,
    ]),
    el("div", { class: "deleg-cfg-item" }, [
      el("div", { class: "deleg-cfg-label", text: "子自动批准" }),
      el("div", { class: "deleg-cfg-desc muted small", text: "子 agent 危险命令自动批准（谨慎，默认关）" }),
      autoApprove,
    ]),
    el("div", { class: "deleg-cfg-item" }, [
      el("div", { class: "deleg-cfg-label", text: "预期输出" }),
      el("div", { class: "deleg-cfg-desc muted small", text: "约束子任务返回格式（并入 context）" }),
      expectedOutput,
    ]),
    el("div", { class: "deleg-cfg-item" }, [
      el("div", { class: "deleg-cfg-label", text: "共享上下文文件" }),
      el("div", { class: "deleg-cfg-desc muted small", text: "逗号分隔的文件路径，内容并入每个子任务 context" }),
      contextShare,
    ]),
  ]));
  cfgBody.appendChild(el("div", { class: "actions-row" }, [
    el("button", { class: "btn ghost", text: "\uD83D\uDCBE 保存配置", onclick: async () => {
      const r = await postJSON("/api/delegation/config", {
        child_model: childModel.value.trim(),
        child_provider: childProvider.value.trim(),
        child_role: childRole.value,
        inherit_mcp_toolsets: inheritMcp.checked,
        subagent_auto_approve: autoApprove.checked,
        expected_output: expectedOutput.value.trim(),
        context_share: contextShare.value.split(",").map(v => v.trim()).filter(Boolean),
        max_spawn_depth: parseInt(depth.value || "1", 10),
        max_concurrent_children: parseInt(conc.value || "3", 10),
        child_timeout_seconds: to.value ? parseInt(to.value, 10) : null,
      }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) toast("配置已保存", "ok"); else toast("保存失败：" + (r.error || ""), "err");
    } }),
  ]));

  wrap.appendChild(cfgToggle);
  wrap.appendChild(cfgBody);

  // 运行按钮
  const runBtn = el("button", { class: "btn primary", style: "margin-top:14px;width:100%;padding:10px;font-size:14px;", text: "\uD83D\uDE80 运行委派" });
  runBtn.onclick = async () => {
    if (!goal.value.trim()) { toast("请填写目标", "err"); goal.focus(); return; }
    runBtn.disabled = true; runBtn.textContent = "\u23F3 委派启动中\u2026";
    const r = await postJSON("/api/delegation/run", {
      goal: goal.value.trim(),
      options: {
        child_model: childModel.value.trim(),
        child_provider: childProvider.value.trim(),
        child_role: childRole.value,
        inherit_mcp_toolsets: inheritMcp.checked,
        subagent_auto_approve: autoApprove.checked,
        expected_output: expectedOutput.value.trim(),
        context_share: contextShare.value.split(",").map(v => v.trim()).filter(Boolean),
        max_spawn_depth: parseInt(depth.value || "1", 10),
        max_concurrent_children: parseInt(conc.value || "3", 10),
        child_timeout_seconds: to.value ? parseInt(to.value, 10) : null,
      },
    }).catch(e => ({ ok: false, error: e.message }));
    runBtn.disabled = false; runBtn.textContent = "\uD83D\uDE80 运行委派";
    if (r.ok) {
      toast("委派已启动，切换到「运行中」标签查看进度", "ok");
      _delegActiveTab = "active";
      Views.refreshPanels();
    } else {
      toast("启动失败：" + (r.error || ""), "err");
    }
  };
  wrap.appendChild(runBtn);

  // 提示信息
  wrap.appendChild(el("div", { class: "deleg-hint", text: "子 agent 从空白上下文起步，每个子任务描述须自带足够上下文。运行后可在「运行中」标签查看实时进度，在「历史」标签查看结果。" }));
}

// ── 运行中标签页 ──────────────────────────────────────────────────────────
function renderDelegActiveTab(wrap, subagents) {
  if (subagents.length === 0) {
    wrap.appendChild(el("div", { class: "deleg-empty" }, [
      el("div", { class: "deleg-empty-icon", text: "\u2705" }),
      el("div", { class: "deleg-empty-title", text: "无活跃子智能体" }),
      el("div", { class: "deleg-empty-desc", text: "当前没有正在运行的委派任务。切换到「执行」标签页提交一个复杂目标即可开始。" }),
    ]));
    return;
  }

  const list = el("div", { class: "card-list", style: "display:flex;flex-direction:column;gap:8px;" });
  for (const sa of subagents) {
    const sid = sa.subagent_id || "";
    const isRunning = sa.status === "running" || !sa.status;
    const card = el("div", { class: "deleg-sa-card" });

    // 头部
    const head = el("div", { class: "deleg-sa-head" });
    head.appendChild(el("div", { class: "deleg-sa-name", text: (sa.goal || sid).slice(0, 80) }));
    head.appendChild(el("span", { class: "badge " + (isRunning ? "on" : "off"), text: isRunning ? "运行中" : (sa.status || "未知") }));
    card.appendChild(head);

    // 元信息
    const meta = el("div", { class: "deleg-sa-meta" });
    const metaParts = [];
    if (sa.model) metaParts.push("模型：" + sa.model);
    if (sa.depth !== undefined) metaParts.push("深度：" + sa.depth);
    if (sa.parent_id) metaParts.push("父：" + sa.parent_id.slice(0, 8));
    if (sa.started_at) metaParts.push("启动：" + new Date(sa.started_at).toLocaleTimeString());
    if (sa.tool_count !== undefined) metaParts.push("工具调用：" + sa.tool_count + " 次");
    meta.textContent = metaParts.join("  \u00B7  ");
    card.appendChild(meta);

    // 操作按钮
    const actions = el("div", { class: "deleg-sa-actions" });
    if (isRunning) {
      actions.appendChild(el("button", { class: "btn danger-ghost", text: "\u25A0 中断",
        onclick: async () => {
          if (!confirm("中断子智能体：" + (sa.goal || sid).slice(0, 40) + "？")) return;
          const r = await postJSON("/api/delegation/" + encodeURIComponent(sid) + "/cancel", {}).catch(e => ({ ok: false, error: e.message }));
          if (r.ok) toast("已发送中断请求", "ok"); else toast("中断失败：" + (r.error || ""), "err");
          Views.refreshPanels();
        } }));
    }
    card.appendChild(actions);

    list.appendChild(card);
  }
  wrap.appendChild(list);
}

// ── 历史标签页 ──────────────────────────────────────────────────────────
function renderDelegHistoryTab(wrap, running) {
  if (running.length === 0) {
    wrap.appendChild(el("div", { class: "deleg-empty" }, [
      el("div", { class: "deleg-empty-icon", text: "\uD83D\uDCCB" }),
      el("div", { class: "deleg-empty-title", text: "暂无委派历史" }),
      el("div", { class: "deleg-empty-desc", text: "运行委派任务后，此处将显示执行记录。" }),
      el("button", { class: "btn primary", style: "margin-top:12px;", text: "\u25B6 去执行",
        onclick: () => { _delegActiveTab = "execute"; Views.refreshPanels(); } }),
    ]));
    return;
  }

  // 排序：最新的在前
  const sorted = [...running].sort((a, b) => (b.started_at || "").localeCompare(a.started_at || ""));

  const list = el("div", { class: "card-list", style: "display:flex;flex-direction:column;gap:8px;" });
  for (const rec of sorted) {
    const isDone = rec.status === "done";
    const isError = rec.status === "error";
    const isCancelling = rec.status === "cancelling";
    const card = el("div", { class: "deleg-hist-card" + (isDone ? " deleg-h-done" : "") + (isError ? " deleg-h-err" : "") });

    // 头部
    const head = el("div", { class: "deleg-hist-head" });
    head.appendChild(el("div", { class: "deleg-hist-goal", text: (rec.goal || "").slice(0, 100) }));
    const statusText = isDone ? "\u2705 已完成" : isError ? "\u274C 失败" : isCancelling ? "\u23F3 取消中" : "\u26A1 运行中";
    head.appendChild(el("span", { class: "badge " + (isDone ? "on" : isError ? "off" : "warn"), text: statusText }));
    head.appendChild(el("button", { class: "btn ghost sm", style: "margin-left:auto;", text: "\u21BA 重启", onclick: async () => {
      if (!confirm("整体重启这条委派？")) return;
      const r = await postJSON("/api/delegation/" + encodeURIComponent(rec.id || "") + "/restart", {}).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) toast("已请求整体重启", "ok"); else toast("重启失败：" + (r.error || ""), "err");
      Views.refreshPanels();
    } }));
    card.appendChild(head);

    // 元信息
    const meta = el("div", { class: "deleg-hist-meta" });
    const metaParts = [];
    const subtasks = rec.subtasks || [];
    metaParts.push("子任务：" + subtasks.length + " 个");
    if (rec.started_at) metaParts.push("开始：" + new Date(rec.started_at).toLocaleString());
    if (rec.finished_at) metaParts.push("结束：" + new Date(rec.finished_at).toLocaleString());
    meta.textContent = metaParts.join("  \u00B7  ");
    card.appendChild(meta);

    // 可展开详情
    const detail = el("div", { class: "deleg-hist-detail hidden" });

    // 子任务列表
    if (subtasks.length > 0) {
      const subList = el("div", { class: "deleg-subtask-list" });
      for (const st of subtasks) {
        const stDone = st.status === "done";
        const stItem = el("div", { class: "deleg-subtask-item" + (stDone ? " deleg-st-done" : "") });
        stItem.appendChild(el("div", { class: "deleg-st-header" }, [
          el("span", { class: "deleg-st-idx", text: "#" + st.index }),
          el("span", { class: "deleg-st-task", text: (st.task || "").slice(0, 120) }),
          el("span", { class: "badge " + (stDone ? "on" : "off"), text: stDone ? "完成" : (st.status || "运行中") }),
          el("button", { class: "btn ghost sm", style: "margin-left:auto;", text: "\u21BA 重启分支", onclick: async () => {
            if (!confirm("重启子任务 #" + st.index + "？")) return;
            const r = await postJSON("/api/delegation/" + encodeURIComponent(rec.id || "") + "/restart-branch", { idx: st.index }).catch(e => ({ ok: false, error: e.message }));
            if (r.ok) toast("已请求重启分支 #" + st.index, "ok"); else toast("重启失败：" + (r.error || ""), "err");
            Views.refreshPanels();
          } }),
        ]));
        if (st.finished_at) {
          stItem.appendChild(el("div", { class: "deleg-st-meta muted small", text: "完成：" + new Date(st.finished_at).toLocaleTimeString() }));
        }
        if (st.result) {
          const resultPre = el("pre", { class: "deleg-st-result" });
          resultPre.textContent = (st.result || "").slice(0, 2000);
          stItem.appendChild(resultPre);
        }
        subList.appendChild(stItem);
      }
      detail.appendChild(subList);
    }

    // 最终汇总结果
    if (rec.result) {
      detail.appendChild(el("div", { class: "section-title", style: "font-size:13px;margin-top:10px;", text: "\uD83D\uDCDD 汇总结果" }));
      const resultPre = el("pre", { class: "deleg-st-result" });
      resultPre.textContent = (rec.result || "").slice(0, 4000);
      detail.appendChild(resultPre);
    }

    if (rec.error) {
      detail.appendChild(el("div", { class: "deleg-st-error", text: "错误：" + rec.error }));
    }

    card.appendChild(detail);

    // 展开/收起按钮
    const toggleBtn = el("button", { class: "btn ghost", style: "width:100%;font-size:12px;",
      text: "\uD83D\uDCC2 展开详情", onclick: () => {
        const isHidden = detail.classList.contains("hidden");
        detail.classList.toggle("hidden");
        toggleBtn.textContent = isHidden ? "\uD83D\uDCC1 收起详情" : "\uD83D\uDCC2 展开详情";
      } });
    card.appendChild(toggleBtn);

    list.appendChild(card);
  }
  wrap.appendChild(list);
}

