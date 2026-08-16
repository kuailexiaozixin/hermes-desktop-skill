// @ts-check
/* =====================================================================
 * structured.js — 结构化输出面板
 *   对齐 Hermes Library 的 structured output：
 *   1) 运行：把「指令 + 可选输入 + 可选 JSON Schema」交给 host-owned 模型，
 *      返回原始文本 / 解析后的 JSON / 校验结果；
 *   2) 校验：离线把一段 JSON 按可选 schema 校验（纯本地）。
 *   仅触发 host-owned 客户端并读取其输出，不写盘、不改配置、不碰密钥。
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { postJSON } from "../api.js";

export async function renderStructuredPanel(body) {
  body.innerHTML = "";

  // 顶部说明（如实）
  const intro = el("div", { class: "muted small", style: "margin-bottom:12px;" }, [
    "Hermes 的结构化输出：把一段指令交给模型，要求其返回符合 JSON Schema 的 JSON。",
    "本面板通过 Hermes 托管的 host-owned 客户端执行（",
    el("b", { text: "密钥由 Hermes 保管，本面板看不到、也拿不到" }),
    "），只读取模型返回。下方「校验」为纯本地，无需联网。",
  ]);
  body.appendChild(intro);

  // ── 区块 1：运行结构化输出 ──
  const runCard = el("div", { class: "struct-card" });
  body.appendChild(runCard);
  runCard.appendChild(el("div", { class: "struct-card-title", text: "① 运行结构化输出（调用模型）" }));

  const instrTa = el("textarea", { class: "form-input struct-ta", rows: "3",
    placeholder: "例如：从下面的资料中抽取联系人信息" });
  const inputTa = el("textarea", { class: "form-input struct-ta", rows: "3",
    placeholder: "可选：给模型的原始资料 / 待抽取文本" });

  // 模式：json_object vs json_schema
  const modeSel = el("select", { class: "form-input struct-filter" }, [
    el("option", { value: "schema", text: "JSON Schema 模式（推荐，带校验）" }),
    el("option", { value: "object", text: "json_object 模式（只要求返回 JSON）" }),
  ]);
  const schemaTa = el("textarea", { class: "form-input struct-ta", rows: "5",
    placeholder: "JSON Schema（当上方选择 Schema 模式时生效），例如：\n{\n  \"type\": \"object\",\n  \"properties\": {\n    \"name\": {\"type\": \"string\"},\n    \"age\": {\"type\": \"integer\"}\n  },\n  \"required\": [\"name\"]\n}" });
  const schemaName = el("input", { class: "form-input struct-filter",
    placeholder: "schema 名称（可选）", style: "width:200px;" });
  const tempInp = el("input", { class: "form-input struct-filter", type: "number",
    step: "0.1", min: "0", max: "2", placeholder: "温度0.2", style: "width:90px;" });
  const maxInp = el("input", { class: "form-input struct-filter", type: "number",
    min: "1", placeholder: "最大令牌2000", style: "width:110px;" });

  const fillDemo = el("button", { class: "btn ghost", text: "填入示例", title: "填入一个可运行的示例" });
  const runBtn = el("button", { class: "btn primary", text: "运行" });

  runCard.appendChild(el("label", { class: "struct-label", text: "指令（必填）" }));
  runCard.appendChild(instrTa);
  runCard.appendChild(el("label", { class: "struct-label", text: "输入资料（可选）" }));
  runCard.appendChild(inputTa);
  runCard.appendChild(el("label", { class: "struct-label", text: "输出模式" }));
  runCard.appendChild(modeSel);
  runCard.appendChild(el("label", { class: "struct-label", text: "JSON Schema（Schema 模式时生效）" }));
  runCard.appendChild(schemaTa);
  const optRow = el("div", { class: "struct-opt-row" }, [
    el("span", { class: "muted small", text: "名称" }), schemaName,
    el("span", { class: "muted small", text: "温度" }), tempInp,
    el("span", { class: "muted small", text: "最大令牌" }), maxInp,
  ]);
  runCard.appendChild(optRow);
  runCard.appendChild(el("div", { class: "struct-btn-row" }, [fillDemo, runBtn]));

  // ── 区块 2：离线校验 ──
  const valCard = el("div", { class: "struct-card" });
  body.appendChild(valCard);
  valCard.appendChild(el("div", { class: "struct-card-title", text: "② 离线校验 JSON（纯本地）" }));
  const valJson = el("textarea", { class: "form-input struct-ta", rows: "4",
    placeholder: "粘贴待校验的 JSON" });
  const valSchema = el("textarea", { class: "form-input struct-ta", rows: "4",
    placeholder: "粘贴 JSON Schema（可选）" });
  const valBtn = el("button", { class: "btn", text: "校验" });
  valCard.appendChild(el("label", { class: "struct-label", text: "JSON" }));
  valCard.appendChild(valJson);
  valCard.appendChild(el("label", { class: "struct-label", text: "JSON Schema（可选）" }));
  valCard.appendChild(valSchema);
  valCard.appendChild(el("div", { class: "struct-btn-row" }, [valBtn]));

  // ── 结果区 ──
  const result = el("div", { class: "struct-result" });
  body.appendChild(result);

  function _renderRunResult(d) {
    result.innerHTML = "";
    if (!d || !d.ok) {
      result.appendChild(el("div", { class: "struct-bad struct-msg",
        text: "失败：" + (d && d.error || "未知错误") }));
      return;
    }
    if (d.available === false) {
      result.appendChild(el("div", { class: "struct-warn struct-msg", text: d.error || "不可用" }));
      if (d.note) result.appendChild(el("div", { class: "muted small", text: d.note }));
      return;
    }
    // 元信息行
    const meta = el("div", { class: "struct-meta" }, [
      el("span", { class: "struct-badge", text: "模型：" + (d.model || "?") }),
      el("span", { class: "struct-badge " + (d.content_type === "json" ? "ok" : "warn"),
        text: "内容：" + (d.content_type === "json" ? "JSON" : "文本") }),
      el("span", { class: "struct-badge " + (d.validation_ok ? "ok" : "bad"),
        text: d.validation_ok ? "Schema 校验通过" : (d.validation_error ? "Schema 校验未通过" : "未校验") }),
    ]);
    result.appendChild(meta);
    if (d.validation_error) {
      result.appendChild(el("div", { class: "struct-bad struct-msg", text: d.validation_error }));
    }
    // 原始文本
    result.appendChild(el("div", { class: "struct-sub", text: "原始返回" }));
    const raw = el("pre", { class: "struct-raw" }, [esc(d.text || "")]);
    result.appendChild(raw);
    // 解析后的 JSON
    if (d.content_type === "json" && d.parsed !== null && d.parsed !== undefined) {
      let pretty;
      try { pretty = JSON.stringify(d.parsed, null, 2); }
      catch (e) { pretty = String(d.parsed); }
      result.appendChild(el("div", { class: "struct-sub", text: "解析后的 JSON" }));
      const pj = el("pre", { class: "struct-json" }, [esc(pretty)]);
      result.appendChild(pj);
    }
  }

  function _renderValidateResult(d) {
    result.innerHTML = "";
    if (!d || !d.ok) {
      result.appendChild(el("div", { class: "struct-bad struct-msg",
        text: "失败：" + (d && d.error || "未知错误") }));
      return;
    }
    const meta = el("div", { class: "struct-meta" }, [
      el("span", { class: "struct-badge",
        text: "类型：" + (d.content_type === "json" ? "JSON" : "文本") }),
      el("span", { class: "struct-badge " + (d.validation_ok ? "ok" : "bad"),
        text: d.validation_ok ? "校验通过" : "校验未通过" }),
    ]);
    result.appendChild(meta);
    if (d.validation_error) {
      result.appendChild(el("div", { class: "struct-bad struct-msg", text: d.validation_error }));
    }
    if (d.parsed !== null && d.parsed !== undefined) {
      let pretty;
      try { pretty = JSON.stringify(d.parsed, null, 2); }
      catch (e) { pretty = String(d.parsed); }
      result.appendChild(el("div", { class: "struct-sub", text: "解析后的 JSON" }));
      result.appendChild(el("pre", { class: "struct-json" }, [esc(pretty)]));
    }
  }

  function _setRunning(on) {
    runBtn.disabled = on;
    runBtn.textContent = on ? "运行中…" : "运行";
  }

  runBtn.addEventListener("click", async () => {
    const instructions = instrTa.value.trim();
    if (!instructions) { toast("请填写指令", "err"); return; }
    const useSchema = modeSel.value === "schema";
    const body2 = {
      instructions,
      input: inputTa.value,
      json_mode: !useSchema,
      schema: useSchema ? schemaTa.value : "",
      schema_name: schemaName.value,
      temperature: tempInp.value,
      max_tokens: maxInp.value,
    };
    _setRunning(true);
    try {
      const d = await postJSON("/api/structured/run", body2)
        .catch(() => ({ ok: false, error: "网络错误" }));
      _renderRunResult(d);
      if (d && d.ok && d.available !== false) toast("结构化输出完成", "ok");
      else if (d && d.available === false) toast(d.error || "不可用", "info");
      else if (!d || !d.ok) toast("运行失败", "err");
    } finally {
      _setRunning(false);
    }
  });

  valBtn.addEventListener("click", async () => {
    const d = await postJSON("/api/structured/validate",
      { json: valJson.value, schema: valSchema.value })
      .catch(() => ({ ok: false, error: "网络错误" }));
    _renderValidateResult(d);
    if (d && d.ok) toast(d.validation_ok ? "校验通过" : "校验未通过", d.validation_ok ? "ok" : "warn");
    else toast("校验失败", "err");
  });

  fillDemo.addEventListener("click", () => {
    instrTa.value = "从资料中抽取联系人信息，返回 name（姓名）与 age（年龄，整数）。";
    inputTa.value = "张伟的年纪是 28 岁，李娜今年 34 岁。";
    modeSel.value = "schema";
    schemaTa.value = JSON.stringify({
      type: "object",
      properties: {
        name: { type: "string" },
        age: { type: "integer" },
      },
      required: ["name", "age"],
    }, null, 2);
    schemaName.value = "contact";
    tempInp.value = "0.2";
    maxInp.value = "2000";
    toast("已填入示例，点击「运行」试试", "info");
  });
}
