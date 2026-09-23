// @ts-check
/* =====================================================================
 * channels.js — 远程渠道（进程内 IM 桥）视图：连接/断开/测试 + 实时消息流水
 * 自包含：仅依赖叶子模块（dom/api），不反向依赖其他视图模块。
 * ===================================================================== */
import { $, el, toast } from "./dom.js";
import { getJSON, postJSON } from "./api.js";

let _chStatusTimer = null, _chEventsTimer = null;

async function renderChannelsView() {
  const v = $("#view-channels"); if (!v) return;
  v.innerHTML = "";
  const sp = el("div", { class: "app-view-body" });
  v.appendChild(sp);
  sp.appendChild(el("div", { class: "section-title", text: "远程渠道（进程内 IM 桥）" }));
  sp.appendChild(el("div", { class: "muted small", text: "智能体在桌面进程内直跑；本桥用标准库直连 IM 平台——Telegram 纯轮询，飞书/企微/钉钉/Slack/Discord 用出站 Webhook + 本地推送接收器。QQ 官方 Bot API v2 与微信 Hermes iLink 已进程内直连实装。" }));

  const [d, st] = await Promise.all([
    getJSON("/api/channels").catch(() => ({ ok: false, channels: [] })),
    getJSON("/api/channels/status").catch(() => ({ ok: false, connectors: [] })),
  ]);
  if (!st || !st.ok) { sp.appendChild(el("div", { class: "muted", text: "桥状态加载失败" })); return; }

  // —— 实时消息流水 ——
  const eventsBox = el("div", { class: "panel" }, [
    el("div", { class: "cr-title", text: "实时消息流水" }),
    el("div", { class: "muted small", text: "入站消息 → 进程内 Agent → 回推平台" }),
    el("div", { id: "ch-events", class: "ch-events", style: "max-height:200px;overflow:auto;" }),
  ]);
  sp.appendChild(eventsBox);

  const savedMap = {};
  for (const c of (d.channels || [])) savedMap[c.id] = c.config || {};

  // 搜索框
  let _chFilter = "";
  const chSearch = el("input", { class: "form-input", style: "margin-bottom:10px;", placeholder: "搜索渠道名称…",
    oninput: () => { _chFilter = chSearch.value.trim().toLowerCase(); applyChFilter(); } });
  sp.appendChild(chSearch);
  const grid = el("div", { class: "ch-grid" });
  sp.appendChild(grid);
  function applyChFilter() {
    for (const card of grid.querySelectorAll(".ch-card")) {
      const txt = (card.dataset.search || "").toLowerCase();
      card.style.display = !_chFilter || txt.includes(_chFilter) ? "" : "none";
    }
    let noResult = grid.querySelector(".ch-no-result");
    const visible = grid.querySelectorAll('.ch-card[style*="display"]:not([style*="display: none"])').length > 0
      || !_chFilter;
    if (!visible && _chFilter) {
      if (!noResult) {
        noResult = el("div", { class: "muted ch-no-result", style: "padding:14px;text-align:center;", text: "未找到匹配的渠道" });
        grid.appendChild(noResult);
      }
      noResult.style.display = "";
    } else if (noResult) {
      noResult.style.display = "none";
    }
  }
  for (const c of (st.connectors || [])) {
    const saved = savedMap[c.cid] || {};
    const card = el("div", { class: "ch-card" });
    card.dataset.cid = c.cid;
    card.dataset.search = (c.label || "") + " " + (c.name || "") + " " + (c.desc || "");
    card.appendChild(el("div", { class: "ch-head" }, [
      el("span", { class: "ch-icon", text: c.icon }),
      el("div", { class: "ch-name", text: c.label }),
      el("span", { class: "badge " + (c.connected ? "on" : "off"),
        text: c.connected ? "已连接" : (c.needs_bridge ? "需桥接" : "未连接") }),
    ]));
    card.appendChild(el("div", { class: "muted small", text: c.desc }));

    if (c.needs_bridge) {
      card.appendChild(el("div", { class: "warn small", style: "color:#e6a23c;",
        text: "该渠道需先部署外部桥接服务（Docker REST）；QQ 官方与微信 iLink 已进程内直连实装。" }));
      grid.appendChild(card); continue;
    }

    const inputs = {};
    for (const f of (c.fields || [])) {
      const inp = el("input", { class: "form-input", placeholder: f.placeholder || "" });
      inp.value = saved[f.key] || "";
      if (f.secret) inp.type = "password";
      inputs[f.key] = inp;
      card.appendChild(el("div", { class: "field" }, [el("label", { text: f.label }), inp]));
    }

    if (c.connected && c.webhook_url) {
      const wu = el("input", { class: "form-input", value: c.webhook_url });
      wu.readOnly = true;
      card.appendChild(el("div", { class: "field" }, [
        el("label", { text: "回调 URL（填到平台事件订阅）" }), wu ]));
    }

    const actions = el("div", { class: "actions-row" });
    // 微信：一键扫码登录（推荐，免手填 account_id / token）
    if (c.cid === "wechat" && !c.connected) {
      actions.appendChild(el("button", { class: "btn primary",
        text: "📷 扫码登录（推荐）", onclick: () => openWechatQrModal(c, inputs) }));
    }
    actions.appendChild(el("button", { class: "btn " + (c.connected ? "primary" : (c.cid === "wechat" ? "ghost" : "primary")),
      "data-role": "connect",
      text: c.connected ? "断开" : (c.cid === "wechat" ? "手动连接" : "连接"), onclick: async () => {
        if (c.connected) {
          const r = await postJSON("/api/channels/" + c.cid + "/disconnect", {})
            .catch(e => ({ ok: false, error: e.message }));
          if (r.ok) { toast("已断开", "ok"); renderChannelsView(); }
          else toast("断开失败：" + (r.error || ""), "err");
        } else {
          await connectChannel(c, inputs);
          renderChannelsView();
        }
      } }));
    if (c.connected) {
      actions.appendChild(el("button", { class: "btn ghost", text: "发送测试", onclick: async () => {
        const r = await postJSON("/api/channels/" + c.cid + "/test",
          { text: "测试：Hello from Hermes Desktop!" })
          .catch(e => ({ ok: false, error: e.message }));
        toast(r.ok ? "测试已发送" : ("失败：" + (r.error || "")), r.ok ? "ok" : "err");
      } }));
    }
    card.appendChild(actions);
    grid.appendChild(card);
  }
  sp.appendChild(grid);

  if (_chStatusTimer) clearInterval(_chStatusTimer);
  if (_chEventsTimer) clearInterval(_chEventsTimer);
  _chStatusTimer = setInterval(() => {
    getJSON("/api/channels/status").then(s => { if (s && s.ok) updateChannelBadges(s.connectors); });
  }, 4000);
  _chEventsTimer = setInterval(refreshChannelEvents, 2000);
  refreshChannelEvents();
}

/** 保存配置并发起连接（被「连接」按钮与微信扫码成功后复用）。 */
async function connectChannel(c, inputs) {
  const config = {};
  for (const f of (c.fields || [])) config[f.key] = (inputs[f.key].value || "").trim();
  const r = await postJSON("/api/channels/" + c.cid, { enabled: true, ...config })
    .catch(e => ({ ok: false, error: e.message }));
  if (!r.ok) { toast("保存失败：" + (r.error || ""), "err"); return r; }
  const rc = await postJSON("/api/channels/" + c.cid + "/connect", { config })
    .catch(e => ({ ok: false, error: e.message }));
  if (rc.ok) toast("已连接", "ok");
  else toast("连接失败：" + (rc.error || ""), "err");
  return rc;
}

/* 微信 iLink 一键扫码登录弹窗：
   点击「扫码登录」→ 弹出二维码 → 后台轮询扫码状态 →
   确认后自动填好账号/凭证并连接，无需手动填写。 */
async function openWechatQrModal(c, inputs) {
  let closed = false;
  let pollTimer = null;
  let sid = null;

  const statusEl = el("div", { class: "qr-status muted small", text: "正在生成二维码…" });
  const imgEl = el("img", { class: "qr-image", alt: "微信登录二维码", style: "display:none;" });
  const fallbackEl = el("div", { class: "qr-fallback", style: "display:none;" });
  const qrBox = el("div", { class: "qr-box" }, [imgEl, fallbackEl]);

  const rescanBtn = el("button", { class: "btn ghost", text: "重新扫码", style: "display:none;" });
  const cancelBtn = el("button", { class: "btn", text: "取消" });

  const mask = el("div", { class: "mask" }, [
    el("div", { class: "modal", style: "width:360px;" }, [
      el("div", { class: "modal-head" }, [
        el("div", { class: "modal-title", text: "微信扫码登录" }),
        el("button", { class: "btn icon", text: "×", onclick: () => closeModal() }),
      ]),
      el("div", { class: "approval-body", style: "text-align:center;" }, [
        el("div", { class: "muted small", style: "margin-bottom:10px;",
          text: "请用微信扫描下方二维码，在手机上确认后，即可自动完成连接。" }),
        qrBox,
        statusEl,
      ]),
      el("div", { class: "modal-foot" }, [rescanBtn, cancelBtn]),
    ]),
  ]);
  mask.addEventListener("click", (e) => { if (e.target === mask) closeModal(); });
  document.body.appendChild(mask);

  function closeModal() {
    if (closed) return;
    closed = true;
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    if (sid) postJSON("/api/channels/wechat/qr/cancel", { sid }).catch(() => {});
    mask.remove();
  }
  cancelBtn.onclick = () => closeModal();

  function showQr(data) {
    imgEl.style.display = "none"; fallbackEl.style.display = "none";
    if (data.qr_image) {
      imgEl.src = data.qr_image; imgEl.style.display = "";
    } else if (data.qrcode_url && /^(https?:|data:)/.test(data.qrcode_url)) {
      imgEl.src = data.qrcode_url; imgEl.style.display = "";
    } else {
      fallbackEl.style.display = "";
      fallbackEl.textContent = "请复制以下内容，在微信中手动登录：\n" + (data.scan_data || "");
    }
  }

  function startPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
      if (closed || !sid) return;
      const s = await getJSON("/api/channels/wechat/qr/status?sid=" + encodeURIComponent(sid))
        .catch(() => ({}));
      if (closed || !s || !s.ok) return;
      const st = s.status;
      if (st === "scaned") {
        statusEl.textContent = s.message || "已扫码，请在微信中确认…";
      } else if (st === "confirmed") {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
        statusEl.textContent = "登录成功，正在连接…";
        const cred = s.credentials || {};
        if (inputs["api_base"]) inputs["api_base"].value = cred.base_url || inputs["api_base"].value;
        if (inputs["account_id"]) inputs["account_id"].value = cred.account_id || "";
        if (inputs["token"]) inputs["token"].value = cred.token || "";
        closeModal();
        const rc = await connectChannel(c, inputs);
        if (rc && rc.ok) { toast("微信已连接", "ok"); renderChannelsView(); }
        else toast("已登录，但连接失败：" + ((rc && rc.error) || ""), "err");
      } else if (st === "expired" || st === "timeout" || st === "error" || st === "cancelled") {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
        statusEl.textContent = s.message || "扫码已结束";
        statusEl.className = "qr-status warn small";
        rescanBtn.style.display = "";
      } else if (s.message) {
        statusEl.textContent = s.message;
      }
    }, 1500);
  }

  async function startLogin() {
    statusEl.className = "qr-status muted small";
    statusEl.textContent = "正在生成二维码…";
    rescanBtn.style.display = "none";
    const r = await postJSON("/api/channels/wechat/qr/start", {})
      .catch(e => ({ ok: false, error: e.message }));
    if (closed) return;
    if (!r.ok) {
      statusEl.className = "qr-status warn small";
      statusEl.textContent = "生成失败：" + (r.error || "未知错误");
      rescanBtn.style.display = "";
      return;
    }
    sid = r.sid;
    showQr(r);
    statusEl.textContent = r.message || "请使用微信扫描下方二维码";
    startPolling();
  }

  rescanBtn.onclick = () => { if (!closed) startLogin(); };
  await startLogin();
}

function updateChannelBadges(connectors) {
  for (const c of (connectors || [])) {
    const card = document.querySelector('#view-channels .ch-card[data-cid="' + c.cid + '"]');
    if (!card) continue;
    const badge = card.querySelector(".badge");
    if (badge) {
      badge.textContent = c.connected ? "已连接" : (c.needs_bridge ? "需桥接" : "未连接");
      badge.className = "badge " + (c.connected ? "on" : "off");
    }
    const btn = card.querySelector('.btn[data-role="connect"]');
    if (btn && !c.needs_bridge) btn.textContent = c.connected ? "断开" : "连接";
  }
}

async function refreshChannelEvents() {
  const box = document.getElementById("ch-events"); if (!box) return;
  const d = await getJSON("/api/channels/events?limit=30").catch(() => ({ events: [] }));
  const evs = (d && d.events) || [];
  box.innerHTML = "";
  if (!evs.length) { box.appendChild(el("div", { class: "muted small", text: "（暂无消息）" })); return; }
  for (const e of evs) {
    const map = { in: ["入站", "#7fd1ff"], out: ["出站", "#9fe8c8"],
                  error: ["错误", "#ff9f9f"], system: ["系统", "#c9c9c9"] };
    const [tag, color] = map[e.direction] || ["·", "#c9c9c9"];
    box.appendChild(el("div", { class: "ch-ev",
      style: "font-size:12px;padding:3px 0;border-bottom:1px solid #1c2433;color:" + color + ";" }, [
      el("span", { text: "[" + tag + "] " }),
      el("span", { class: "muted", text: (e.cid || "") + " " }),
      el("span", { text: (e.text || "").slice(0, 120) }),
    ]));
  }
}

export { renderChannelsView, updateChannelBadges, refreshChannelEvents };
