// @ts-check
/* =====================================================================
 * plugins.js — plugins 面板子模块
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { State } from "../state.js";
import { getJSON, postJSON, delJSON, parseSSE } from "../api.js";
import * as Views from "../views.js";
// ------------------------------------------------------------------ 插件面板
let _pluginPanelBody = null;
export async function renderPluginsPanel(body) {
  _pluginPanelBody = body;
  const data = await getJSON("/api/plugins");
  const wrap = el("div", { class: "panel" });
  if (!data.ok) {
    wrap.appendChild(el("div", { class: "muted", text: "插件信息不可用：" + (data.error || "") }));
    body.appendChild(wrap);
    return;
  }

  // 统计信息
  const stats = el("div", { class: "plugin-stats" }, [
    el("span", { class: "plugin-stat-item", text: `📦 共 ${data.plugin_count || 0} 个插件` }),
    el("span", { class: "plugin-stat-item", text: `📁 ${data.module_count || 0} 个模块` }),
    el("span", { class: "plugin-stat-item muted small", text: "默认不启用：仅 config 中「已启用」的插件会在下次会话真正加载" }),
  ]);
  wrap.appendChild(stats);

  // 搜索框
  const searchInput = el("input", {
    class: "form-input", placeholder: "🔍 搜索插件名称、描述、作者…",
    oninput: () => applyFilter()
  });
  wrap.appendChild(searchInput);

  // 状态筛选 tab（全部 / 已启用 / 已禁用 / 未启用）
  let filterStatus = "all";
  const filterBar = el("div", { class: "plugin-filter-bar" });
  const statusOptions = [
    ["all", "全部"], ["enabled", "已启用"], ["disabled", "已禁用"], ["not_enabled", "未启用"],
  ];
  const applyFilter = () => {
    const q = (searchInput.value || "").trim().toLowerCase();
    let visible = 0;
    for (const section of wrap.querySelectorAll(".plugin-section")) {
      let sectionVisible = false;
      for (const card of section.querySelectorAll(".plugin-card")) {
        const st = card.dataset.status || "not_enabled";
        const txt = (card.dataset.search || "").toLowerCase();
        const okStatus = filterStatus === "all" || st === filterStatus;
        const okSearch = !q || txt.includes(q);
        const match = okStatus && okSearch;
        card.style.display = match ? "" : "none";
        if (match) sectionVisible = true;
      }
      section.style.display = sectionVisible ? "" : "none";
      if (sectionVisible) visible++;
    }
    let noResult = wrap.querySelector(".plugin-no-result");
    if (!visible) {
      if (!noResult) {
        noResult = el("div", { class: "muted plugin-no-result", text: "未找到匹配的插件" });
        wrap.appendChild(noResult);
      }
      noResult.style.display = "";
    } else if (noResult) {
      noResult.style.display = "none";
    }
  };
  for (const [val, label] of statusOptions) {
    const btn = el("button", {
      class: "plugin-filter-btn" + (val === "all" ? " active" : ""),
      text: label,
      onclick: () => {
        filterStatus = val;
        filterBar.querySelectorAll(".plugin-filter-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        applyFilter();
      }
    });
    filterBar.appendChild(btn);
  }
  wrap.appendChild(filterBar);


  const categories = data.categories || [];
  if (!categories.length) {
    wrap.appendChild(el("div", { class: "muted", text: "暂无插件信息" }));
    body.appendChild(wrap);
    return;
  }

  // 渲染每个分类
  for (const cat of categories) {
    const plugs = cat.plugins || [];
    if (!plugs.length) continue;

    const section = el("div", { class: "plugin-section" });

    // 分类标题（可折叠）
    const sectionTitle = el("div", { class: "plugin-section-title", onclick: () => {
      const body = section.querySelector(".plugin-section-body");
      const arrow = sectionTitle.querySelector(".plugin-arrow");
      if (body) {
        body.classList.toggle("collapsed");
        if (arrow) arrow.textContent = body.classList.contains("collapsed") ? "▶" : "▼";
      }
    }}, [
      el("span", { class: "plugin-arrow", text: "▼" }),
      el("span", { class: "plugin-cat-label", text: cat.label }),
      el("span", { class: "badge", text: plugs.length + " 个" }),
    ]);
    section.appendChild(sectionTitle);

    const bodyEl = el("div", { class: "plugin-section-body" });

    for (const p of plugs) {
      const card = el("div", { class: "plugin-card" });

      // 左侧主信息
      const mainCol = el("div", { class: "plugin-card-main" });

      // 标题行
      const titleRow = el("div", { class: "plugin-card-title" }, [
        el("span", { class: "plugin-name", text: p.label || p.name }),
      ]);
      if (p.source === "entrypoint") {
        titleRow.appendChild(el("span", { class: "badge", text: "pip 安装" }));
      } else if (p.source === "user") {
        titleRow.appendChild(el("span", { class: "badge warn", text: "用户" }));
      } else {
        titleRow.appendChild(el("span", { class: "badge on", text: "内置" }));
      }
      if (p.status === "enabled") {
        titleRow.appendChild(el("span", { class: "badge on", text: "✅ 已启用" }));
      } else if (p.status === "disabled") {
        titleRow.appendChild(el("span", { class: "badge off", text: "⛔ 已禁用" }));
      } else {
        titleRow.appendChild(el("span", { class: "badge warn", text: "⚪ 未启用" }));
      }
      if (p.version) {
        titleRow.appendChild(el("span", { class: "badge", text: "v" + p.version }));
      }
      if (p.kind) {
        titleRow.appendChild(el("span", { class: "badge", text: p.kind }));
      }
      if (p.provider_category && p.is_active_provider) {
        titleRow.appendChild(el("span", { class: "badge on", text: "⭐ 当前" + providerLabel(p.provider_category) }));
      }
      mainCol.appendChild(titleRow);

      // 描述
      if (p.description) {
        mainCol.appendChild(el("div", { class: "plugin-card-desc", text: p.description }));
      }

      // 元数据标签行
      const metaRow = el("div", { class: "plugin-card-meta" });
      if (p.author) {
        metaRow.appendChild(el("span", { class: "plugin-tag", text: "👤 " + p.author }));
      }
      if (p.hooks && p.hooks.length) {
        metaRow.appendChild(el("span", { class: "plugin-tag", text: "🔗 " + p.hooks.join(", ") }));
      }
      if (p.platforms && p.platforms.length) {
        metaRow.appendChild(el("span", { class: "plugin-tag", text: "💻 " + p.platforms.join(", ") }));
      }
      if (p.provides_tools && p.provides_tools.length) {
        metaRow.appendChild(el("span", { class: "plugin-tag", text: "🔧 " + p.provides_tools.join(", ") }));
      }
      if (p.pip_dependencies && p.pip_dependencies.length) {
        metaRow.appendChild(el("span", { class: "plugin-tag", text: "📦 " + p.pip_dependencies.join(", ") }));
      }
      mainCol.appendChild(metaRow);

      // 依赖缺失 / 捆绑技能提示
      if ((p.pip_missing && p.pip_missing.length) || (p.bundled_skills && p.bundled_skills.length)) {
        const extraRow = el("div", { class: "plugin-card-meta", style: "margin-top:4px;" });
        if (p.pip_missing && p.pip_missing.length) {
          extraRow.appendChild(el("span", { class: "plugin-tag warn", text: "⚠️ 缺依赖: " + p.pip_missing.join(", ") }));
        }
        if (p.bundled_skills && p.bundled_skills.length) {
          extraRow.appendChild(el("span", { class: "plugin-tag", text: "🧩 捆绑技能: " + p.bundled_skills.join(", ") }));
        }
        mainCol.appendChild(extraRow);
      }

      // 工具集状态
      if (p.toolset) {
        const ts = p.toolset;
        const tsRow = el("div", { class: "plugin-card-ts" }, [
          el("span", { class: "plugin-ts-icon", text: ts.available ? "✅" : "⚠️" }),
          el("span", { text: "工具集" }),
          el("span", { class: "badge " + (ts.available ? "on" : "off"), text: ts.available ? "就绪" : "未就绪" }),
          el("span", { class: "badge", text: ts.tool_count + " 工具" }),
        ]);
        if (ts.tools && ts.tools.length) {
          tsRow.appendChild(el("span", { class: "muted small", style: "margin-left:6px;", text: "(" + ts.tools.slice(0, 5).join(", ") + (ts.tools.length > 5 ? "…" : "") + ")" }));
        }
        mainCol.appendChild(tsRow);
      }

      // 环境变量配置信息
      const envItems = [];
      if (p.requires_env && p.requires_env.length) {
        for (const env of p.requires_env) {
          envItems.push(el("span", { class: "plugin-tag plugin-env-tag", text: "🔑 " + (env.name || env) }));
        }
      }
      if (p.optional_env && p.optional_env.length) {
        for (const env of p.optional_env) {
          envItems.push(el("span", { class: "plugin-tag plugin-env-tag muted", text: "⚙️ " + (env.name || env) }));
        }
      }
      if (envItems.length) {
        mainCol.appendChild(el("div", { class: "plugin-card-meta", style: "margin-top:4px;" }, envItems));
      }

      card.appendChild(mainCol);

      // 右侧操作区
      const actionsCol = el("div", { class: "plugin-card-actions" });
      if (p.requires_env && p.requires_env.length) {
        actionsCol.appendChild(el("button", { class: "btn sm", text: "配置",
          onclick: (e) => { e.stopPropagation(); openPluginConfig(p); } }));
      }
      // 启用 / 禁用（入口点插件由 pip 管理，不在本面板切换）
      if (p.source === "entrypoint") {
        actionsCol.appendChild(el("span", { class: "badge muted", text: "pip 管理" }));
      } else {
        const _isOn = p.status === "enabled";
        actionsCol.appendChild(el("button", { class: "btn sm " + (_isOn ? "ghost" : "primary"), text: _isOn ? "禁用" : "启用",
          onclick: (e) => { e.stopPropagation(); togglePluginEnabled(p); } }));
      }
      // 删除（仅用户自行安装的插件）
      if (p.source === "user") {
        actionsCol.appendChild(el("button", { class: "btn sm danger", text: "删除",
          onclick: (e) => { e.stopPropagation(); deleteUserPlugin(p); } }));
      }
      // Provider 单选激活
      if (p.provider_category) {
        if (p.is_active_provider) {
          actionsCol.appendChild(el("span", { class: "badge on", text: "✓ 当前" + providerLabel(p.provider_category) }));
        } else {
          actionsCol.appendChild(el("button", { class: "btn sm", text: "设为" + providerLabel(p.provider_category),
            onclick: (e) => { e.stopPropagation(); setProvider(p); } }));
        }
      }
      // pip 依赖安装
      if (p.pip_missing && p.pip_missing.length) {
        actionsCol.appendChild(el("button", { class: "btn sm", text: "安装依赖",
          onclick: (e) => { e.stopPropagation(); installDeps(p); } }));
      }
      // 详情展开按钮
      actionsCol.appendChild(el("button", { class: "btn sm ghost", text: "详情",
        onclick: (e) => { e.stopPropagation(); togglePluginDetail(card, p); } }));
      card.appendChild(actionsCol);

      // 搜索数据
      const searchParts = [p.name, p.label || "", p.description || "", p.author || "", p.kind || ""];
      if (p.hooks) searchParts.push(p.hooks.join(" "));
      if (p.provides_tools) searchParts.push(p.provides_tools.join(" "));
      card.dataset.status = p.status || "not_enabled";
      card.dataset.search = searchParts.join(" ").toLowerCase();

      bodyEl.appendChild(card);
    }

    section.appendChild(bodyEl);
    wrap.appendChild(section);
  }

  body.appendChild(wrap);
}

// Provider 分类显示名
function providerLabel(cat) {
  return { web: "搜索后端", memory: "记忆 Provider", context_engine: "上下文引擎", image_gen: "图像 Provider", video_gen: "视频 Provider" }[cat] || cat;
}

// 设为当前 provider（写 config.yaml 对应字段，重启会话生效）
async function setProvider(p) {
  try {
    const r = await postJSON("/api/plugins/set-provider", { category: p.provider_category, value: p.provider_value });
    if (r && r.ok) {
      toast(`已将「${p.label || p.name}」设为当前 ${providerLabel(p.provider_category)}（重启会话生效）`, "ok");
      if (_pluginPanelBody) renderPluginsPanel(_pluginPanelBody);
    } else {
      toast("设置失败：" + ((r && r.error) || "未知错误"), "err");
    }
  } catch (e) {
    toast("设置失败：" + e.message, "err");
  }
}

// 安装插件缺失的 pip 依赖（调用应用 python -m pip install）
async function installDeps(p) {
  const deps = p.pip_missing || [];
  if (!deps.length) return;
  if (!confirm(`安装插件「${p.label || p.name}」缺失的依赖？\n\n${deps.join("\n")}\n\n将调用 pip 安装到当前 Python 环境。`)) return;
  try {
    const r = await postJSON("/api/plugins/install-deps", { deps });
    if (r && r.ok) {
      toast("依赖已安装", "ok");
      if (_pluginPanelBody) renderPluginsPanel(_pluginPanelBody);
    } else {
      toast("安装失败：" + ((r && r.error) || "未知错误"), "err");
    }
  } catch (e) {
    toast("安装失败：" + e.message, "err");
  }
}

// 插件配置弹窗
function openPluginConfig(p) {
  const overlay = el("div", { class: "ss-edit-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });
  const modal = el("div", { class: "ss-edit-modal" });
  modal.appendChild(el("h3", { text: "配置插件：" + (p.label || p.name) }));
  if (p.description) {
    modal.appendChild(el("p", { class: "muted", style: "margin-bottom:14px;", text: p.description }));
  }
  const envList = p.requires_env || [];
  const optEnvList = p.optional_env || [];
  if (!envList.length && !optEnvList.length) {
    modal.appendChild(el("p", { class: "muted", text: "该插件无需额外配置环境变量。" }));
  }
  for (const env of envList) {
    const name = env.name || env;
    const label = env.prompt || name;
    const isPassword = env.password !== false;
    modal.appendChild(el("div", { class: "ss-edit-field" }, [
      el("label", { text: label }),
      el("input", { type: isPassword ? "password" : "text", placeholder: name,
        style: "width:100%;", "data-env-key": name }),
    ]));
  }
  for (const env of optEnvList) {
    const name = env.name || env;
    const label = env.prompt || name + "（可选）";
    const isPassword = env.password === true;
    modal.appendChild(el("div", { class: "ss-edit-field" }, [
      el("label", { text: label, class: "muted" }),
      el("input", { type: isPassword ? "password" : "text", placeholder: name,
        style: "width:100%;", "data-env-key": name }),
    ]));
  }
  const btnRow = el("div", { style: "display:flex;gap:8px;margin-top:16px;justify-content:flex-end;" });
  btnRow.appendChild(el("button", { class: "btn", text: "取消", onclick: () => overlay.remove() }));
  btnRow.appendChild(el("button", { class: "btn primary", text: "保存",
    onclick: async () => {
      const values = {};
      for (const inp of modal.querySelectorAll("[data-env-key]")) {
        values[inp.dataset.envKey] = inp.value;
      }
      // 真实写入示例 HERMES_HOME 的 .env（对齐 hermes plugins install 的落盘位置）
      try {
        const r = await postJSON("/api/plugins/env", { key: p.key || p.name, values });
        if (r && r.ok) {
          toast("环境变量已保存（重启会话后生效）", "ok");
          overlay.remove();
        } else {
          toast("保存失败：" + ((r && r.error) || "未知错误"), "err");
        }
      } catch (e) {
        toast("保存失败：" + e.message, "err");
      }
    }
  }));
  modal.appendChild(btnRow);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}

// 启用 / 禁用插件（写入示例 HERMES_HOME 的 config.yaml，下次会话生效）
async function togglePluginEnabled(p) {
  const enable = p.status !== "enabled";
  try {
    const r = await postJSON("/api/plugins/toggle", { key: p.key || p.name, enabled: enable });
    if (r && r.ok) {
      toast(enable ? "已启用（下次会话生效）" : "已禁用（下次会话生效）", "ok");
      if (_pluginPanelBody) renderPluginsPanel(_pluginPanelBody);
    } else {
      toast("操作失败：" + ((r && r.error) || "未知错误"), "err");
    }
  } catch (e) {
    toast("操作失败：" + e.message, "err");
  }
}

// 删除用户自行安装的插件
async function deleteUserPlugin(p) {
  if (!confirm(`确定删除用户插件「${p.label || p.name}」？此操作不可恢复。`)) return;
  try {
    const r = await postJSON("/api/plugins/delete", { key: p.key || p.name });
    if (r && r.ok) {
      toast("已删除", "ok");
      if (_pluginPanelBody) renderPluginsPanel(_pluginPanelBody);
    } else {
      toast("删除失败：" + ((r && r.error) || "未知错误"), "err");
    }
  } catch (e) {
    toast("删除失败：" + e.message, "err");
  }
}

// 插件详情展开/收起
function togglePluginDetail(card, p) {
  let detail = card.querySelector(".plugin-detail");
  if (detail) {
    detail.remove();
    return;
  }
  detail = el("div", { class: "plugin-detail" });
  const table = el("table", { class: "plugin-detail-table" });
  const rows = [
    ["插件名", p.name],
    ["显示名", p.label || "-"],
    ["版本", p.version || "-"],
    ["作者", p.author || "-"],
    ["类型", p.kind || "-"],
    ["来源", p.source === "user" ? "用户安装" : "内置"],
    ["分类", (p.category_icon || "") + " " + (p.category || "-")],
    ["模块数", String(p.module_count || 0)],
    ["子包数", String(p.package_count || 0)],
    ["文件数", String(p.file_count || 0)],
  ];
  if (p.hooks && p.hooks.length) {
    rows.push(["Hooks", p.hooks.join(", ")]);
  }
  if (p.platforms && p.platforms.length) {
    rows.push(["支持平台", p.platforms.join(", ")]);
  }
  if (p.provides_tools && p.provides_tools.length) {
    rows.push(["提供工具", p.provides_tools.join(", ")]);
  }
  if (p.pip_dependencies && p.pip_dependencies.length) {
    rows.push(["依赖", p.pip_dependencies.join(", ")]);
  }
  for (const [k, v] of rows) {
    const tr = el("tr", {}, [
      el("td", { class: "plugin-detail-key", text: k }),
      el("td", { text: v }),
    ]);
    table.appendChild(tr);
  }
  detail.appendChild(table);
  card.appendChild(detail);
}
