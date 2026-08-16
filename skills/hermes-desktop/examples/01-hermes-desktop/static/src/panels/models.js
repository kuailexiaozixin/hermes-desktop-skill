// @ts-check
/* =====================================================================
 * models.js — models 面板子模块
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { State } from "../state.js";
import { getJSON, postJSON, delJSON, parseSSE } from "../api.js";
import * as Chat from "../chat.js";
import * as Views from "../views.js";
// ------------------------------------------------------------------ 模型面板
export async function renderModelsPanel(body) {
  const data = await getJSON("/api/models");
  const vendors = data.vendors || {};
  const wrap = el("div", { class: "panel" });

  if (data.web && (data.web.data || data.web).backend) {
    const ws = (data.web && data.web.data) || data.web || {};
    wrap.appendChild(el("div", { class: "row-between" }, [
      el("div", {}, [
        el("div", { class: "label", text: "联网检索后端" }),
        el("div", { class: "desc", text: `后端：${ws.backend}` + (ws.ready ? "（已就绪）" : `（需环境变量 ${ws.key_env}）`) }),
      ]),
      el("span", { class: "badge " + (ws.ready ? "on" : "warn"), text: ws.ready ? "就绪" : "缺密钥" }),
    ]));
  }

  wrap.appendChild(el("div", { class: "section-title", text: "模型（按厂商分组）" }));
  const list = el("div", { class: "card-list" });

  // 按 vendor 分组（Provider 实体视图：一个厂商下挂多个模型）
  const groups = {};
  for (const m of data.items || []) {
    const vid = m.vendor || "未分组";
    (groups[vid] = groups[vid] || []).push(m);
  }
  for (const [vid, ms] of Object.entries(groups)) {
    const v = (vendors[vid]) || {};
    const section = el("div", { class: "vendor-group" });
    section.appendChild(el("div", { class: "vg-head" }, [
      el("span", { class: "vg-title", text: v.label || vid }),
      el("span", { class: "badge", text: `${ms.length} 个模型` }),
      el("button", { class: "btn ghost sm", text: "＋ 添加模型",
        onclick: () => openModelEditor(wrap, data, vid, null) }),
    ]));
    const rows = el("div", { class: "vg-rows" });
    for (const m of ms) rows.appendChild(buildModelRow(m, data, wrap));
    section.appendChild(rows);
    list.appendChild(section);
  }
  wrap.appendChild(list);

  // 模型编辑器（新增/编辑共用，保存走增量 upsert，不再全量替换）
  openModelEditor(wrap, data, "", null);
  body.appendChild(wrap);
}

// 单行模型：标题/徽章 + 操作（设为当前 / 编辑 / 测试连通性 / 删除）
function buildModelRow(m, data, wrap) {
  const isActive = m.id === data.active;
  return el("div", { class: "card-row", dataset: { modelId: m.id } }, [
    el("div", { class: "cr-main" }, [
      el("div", { class: "cr-title" }, [
        el("span", { text: m.model || m.id }),
        m.has_key ? el("span", { class: "badge on", text: "已配密钥" }) : el("span", { class: "badge off", text: "无密钥" }),
        isActive ? el("span", { class: "badge on", text: "当前" }) : null,
      ]),
      el("div", { class: "cr-desc", text: m.base_url || ((data.vendors && data.vendors[m.vendor] && data.vendors[m.vendor].base_url) || "") }),
    ]),
    el("div", { class: "cr-actions" }, [
      el("button", { class: "btn ghost sm", text: "设为当前", onclick: async () => {
        const r = await postJSON("/api/models/upsert",
          { model: { id: m.id, vendor: m.vendor, model: m.model, base_url: m.base_url, api_key: "" }, set_active: true })
          .catch((e) => ({ ok: false, error: e.message }));
        if (r.ok) { toast("已设为当前模型", "ok"); Views.refreshPanels(); Chat.loadToolbarSelects(); }
        else toast("操作失败：" + (r.error || ""), "err");
      } }),
      el("button", { class: "btn ghost sm", text: "编辑", onclick: () => openModelEditor(wrap, data, m.vendor || "", m) }),
      el("button", { class: "btn ghost sm", text: "测试", onclick: async () => {
        toast("正在测试连通性…", "ok");
        const r = await postJSON("/api/models/test", { vendor: m.vendor, base_url: m.base_url, api_key: "", model: m.model })
          .catch((e) => ({ ok: false, error: e.message }));
        if (r.ok) toast("连接成功：" + (r.detail || ""), "ok");
        else toast("连接失败：" + ((r.detail) || r.error || ""), "err");
      } }),
      el("button", { class: "btn ghost sm danger", text: "删除", onclick: async () => {
        if (!confirm(`确定删除模型 ${m.model || m.id}？`)) return;
        const r = await postJSON("/api/models/remove", { id: m.id }).catch((e) => ({ ok: false, error: e.message }));
        if (r.ok) { toast("已删除", "ok"); Views.refreshPanels(); Chat.loadToolbarSelects(); }
        else toast("删除失败：" + (r.error || ""), "err");
      } }),
    ]),
  ]);
}

// 模型编辑器：新增 / 编辑，保存走增量 upsert（llm.json 仍为扁平存储）
function openModelEditor(wrap, data, vid, existing) {
  const prev = wrap.querySelector(".model-editor");
  if (prev) prev.remove();
  const vendors = data.vendors || {};

  // ── 基础字段 ──
  const vsel = el("select", {},
    [el("option", { value: "", text: "选择厂商…" }),
     ...Object.entries(vendors).map(([k, v]) => el("option", { value: k, text: v.label || k }))]);

  // 模型名 + 一键检测按钮
  const mselWrap = el("div", { class: "model-inp-wrap", style: "display:flex;gap:6px;align-items:center;" });
  const msel = el("input", { placeholder: "模型名，如 gpt-5.1 / claude-opus-4-7", style: "flex:1;" });
  const detectBtn = el("button", { class: "btn ghost sm", text: "🔍 检测",
    title: "从 API 端点自动检测可用模型列表",
    onclick: async () => {
      const baseUrl = getBurlValue();
      const apiKey = akey.value.trim();
      if (!baseUrl) { toast("请先选择厂商或填写 Base URL", "err"); return; }
      if (!apiKey) { toast("请先填写 API Key", "err"); return; }
      detectBtn.disabled = true; detectBtn.textContent = "检测中…";
      const r = await postJSON("/api/models/detect", { base_url: baseUrl, api_key: apiKey })
        .catch(e => ({ ok: false, error: e.message }));
      detectBtn.disabled = false; detectBtn.textContent = "🔍 检测";
      if (!r.ok) { toast("检测失败：" + (r.error || ""), "err"); return; }
      const models = r.models || [];
      if (!models.length) { toast("未检测到可用模型", "err"); return; }
      showModelPicker(models, (selected) => {
        msel.value = selected;
        autoDetectCapabilities();
      });
    } });
  mselWrap.appendChild(msel);
  mselWrap.appendChild(detectBtn);

  // ── Base URL：DeepSeek 用下拉选择，其他厂商用文本输入 ──
  const burlWrap = el("div", { style: "display:flex;gap:6px;align-items:center;flex:1;" });
  const burlInp = el("input", { placeholder: "Base URL（留空用厂商默认）", style: "flex:1;" });
  const burlSel = el("select", { style: "flex:1;" });
  function getBurlValue() {
    if (burlSel.parentNode === burlWrap) return burlSel.value;
    return burlInp.value.trim() || (vendors[vsel.value] && vendors[vsel.value].base_url) || "";
  }
  function setBurlValue(val) {
    if (burlSel.parentNode === burlWrap) { burlSel.value = val; }
    else { burlInp.value = val || ""; }
  }
  function updateBurlField() {
    const v = vendors[vsel.value];
    burlWrap.innerHTML = "";
    if (vsel.value === "deepseek" && v && v.alt_base_urls) {
      burlSel.innerHTML = "";
      for (const url of v.alt_base_urls) {
        const label = url === "https://api.deepseek.com"
          ? "https://api.deepseek.com（兼容 OpenAI）"
          : url === "https://api.deepseek.com/anthropic"
          ? "https://api.deepseek.com/anthropic（兼容 Anthropic）"
          : url;
        burlSel.appendChild(el("option", { value: url, text: label }));
      }
      burlSel.value = v.base_url || "https://api.deepseek.com";
      burlWrap.appendChild(burlSel);
    } else {
      burlInp.value = (v && v.base_url) || "";
      burlInp.placeholder = (v && v.base_url) ? "Base URL（已自动填充）" : "Base URL（留空用厂商默认）";
      burlWrap.appendChild(burlInp);
    }
  }

  // API Key + 眼睛按钮
  const akeyWrap = el("div", { class: "toolcfg-inp-wrap", style: "display:flex;gap:4px;align-items:center;" });
  const akey = el("input", { placeholder: "API Key（留空=保持既有）", type: "password", style: "flex:1;" });
  const eyeBtn = el("button", { class: "btn icon", type: "button", text: "👁",
    title: "显示/隐藏 API Key",
    onclick: (e) => {
      e.preventDefault();
      const isPw = akey.getAttribute("type") === "password";
      akey.setAttribute("type", isPw ? "text" : "password");
      eyeBtn.textContent = isPw ? "👁‍🗨" : "👁";
    } });
  akeyWrap.appendChild(akey);
  akeyWrap.appendChild(eyeBtn);

  // ── 厂商切换时更新 Base URL 字段 ──
  vsel.addEventListener("change", updateBurlField);

  if (existing) {
    vsel.value = existing.vendor || "";
    msel.value = existing.model || existing.id || "";
  } else if (vid) {
    vsel.value = vid;
  }
  updateBurlField();
  if (existing && existing.base_url) setBurlValue(existing.base_url);

  // ── 模型能力配置 ──
  const capTools = existing ? !!(existing.tools) : true;
  const capVision = existing ? !!(existing.vision) : false;
  const capThinking = existing ? !!(existing.thinking) : false;
  const capCustom = existing ? !!(existing.custom_protocol) : false;
  const capInputMax = existing ? (existing.input_max_tokens || "") : "";
  const capOutputMax = existing ? (existing.output_max_tokens || "") : "";
  const capReasoning = existing ? (existing.reasoning_effort || "") : "";

  const capToolsCb = el("input", { type: "checkbox", checked: capTools });
  const capVisionCb = el("input", { type: "checkbox", checked: capVision });
  const capThinkingCb = el("input", { type: "checkbox", checked: capThinking });
  const capCustomCb = el("input", { type: "checkbox", checked: capCustom });

  const capInputMaxSel = el("select", {},
    [el("option", { value: "", text: "使用提供商默认" }),
     el("option", { value: "32000", text: "32K" }),
     el("option", { value: "64000", text: "64K" }),
     el("option", { value: "128000", text: "128K" }),
     el("option", { value: "256000", text: "256K" })]);
  if (capInputMax) capInputMaxSel.value = String(capInputMax);

  const capOutputMaxSel = el("select", {},
    [el("option", { value: "", text: "使用提供商默认" }),
     el("option", { value: "8000", text: "8K" }),
     el("option", { value: "16000", text: "16K" }),
     el("option", { value: "32000", text: "32K" }),
     el("option", { value: "64000", text: "64K" })]);
  if (capOutputMax) capOutputMaxSel.value = String(capOutputMax);

  const capReasoningSel = el("select", {},
    [el("option", { value: "", text: "使用模型默认" }),
     el("option", { value: "high", text: "高（更强推理，更慢）" }),
     el("option", { value: "low", text: "低（更快，节省 Token）" })]);
  if (capReasoning) capReasoningSel.value = capReasoning;

  // ── DeepSeek 高级参数 ──
  const dsTemp = existing ? (existing.temperature || "") : "";
  const dsTopP = existing ? (existing.top_p || "") : "";
  const dsTopLogprobs = existing ? (existing.top_logprobs || "") : "";
  const dsStop = existing ? (existing.stop_sequences || "") : "";
  const dsRespFmt = existing ? (existing.response_format || "") : "";
  const dsWebSearch = existing ? !!(existing.web_search) : false;

  const dsTempInp = el("input", { type: "number", min: "0", max: "2", step: "0.1",
    placeholder: "0.0~2.0", style: "width:70px;", value: dsTemp });
  const dsTopPInp = el("input", { type: "number", min: "0", max: "1", step: "0.05",
    placeholder: "0.0~1.0", style: "width:70px;", value: dsTopP });
  const dsTopLogprobsSel = el("select", { style: "width:70px;" },
    [el("option", { value: "", text: "关闭" }),
     ...Array.from({length: 21}, (_, i) => el("option", { value: String(i), text: String(i) }))]);
  if (dsTopLogprobs) dsTopLogprobsSel.value = dsTopLogprobs;
  const dsStopInp = el("input", { placeholder: "多个用逗号分隔", style: "width:160px;", value: dsStop });
  const dsRespFmtSel = el("select", { style: "width:100px;" },
    [el("option", { value: "", text: "纯文本" }),
     el("option", { value: "json_object", text: "JSON 对象" })]);
  if (dsRespFmt) dsRespFmtSel.value = dsRespFmt;
  const dsWebSearchCb = el("input", { type: "checkbox", checked: dsWebSearch });

      // ── 模型工具类型列表（显示该模型支持的工类型，非 Hermes 系统工具） ──
  const toolCapWrap = el("div", { style: "margin-top:8px;font-size:12px;display:none;" });
  let lastToolCaps = null;
  function updateToolCapabilities() {
    if (!capToolsCb.checked || !lastToolCaps) { toolCapWrap.style.display = "none"; return; }
    toolCapWrap.style.display = "block";
    const items = lastToolCaps.map(t => {
      const icon = t.supported ? "✅" : "❌";
      return `<span style="display:inline-flex;align-items:center;gap:3px;margin:2px 8px 2px 0;white-space:nowrap;">${icon} ${t.name}</span>`;
    }).join("");
    toolCapWrap.innerHTML = `<div style="color:var(--text-dim);margin-bottom:4px;">模型支持的工类型：</div><div>${items}</div>`;
  }
  capToolsCb.addEventListener("change", updateToolCapabilities);

  // ── 自动检测模型能力 ──
  // ── 自动检测模型能力 ──
  let detectTimer = null;
  async function autoDetectCapabilities() {
    const model = msel.value.trim();
    const baseUrl = getBurlValue();
    const apiKey = akey.value.trim();
    if (!model || !baseUrl || !apiKey) return;
    capVisionCb.disabled = true;
    capToolsCb.disabled = true;
    const r = await postJSON("/api/models/check-capabilities", {
      base_url: baseUrl, api_key: apiKey, model: model, vendor: vsel.value
    }).catch(e => ({ ok: false, error: e.message }));
    capVisionCb.disabled = false;
    capToolsCb.disabled = false;
    if (r.ok) {
      if (r.vision !== undefined) capVisionCb.checked = !!r.vision;
      if (r.tools !== undefined) capToolsCb.checked = !!r.tools;
      if (r.tool_capabilities) { lastToolCaps = r.tool_capabilities; }
      updateToolCapabilities();
    }
  }
  msel.addEventListener("input", () => {
    clearTimeout(detectTimer);
    detectTimer = setTimeout(autoDetectCapabilities, 600);
  });

  // ── 能力配置面板 ──
  const capSection = el("div", { class: "panel", style: "margin-top:12px;border:1px solid var(--border);border-radius:10px;padding:14px;" }, [
    el("div", { class: "section-title", text: "⚙ 模型能力配置" }),
    el("div", { style: "display:flex;flex-wrap:wrap;gap:12px;margin-bottom:10px;" }, [
      el("label", { class: "field-inline", style: "gap:4px;" }, [capToolsCb, el("span", { text: "工具调用" }), el("span", { style: "font-size:11px;color:var(--text-faint);", text: "（自动检测）" })]),
      el("label", { class: "field-inline", style: "gap:4px;" }, [capVisionCb, el("span", { text: "图片输入" }), el("span", { style: "font-size:11px;color:var(--text-faint);", text: "（自动检测）" })]),
      el("label", { class: "field-inline", style: "gap:4px;" }, [capThinkingCb, el("span", { text: "思考模式" })]),
      el("label", { class: "field-inline", style: "gap:4px;" }, [capCustomCb, el("span", { text: "自定义协议" })]),
    ]),
    toolCapWrap,
    el("div", { style: "display:flex;flex-wrap:wrap;gap:16px;" }, [
      el("div", { class: "field-inline" }, [el("label", { text: "输入上下文长度" }), capInputMaxSel]),
      el("div", { class: "field-inline" }, [el("label", { text: "输出上下文长度" }), capOutputMaxSel]),
      el("div", { class: "field-inline" }, [el("label", { text: "推理强度" }), capReasoningSel]),
    ]),
    el("div", { style: "display:flex;flex-wrap:wrap;gap:16px;margin-top:8px;padding-top:8px;border-top:1px solid var(--border);" }, [
      el("div", { class: "field-inline" }, [el("label", { text: "Temperature" }), dsTempInp]),
      el("div", { class: "field-inline" }, [el("label", { text: "Top P" }), dsTopPInp]),
      el("div", { class: "field-inline" }, [el("label", { text: "Top Logprobs" }), dsTopLogprobsSel]),
      el("div", { class: "field-inline" }, [el("label", { text: "停止序列" }), dsStopInp]),
      el("div", { class: "field-inline" }, [el("label", { text: "输出格式" }), dsRespFmtSel]),
      el("label", { class: "field-inline", style: "gap:4px;" }, [dsWebSearchCb, el("span", { text: "内置联网搜索" })]),
    ]),
  ]);

  // ── 构建编辑器 ──
  const editor = el("div", { class: "panel model-editor" }, [
    el("div", { class: "section-title", text: existing ? "编辑模型" : "新增模型" }),
    el("div", { class: "field" }, [el("label", { text: "厂商" }), vsel]),
    el("div", { class: "field" }, [el("label", { text: "模型" }), mselWrap]),
    el("div", { class: "field" }, [el("label", { text: "Base URL" }), burlWrap]),
    el("div", { class: "field" }, [el("label", { text: "API Key" }), akeyWrap]),
    capSection,
    el("div", { class: "chips-row", style: "margin-top:8px;" }, [
      el("button", { class: "btn primary", text: existing ? "保存修改" : "添加模型", onclick: async () => {
        const v = vsel.value; const model = msel.value.trim();
        if (!v || !model) { toast("请选择厂商并填写模型名", "err"); return; }
        const payload = {
          id: model, vendor: v, model,
          base_url: getBurlValue(),
          api_key: akey.value.trim(),
          tools: capToolsCb.checked,
          vision: capVisionCb.checked,
          thinking: capThinkingCb.checked,
          custom_protocol: false,
          input_max_tokens: capInputMaxSel.value || null,
          output_max_tokens: capOutputMaxSel.value || null,
          reasoning_effort: capReasoningSel.value || null,
          temperature: dsTempInp.value || null,
          top_p: dsTopPInp.value || null,
          top_logprobs: dsTopLogprobsSel.value || null,
          stop_sequences: dsStopInp.value || null,
          response_format: dsRespFmtSel.value || null,
          web_search: dsWebSearchCb.checked,
        };
        const r = await postJSON("/api/models/upsert", { model: payload })
          .catch((e) => ({ ok: false, error: e.message }));
        if (r.ok) { toast(existing ? "已保存修改" : "已添加模型", "ok"); Views.refreshPanels(); Chat.loadToolbarSelects(); }
        else toast("保存失败：" + (r.error || ""), "err");
      } }),
      existing ? el("button", { class: "btn ghost", text: "取消", onclick: () => editor.remove() }) : null,
    ]),
  ]);
  wrap.appendChild(editor);
  editor.scrollIntoView({ block: "nearest" });
  // 初始加载工具能力列表（如果工具调用已开启）
  if (capTools) updateToolCapabilities();
}

/** 弹出模型选择面板，让用户从列表中选择一个模型 */
function showModelPicker(models, onSelect) {
  const ov = el("div", { class: "ov", style: "z-index:6000;" });
  const box = el("div", { class: "ov-box", style: "max-height:70vh;overflow:auto;" });
  const searchInp = el("input", { placeholder: "搜索模型…", class: "form-input", style: "margin-bottom:10px;width:100%;" });
  const listWrap = el("div", { style: "display:flex;flex-direction:column;gap:2px;" });

  function renderList(filter) {
    listWrap.innerHTML = "";
    const filtered = filter ? models.filter(m => m.toLowerCase().includes(filter.toLowerCase())) : models;
    if (!filtered.length) {
      listWrap.appendChild(el("div", { class: "muted", text: "无匹配模型", style: "padding:12px;text-align:center;" }));
      return;
    }
    for (const m of filtered) {
      const row = el("div", { class: "card-row", style: "cursor:pointer;padding:6px 10px;border-radius:6px;",
        onclick: () => { document.body.removeChild(ov); onSelect(m); } });
      row.appendChild(el("span", { text: m }));
      listWrap.appendChild(row);
    }
  }

  searchInp.addEventListener("input", () => renderList(searchInp.value.trim()));
  box.appendChild(el("div", { class: "section-title", text: `选择模型（共 ${models.length} 个可用）` }));
  box.appendChild(searchInp);
  box.appendChild(listWrap);
  ov.appendChild(box);
  document.body.appendChild(ov);
  renderList("");
  ov.addEventListener("click", (e) => { if (e.target === ov) document.body.removeChild(ov); });
}

