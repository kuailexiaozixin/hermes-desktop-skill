// @ts-check
/* =====================================================================
 * mcp.js — MCP 面板子模块（服务器信息 + 客户端商店）
 *
 * 本模块只负责 MCP 功能面板的渲染与交互：
 *   - renderMcpPanel      统一面板（服务器子面板 + 客户端商店子面板）
 *   - renderMcpServerInfo 只读展示本应用作为 MCP 服务器的启动命令 / 配置（可复制）
 *
 * 客户端商店的真正逻辑在 static/mcpstore.js（window.initMcpStore），
 * 后端代理在 mcpstore_client.py，服务器信息端点在 routes/mcp_server.py。
 * ===================================================================== */
import { el, toast } from "../dom.js";
import { getJSON, postJSON } from "../api.js";

// 托管状态轮询定时器（每次渲染重置，避免重复轮询）
let _msiPollTimer = null;
// 上次探活结果（跨轮询保留，避免被状态刷新清空）
let _lastProbeText = "";
let _lastProbeClass = "";

export async function renderMcpPanel(body) {
  body.innerHTML = "";
  const wrap = el("div", { class: "mcp-unified" });

  // ── 顶部子面板切换 Tab ──
  const tabs = el("div", { class: "mcp-tabs" });
  const tabServer = el("button", { class: "mcp-tab active",
    text: "🖥 MCP 服务器（本应用作为服务器）", title: "查看本应用作为 MCP 服务器的启动命令与配置（信息可复制）" });
  const tabClient = el("button", { class: "mcp-tab",
    text: "🔌 MCP 客户端（连接外部服务器）", title: "浏览 / 安装 / 管理外部 MCP 服务器" });
  tabs.appendChild(tabServer);
  tabs.appendChild(tabClient);
  wrap.appendChild(tabs);

  // ── 两个子面板容器 ──
  const serverSub = el("div", { class: "mcp-subpanel", id: "mcpServerSub" });
  const clientSub = el("div", { class: "mcp-subpanel mcp-store hidden", id: "mcpClientSub" });
  wrap.appendChild(serverSub);
  wrap.appendChild(clientSub);
  body.appendChild(wrap);

  // 区一：MCP 服务器（只读信息 + 一键复制，便于粘贴到其他 MCP 客户端）
  await renderMcpServerInfo(serverSub);
  // 区二：MCP 客户端商店（浏览目录 / 一键安装 / 启用停用 / 管理外部 MCP 服务器）
  if (window.initMcpStore) window.initMcpStore("mcpClientSub");

  function switchTab(which) {
    const isServer = which === "server";
    tabServer.classList.toggle("active", isServer);
    tabClient.classList.toggle("active", !isServer);
    serverSub.classList.toggle("hidden", !isServer);
    clientSub.classList.toggle("hidden", isServer);
  }
  tabServer.addEventListener("click", () => switchTab("server"));
  tabClient.addEventListener("click", () => switchTab("client"));
  window.__showMcpTab = (which) => switchTab(which || "server");
}

// 只读展示本应用作为 MCP 服务器的能力（不内嵌服务器，仅查状态与启动命令）
async function renderMcpServerInfo(wrap) {
  ensureMcpServerInfoStyle();
  // 每次重新渲染时清理旧轮询，避免重复计时器
  if (_msiPollTimer) { clearInterval(_msiPollTimer); _msiPollTimer = null; }
  wrap.innerHTML = '<div class="msi-card"><div class="msi-title">MCP 服务器（本应用作为服务器）</div>' +
    '<div class="msi-loading">加载中…</div></div>';
  try {
    const d = await getJSON("/api/mcp-server/info");
    if (!d || d.ok !== true) {
      wrap.innerHTML = '<div class="msi-card"><div class="msi-title">MCP 服务器</div>' +
        '<div class="msi-loading">暂无信息</div></div>';
      return;
    }

    wrap.innerHTML = "";
    const card = el("div", { class: "msi-card" });

    // 头部标题 + 状态徽章
    const head = el("div", { class: "msi-head" }, [
      el("div", { class: "msi-title", text: "MCP 服务器（本应用作为服务器）" }),
      el("span", {
        class: "msi-badge " + (d.mcp_available ? "ok" : "warn"),
        text: d.mcp_available ? "已安装 mcp 包" : "未安装 mcp 包（pip install 'mcp'）"
      }),
    ]);
    card.appendChild(head);

    // 传输
    card.appendChild(el("div", { class: "msi-row" }, [
      el("span", { class: "msi-label", text: "传输" }),
      el("span", { text: d.transport || "stdio（独立进程）" }),
    ]));

    // 启动命令（每个命令独立可复制）
    const cmdWrap = el("div", { class: "msi-row" });
    cmdWrap.appendChild(el("span", { class: "msi-label", text: "启动命令" }));
    const cmdList = el("div", { class: "msi-cmd-list" });
    const cmdValues = [d.conversation_bridge_command, d.tool_surface_command].filter(Boolean);
    if (!cmdValues.length) {
      cmdList.appendChild(el("span", { class: "muted", text: "暂无可用命令" }));
    } else {
      for (const c of cmdValues) {
        const row = el("div", { class: "msi-cmd-row" }, [
          el("code", { class: "msi-cmd", text: c }),
          renderCopyBtn(c, "复制这条启动命令"),
        ]);
        cmdList.appendChild(row);
      }
    }
    cmdWrap.appendChild(cmdList);
    card.appendChild(cmdWrap);

    // 外部客户端配置（JSON 可复制）
    if (d.client_config) {
      const cfg = JSON.stringify(d.client_config, null, 2);
      const cfgWrap = el("div", { class: "msi-row" });
      cfgWrap.appendChild(el("span", { class: "msi-label", text: "外部客户端配置" }));
      const cfgBox = el("div", { class: "msi-pre-box" }, [
        renderCopyBtn(cfg, "复制 JSON 配置", "📋 复制配置"),
        el("pre", { class: "msi-pre", text: cfg }),
      ]);
      cfgWrap.appendChild(cfgBox);
      card.appendChild(cfgWrap);
    }

    if (d.note) card.appendChild(el("div", { class: "msi-note", text: d.note }));
    if (d.security) card.appendChild(el("div", { class: "msi-sec", text: d.security }));

    wrap.appendChild(card);

    // ── 应用托管控制区（启动 / 停止 / 探活 + 实时状态）──
    const hostedCard = el("div", { class: "msi-card", "data-msi-hosted": "" });
    wrap.appendChild(hostedCard);
    await renderHostedStatus(hostedCard);
    _msiPollTimer = setInterval(() => renderHostedStatus(hostedCard), 5000);
  } catch (e) {
    if (_msiPollTimer) { clearInterval(_msiPollTimer); _msiPollTimer = null; }
    wrap.innerHTML = '<div class="msi-card"><div class="msi-title">MCP 服务器</div>' +
      '<div class="msi-loading">信息加载失败，请稍后重试</div></div>';
  }
}

// 渲染「应用托管」控制区：实时状态徽章 + 启动 / 停止 / 探活按钮
async function renderHostedStatus(box, preloaded) {
  let status = preloaded;
  if (!status) {
    try { status = await getJSON("/api/mcp-server/status"); }
    catch (_) { status = null; }
  }
  const run = (status && status.running && status.running.length) ? status.running[0] : null;
  const running = !!(run && run.running);
  const ready = !!(status && status.python_ready);

  box.innerHTML = "";
  const head = el("div", { class: "msi-head" }, [
    el("div", { class: "msi-title", text: "应用托管（启动 / 停止 / 探活）" }),
    el("span", {
      class: "msi-badge " + (running ? "ok" : (ready ? "idle" : "warn")),
      text: running ? `运行中 · pid ${run.pid}` : (ready ? "空闲 · 可启动" : "环境未就绪"),
    }),
  ]);
  box.appendChild(head);

  const ctrl = el("div", { class: "msi-ctrl" });
  const btnStart = el("button", { class: "msi-btn primary", text: "▶ 启动工具面" });
  // 注意：el() 会把非 null 的 disabled 一律 setAttribute，故运行时应传 undefined（不设属性）
  const btnStop = el("button", { class: "msi-btn danger", text: "■ 停止", disabled: running ? undefined : true });
  const btnProbe = el("button", { class: "msi-btn", text: "🔍 探活", disabled: running ? undefined : true });
  const probeOut = el("div", { class: _lastProbeClass || "msi-probe", text: _lastProbeText });
  ctrl.append(btnStart, btnStop, btnProbe);
  box.appendChild(ctrl);
  box.appendChild(probeOut);

  btnStart.onclick = async () => {
    btnStart.disabled = true;
    btnStart.textContent = "启动中…";
    try {
      const r = await postJSON("/api/mcp-server/start", { kind: "tool_surface" });
      if (r && r.ok) toast(`已启动工具面 MCP 服务器（pid ${r.pid}）`, "ok");
      else toast("启动失败：" + ((r && r.error) || "未知"), "warn");
    } catch (e) { toast("启动异常：" + e.message, "warn"); }
    btnStart.disabled = false;
    btnStart.textContent = "▶ 启动工具面";
    renderHostedStatus(box);
  };
  btnStop.onclick = async () => {
    btnStop.disabled = true;
    try {
      const r = await postJSON("/api/mcp-server/stop", { kind: "tool_surface" });
      if (r && r.ok) toast("已停止 MCP 服务器", "ok");
      else toast("停止失败：" + ((r && r.error) || "未知"), "warn");
    } catch (e) { toast("停止异常：" + e.message, "warn"); }
    renderHostedStatus(box);
  };
  btnProbe.onclick = async () => {
    btnProbe.disabled = true;
    probeOut.textContent = "探活中…";
    probeOut.className = "msi-probe";
    try {
      const r = await postJSON("/api/mcp-server/probe", { kind: "tool_surface" });
      if (r && r.ok) {
        const si = r.server_info || {};
        _lastProbeText = `✓ 探活通过 · ${si.name || "?"} v${si.version || "?"} · protocol ${r.protocolVersion || ""}`;
        _lastProbeClass = "msi-probe ok";
      } else {
        _lastProbeText = "✗ " + ((r && r.error) || "探活失败");
        _lastProbeClass = "msi-probe err";
      }
    } catch (e) {
      _lastProbeText = "✗ 探活异常：" + e.message;
      _lastProbeClass = "msi-probe err";
    }
    probeOut.textContent = _lastProbeText;
    probeOut.className = _lastProbeClass;
    btnProbe.disabled = false;
  };

  if (!ready) {
    box.appendChild(el("div", {
      class: "msi-note",
      text: "未找到含工具面 MCP 模块（agent.transports.hermes_tools_mcp_server）的 python，无法托管启动。请检查应用 venv 环境。",
    }));
  }
  if (status && status.note) {
    box.appendChild(el("div", { class: "msi-note", text: status.note }));
  }
}

// 渲染一个复制小按钮
function renderCopyBtn(text, title, label) {
  const btn = el("button", {
    class: "msi-copy",
    title: title || "复制",
    text: label || "📋",
  });
  btn.onclick = async () => {
    const ok = await copyText(text);
    if (ok) toast("已复制到剪贴板", "ok");
    else toast("复制失败，请手动选择文本复制", "warn");
  };
  return btn;
}

// 复制到剪贴板（优先 Clipboard API，降级 execCommand）
async function copyText(text) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (_) {}
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    return ok;
  } catch (_) {
    return false;
  }
}

let _msiStyleDone = false;
function ensureMcpServerInfoStyle() {
  if (_msiStyleDone) return;
  _msiStyleDone = true;
  const css = [
    ".msi-card{border:1px solid var(--border-strong,#cbd5e1);border-radius:14px;padding:16px;margin-bottom:18px;background:var(--bg-card,#fff);box-shadow:0 1px 3px rgba(15,23,42,.07);}",
    ".msi-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px;}",
    ".msi-title{font-weight:700;font-size:14px;color:var(--text-primary,#0f172a);}",
    ".msi-badge{font-size:11px;padding:2px 9px;border-radius:999px;}",
    ".msi-badge.ok{background:#dcfce7;color:#166534;}",
    ".msi-badge.warn{background:#fef3c7;color:#92400e;}",
    ".msi-row{display:flex;gap:12px;align-items:flex-start;margin:8px 0;font-size:13px;color:var(--text-secondary,#64748b);}",
    ".msi-label{flex:0 0 96px;color:var(--text-tertiary,#94a3b8);font-size:12px;padding-top:2px;}",
    ".msi-cmd{display:block;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;background:var(--bg-muted,#f1f5f9);border:1px solid var(--border,#e2e8f0);border-radius:8px;padding:4px 8px;margin:2px 0;color:var(--text-primary,#0f172a);white-space:pre-wrap;}",
    ".msi-pre{margin:0;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;background:var(--bg-muted,#f1f5f9);border:1px solid var(--border,#e2e8f0);border-radius:8px;padding:8px 10px;max-width:440px;white-space:pre-wrap;color:var(--text-primary,#0f172a);}",
    ".msi-note{margin-top:10px;font-size:12px;line-height:1.7;color:var(--text-secondary,#64748b);}",
    ".msi-sec{margin-top:6px;font-size:11.5px;line-height:1.7;color:#b45309;}",
    ".msi-loading{font-size:13px;color:var(--text-tertiary,#94a3b8);}",
    ".msi-cmd-list{display:flex;flex-direction:column;gap:6px;}",
    ".msi-cmd-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}",
    ".msi-cmd{flex:1;min-width:260px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;background:var(--bg-muted,#f1f5f9);border:1px solid var(--border,#e2e8f0);border-radius:8px;padding:5px 8px;color:var(--text-primary,#0f172a);white-space:pre-wrap;}",
    ".msi-pre-box{display:flex;flex-direction:column;gap:6px;}",
    ".msi-pre{margin:0;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;background:var(--bg-muted,#f1f5f9);border:1px solid var(--border,#e2e8f0);border-radius:8px;padding:8px 10px;max-width:440px;white-space:pre-wrap;color:var(--text-primary,#0f172a);}",
    ".msi-copy{padding:3px 8px;border-radius:6px;border:1px solid var(--border,#e2e8f0);background:var(--bg-elev,#fff);color:var(--text-secondary,#64748b);font-size:11.5px;cursor:pointer;white-space:nowrap;}",
    ".msi-copy:hover{border-color:var(--accent,#2563eb);color:var(--accent,#2563eb);}",
    ".msi-copy-label{display:none;}",
    ".msi-badge.idle{background:#e0f2fe;color:#075985;}",
    ".msi-ctrl{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0;}",
    ".msi-btn{padding:5px 12px;border-radius:8px;border:1px solid var(--border,#e2e8f0);background:var(--bg-elev,#fff);color:var(--text-primary,#0f172a);font-size:12.5px;cursor:pointer;}",
    ".msi-btn:hover{border-color:var(--accent,#2563eb);color:var(--accent,#2563eb);}",
    ".msi-btn:disabled{opacity:.45;cursor:not-allowed;}",
    ".msi-btn.primary{background:var(--accent,#2563eb);border-color:var(--accent,#2563eb);color:#fff;}",
    ".msi-btn.primary:hover{background:#1d4ed8;color:#fff;}",
    ".msi-btn.danger{border-color:#f87171;color:#dc2626;}",
    ".msi-btn.danger:hover:not(:disabled){background:#fef2f2;border-color:#ef4444;color:#dc2626;}",
    ".msi-probe{margin-top:4px;font-size:12px;color:var(--text-tertiary,#94a3b8);min-height:16px;}",
    ".msi-probe.ok{color:#166534;}",
    ".msi-probe.err{color:#dc2626;}"
  ].join("\n");
  const st = document.createElement("style");
  st.id = "mcp-server-info-style";
  st.textContent = css;
  document.head.appendChild(st);
}
