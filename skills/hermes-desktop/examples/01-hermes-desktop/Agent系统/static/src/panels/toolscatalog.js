// @ts-check
/* =====================================================================
 * toolscatalog.js — 工具清单面板（只读）
 *   对齐 Hermes Library 的 tools.registry：
 *   把已注册的全部工具（Hermes 内置 + 本示例注入的宿主/业务扩展工具）以
 *   可读清单呈现——name / toolset / description / 入参 schema / 来源徽标。
 *   仅读取注册表元信息，不写盘、不改配置、不碰密钥。
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { getJSON } from "../api.js";

export async function renderToolsCatalogPanel(body) {
  body.innerHTML = "";

  // 顶部说明（如实）
  const intro = el("div", { class: "muted small", style: "margin-bottom:12px;" }, [
    "工具清单：列出当前进程内已注册到 Hermes 注册表的所有工具。",
    "工具的 API 密钥由 Hermes 在进程内托管（",
    el("b", { text: "本面板看不到、也拿不到任何密钥" }),
    "），这里只罗列工具的元信息。",
  ]);
  body.appendChild(intro);

  // ── 概览徽标区 ──
  const stats = el("div", { class: "toolcat-stats" });
  body.appendChild(stats);

  // ── 过滤区 ──
  const controls = el("div", { class: "toolcat-controls" });

  const search = el("input", { class: "form-input toolcat-search",
    placeholder: "搜索工具名 / 描述 / 所属工具集", style: "flex:1;" });

  const tsSel = el("select", { class: "form-input toolcat-filter" });
  tsSel.appendChild(el("option", { value: "", text: "全部工具集" }));

  const originSel = el("select", { class: "form-input toolcat-filter" });
  originSel.appendChild(el("option", { value: "", text: "全部来源" }));
  originSel.appendChild(el("option", { value: "hermes_builtin", text: "Hermes 内置" }));
  originSel.appendChild(el("option", { value: "example_injected", text: "本示例注入（自定义）" }));
  originSel.appendChild(el("option", { value: "other", text: "其他来源" }));

  const refreshBtn = el("button", { class: "btn", text: "刷新" });

  controls.appendChild(search);
  controls.appendChild(tsSel);
  controls.appendChild(originSel);
  controls.appendChild(refreshBtn);
  body.appendChild(controls);

  // ── 结果区 ──
  const result = el("div", { class: "toolcat-result" });
  body.appendChild(result);

  let _data = null;  // 最近一次拉取的全量数据

  function _applyFilter() {
    if (!_data) return;
    const q = search.value.trim().toLowerCase();
    const ts = tsSel.value;
    const og = originSel.value;
    const filtered = _data.tools.filter((t) => {
      if (ts && t.toolset !== ts) return false;
      if (og && t.origin !== og) return false;
      if (q) {
        const hay = (t.name + " " + t.toolset + " " + t.description).toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    _renderTools(filtered, _data.by_toolset);
  }

  function _originBadge(origin) {
    const map = {
      hermes_builtin: ["Hermes 内置", "ok"],
      example_injected: ["本示例注入", "warn"],
      other: ["其他", ""],
    };
    const [text, cls] = map[origin] || ["其他", ""];
    return el("span", { class: "toolcat-badge " + cls, text: text });
  }

  function _renderTools(tools, byToolset) {
    result.innerHTML = "";
    if (!tools.length) {
      result.appendChild(el("div", { class: "muted", text: "没有匹配的工具。" }));
      return;
    }
    // 按 toolset 分组
    const groups = {};
    for (const t of tools) (groups[t.toolset] = groups[t.toolset] || []).push(t);
    const keys = Object.keys(groups).sort();

    const head = el("div", { class: "toolcat-count muted small",
      text: "共 " + tools.length + " 个工具（按工具集分组）" });
    result.appendChild(head);

    for (const ts of keys) {
      const g = el("div", { class: "toolcat-group" });
      g.appendChild(el("div", { class: "toolcat-group-title", text: ts + "（" + groups[ts].length + "）" }));
      for (const t of groups[ts]) {
        g.appendChild(_renderToolCard(t));
      }
      result.appendChild(g);
    }
  }

  function _renderToolCard(t) {
    const card = el("div", { class: "toolcat-card" });

    const titleRow = el("div", { class: "toolcat-card-title" }, [
      el("span", { class: "toolcat-emoji", text: t.emoji || "⚡" }),
      el("span", { class: "toolcat-name", text: t.name }),
      el("span", { class: "toolcat-badge ts", text: "工具集：" + t.toolset }),
      _originBadge(t.origin),
    ]);
    if (t.is_async) titleRow.appendChild(el("span", { class: "toolcat-badge", text: "异步" }));
    if (t.requires_env && t.requires_env.length) {
      titleRow.appendChild(el("span", { class: "toolcat-badge env",
        text: "需环境变量：" + t.requires_env.join(", ") }));
    }
    card.appendChild(titleRow);

    if (t.description) {
      card.appendChild(el("div", { class: "toolcat-desc", text: t.description }));
    }

    const params = (t.schema && t.schema.parameters) || null;
    if (params && params.fields && params.fields.length) {
      const tbl = el("table", { class: "toolcat-params" });
      const thead = el("thead", {}, [el("tr", {}, [
        el("th", { text: "参数" }),
        el("th", { text: "类型" }),
        el("th", { text: "必填" }),
        el("th", { text: "说明" }),
      ])]);
      tbl.appendChild(thead);
      const tbody = el("tbody", {});
      for (const f of params.fields) {
        tbody.appendChild(el("tr", {}, [
          el("td", { class: "toolcat-param-name", text: f.name }),
          el("td", { class: "toolcat-param-type", text: String(f.type) }),
          el("td", { text: f.required ? "是" : "否" }),
          el("td", { class: "toolcat-param-desc", text: f.description || "" }),
        ]));
      }
      tbl.appendChild(tbody);
      card.appendChild(el("div", { class: "toolcat-params-wrap" }, [tbl]));
    } else {
      card.appendChild(el("div", { class: "muted small", text: "（该工具无入参或入参未公开）" }));
    }
    // 一键直达：点击清单中的工具集卡片 → 跳转「工具管理」对应位置
    card.style.cursor = "pointer";
    card.title = "点击直达「工具管理」中该工具集";
    card.appendChild(el("div", { class: "toolcat-goto muted small", text: "⚙ 点击此卡片可直达「工具管理」启用 / 配置" }));
    card.addEventListener("click", () => {
      if (typeof window.__gotoToolsManage === "function") window.__gotoToolsManage(t.toolset);
      else toast("工具管理面板未就绪", "info");
    });
    return card;
  }

  function _renderStats(d) {
    stats.innerHTML = "";
    const oc = d.origin_counts || {};
    const chips = [
      ["工具总数", d.count, ""],
      ["Hermes 内置", oc.hermes_builtin || 0, "ok"],
      ["本示例注入", oc.example_injected || 0, "warn"],
      ["工具集数", Object.keys(d.by_toolset || {}).length, ""],
    ];
    for (const [label, val, cls] of chips) {
      stats.appendChild(el("span", { class: "toolcat-stat " + cls }, [
        el("b", { text: String(val) }), " " + label,
      ]));
    }
  }

  async function _load() {
    result.innerHTML = '<div class="muted">加载中…</div>';
    const d = await getJSON("/api/tools-catalog")
      .catch(() => ({ ok: false, error: "网络错误" }));
    if (!d || !d.ok) {
      result.innerHTML = "";
      result.appendChild(el("div", { class: "struct-msg bad",
        text: "加载失败：" + (d && d.error || "未知错误") }));
      return;
    }
    _data = d;
    _renderStats(d);
    // 填充工具集下拉
    tsSel.innerHTML = "";
    tsSel.appendChild(el("option", { value: "", text: "全部工具集" }));
    for (const [ts, n] of Object.entries(d.by_toolset || {})) {
      tsSel.appendChild(el("option", { value: ts, text: ts + "（" + n + "）" }));
    }
    _applyFilter();
  }

  search.addEventListener("input", _applyFilter);
  tsSel.addEventListener("change", _applyFilter);
  originSel.addEventListener("change", _applyFilter);
  refreshBtn.addEventListener("click", () => { _load(); toast("已刷新工具清单", "ok"); });

  _load();
}
