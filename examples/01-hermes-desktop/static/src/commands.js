// @ts-check
/* =====================================================================
 * commands.js — 斜杠命令注册表：集中管理所有命令定义、分类、匹配与分发
 * 设计原则：
 *   - 单真相源：所有命令在此注册，前端和后端共用此定义
 *   - 分类清晰：按功能领域分组，便于用户浏览和发现
 *   - 可扩展：新增命令只需添加一个条目
 *   - 可发现：提供 getCompletions() 供 UI 补全
 *   - 交互反馈：命令执行时触发 Toast + 可选面板联动
 * ===================================================================== */
import { $, el, esc, toast } from "./dom.js";
import { State, toggleTheme } from "./state.js";
import { getJSON, postJSON } from "./api.js";
import { formatUsage } from "./util.js";

// ------------------------------------------------------------------ 命令分类
export const CATEGORIES = {
  session: { label: "会话管理", icon: "💬" },
  model:   { label: "模型配置", icon: "🤖" },
  tool:    { label: "工具控制", icon: "🔌" },
  info:    { label: "信息查询", icon: "ℹ️" },
  manage:  { label: "系统管理", icon: "⚙️" },
};

// ------------------------------------------------------------------ 动态命令合并（从后端 /api/commands 加载原生指令）
let _dynamicCommands = null;

async function loadDynamicCommands() {
  if (_dynamicCommands) return _dynamicCommands;
  try {
    const { getJSON } = await import("./api.js");
    const data = await getJSON("/api/commands").catch(() => ({ items: [] }));
    const items = (data.items || []).filter(item => {
      const name = (typeof item === "string" ? item : (item.name || item.id || ""));
      return name && !COMMANDS.some(c => c.id === name);
    });
    _dynamicCommands = items.map(item => {
      const name = typeof item === "string" ? item : (item.name || item.id || "");
      const desc = typeof item === "string" ? "Hermes 原生指令" : (item.description || item.desc || "Hermes 原生指令");
      return { id: name, desc, usage: "", category: "manage", handler: async (args) => {
        const r = await postJSON("/api/command", { text: "/" + name + (args ? " " + args : "") }).catch(() => ({}));
        if (r.ok && r.name) {
          const out = r.result && typeof r.result === "object" ? JSON.stringify(r.result, null, 2) : String(r.result || "");
          toast("⚡ 已执行原生指令: " + r.name, "ok");
          return out;
        }
        return "执行失败或未找到该原生指令。";
      }, localOnly: false, dynamic: true };
    });
    return _dynamicCommands;
  } catch (_) { return []; }
}

/** 获取所有命令（含动态合并的） */
export async function getAllCommands() {
  const static_cmds = COMMANDS.slice();
  const dynamic = await loadDynamicCommands();
  return static_cmds.concat(dynamic);
}

/** 获取动态命令 */
export function getDynamicCommands() {
  return _dynamicCommands || [];
}

// ------------------------------------------------------------------ 面板联动
function openPanel(name) {
  const nav = document.querySelector(`#sideNav .nav[data-view="${name}"]`);
  if (nav) { nav.click(); return true; }
  return false;
}

// 面板打开后高亮定位：在面板渲染完成后滚动到目标元素
// 防御式：面板可能未渲染 / 选择器非法（querySelector 会抛 SyntaxError）/ 元素不存在，
// 均静默兜底，绝不影响主流程。
function highlightInPanel(panelName, selector) {
  // 延迟等待面板渲染
  setTimeout(() => {
    const panel = document.getElementById("view-" + panelName);
    if (!panel) return;
    let target = null;
    try { target = panel.querySelector(selector); } catch (_) { target = null; }
    if (!target) return;
    try { target.scrollIntoView({ block: "center", behavior: "smooth" }); } catch (_) {}
    target.classList.add("highlight-flash");
    setTimeout(() => { try { target.classList.remove("highlight-flash"); } catch (_) {} }, 1500);
  }, 300);
}

// ------------------------------------------------------------------ 命令定义
const COMMANDS = [];

function reg(id, desc, category, handler, usage, localOnly) {
  COMMANDS.push({ id, desc, usage: usage || "", category, handler, localOnly: !!localOnly });
}

// =====================================================================
// 会话管理
// =====================================================================
reg("new", "新建对话，清空当前聊天记录", "session", async () => {
  const convList = document.getElementById("convList");
  if (convList) convList.innerHTML = "";
  State.conv_id = null;
  State.usage = { input: 0, output: 0 };
  State.messages = [];
  const conv = document.getElementById("chat");
  if (conv) conv.innerHTML = "";
  updateUsageChip();
  toast("✅ 已新建对话", "ok");
  return "已新建对话，可以开始新的对话了。";
}, undefined, true);

reg("clear", "清空屏幕气泡，保留会话", "session", async () => {
  const conv = document.getElementById("chat");
  if (conv) conv.innerHTML = "";
  toast("🧹 已清空屏幕", "ok");
  return "已清空屏幕。";
}, undefined, true);

reg("undo", "撤销最近的一条用户消息", "session", async () => {
  const conv = document.getElementById("chat");
  if (!conv) { toast("❌ 没有可撤销的消息", "err"); return "没有可撤销的消息。"; }
  const bubbles = conv.querySelectorAll(".msg-row");
  for (let i = bubbles.length - 1; i >= 0; i--) {
    const b = bubbles[i];
    if (b.classList.contains("user-msg")) {
      let next = b.nextElementSibling;
      while (next) {
        const toRemove = next;
        next = next.nextElementSibling;
        toRemove.remove();
      }
      b.remove();
      toast("↩️ 已撤销上一步", "ok");
      return "已撤销上一步。";
    }
  }
  toast("❌ 没有可撤销的消息", "err");
  return "没有可撤销的消息。";
}, undefined, true);

reg("retry", "重新发送最后一条用户消息", "session", async () => {
  const conv = document.getElementById("chat");
  if (!conv) { toast("❌ 没有可重试的消息", "err"); return "没有可重试的消息。"; }
  const bubbles = conv.querySelectorAll(".msg-row.user-msg");
  if (bubbles.length === 0) { toast("❌ 没有可重试的消息", "err"); return "没有可重试的消息。"; }
  const last = bubbles[bubbles.length - 1];
  const text = last.textContent || "";
  const ta = document.getElementById("prompt");
  if (ta) {
    ta.textContent = text;
    ta.dispatchEvent(new Event("input", { bubbles: true }));
  }
  toast("↻ 已复制到输入框，确认后发送", "ok");
  return "已复制最后一条消息到输入框，请确认后发送。";
}, undefined, true);

reg("sessions", "打开历史会话面板", "session", async () => {
  if (openPanel("chat")) {
    toast("📋 已切换到会话面板", "ok");
    return "已切换到会话面板。";
  }
  return "找不到历史会话面板。";
}, undefined, true);

reg("title", "设置当前会话标题，用法：/title 新标题", "session", async (args) => {
  if (!args) return "请指定标题，用法：/title 新标题";
  if (!State.conv_id) { toast("❌ 当前没有活动会话", "err"); return "当前没有活动会话。"; }
  await postJSON("/api/conversations/" + encodeURIComponent(State.conv_id) + "/rename", { name: args }).catch(() => {});
  toast("✏️ 标题已更新：" + args, "ok");
  return "标题已更新为：" + args;
}, undefined, false);

reg("branch", "从当前对话创建分支，用法：/branch 分支描述", "session", async (args) => {
  if (!State.conv_id) { toast("❌ 当前没有活动会话", "err"); return "当前没有活动会话。"; }
  const desc = args || "分支";
  const r = await postJSON("/api/conversations/" + encodeURIComponent(State.conv_id) + "/copy", {}).catch(() => ({}));
  if (r.ok) {
    toast("🌿 已创建分支：" + desc, "ok");
    return "已创建分支：" + desc + "（会话 ID: " + (r.id || "?") + "）";
  }
  toast("❌ 分支创建失败", "err");
  return "分支创建失败，后端可能不支持此操作。";
}, undefined, false);

// =====================================================================
reg("copy", "复制最后一条消息到剪贴板，用法：/copy [text|code]", "session", async (args) => {
  const conv = document.getElementById("chat");
  if (!conv) { toast("没有消息可复制", "err"); return "没有消息可复制。"; }
  const msgs = conv.querySelectorAll(".msg-row");
  if (!msgs.length) { toast("没有消息可复制", "err"); return "没有消息可复制。"; }
  const last = msgs[msgs.length - 1];
  const bubble = last.querySelector(".bubble");
  if (!bubble) { toast("无法获取消息内容", "err"); return "无法获取消息内容。"; }
  let txt = bubble.textContent || "";
  if (args === "code") {
    const codes = bubble.querySelectorAll("code");
    txt = Array.from(codes).map(c => c.textContent).join("\n\n");
  }
  if (typeof copyToClipboard === "function") {
    const ok = await copyToClipboard(txt);
    if (ok) { toast("已复制到剪贴板", "ok"); return "已复制最后一条消息到剪贴板。"; }
  }
  const ta = document.getElementById("prompt");
  if (ta) { ta.textContent = txt; ta.dispatchEvent(new Event("input", { bubbles: true })); }
  toast("已复制到输入框", "ok");
  return "已复制最后一条消息到输入框，请确认后发送。";
}, undefined, false);

// 模型配置
// =====================================================================
reg("model", "查看/切换活动模型，用法：/model 模型名", "model", async (args) => {
  if (!args) {
    const cur = State.model || "未设置";
    const models = await getJSON("/api/models").catch(() => ({ items: [] }));
    const all = (models.items || []).map(m => m.id || m.name || "?").join(", ");
    return "当前模型：" + cur + "\n可用模型：" + (all || "无");
  }
  const models = await getJSON("/api/models").catch(() => ({ items: [] }));
  const found = (models.items || []).find(m => {
    const name = m.id || m.name || "";
    return name.includes(args) || args.includes(name);
  });
  if (!found) { toast("❌ 未找到模型：" + args, "err"); return "未找到模型：" + args + "。请用 /model 查看可用模型。"; }
  State.model_id = found.id || found.name;
  State.model = found.id || found.name;
  const chip = document.getElementById("modelChip");
  if (chip) chip.textContent = State.model;
  // 同步 modelSelect 下拉框
  const sel = document.getElementById("modelSelect");
  if (sel) { sel.value = State.model_id || ""; }
  toast("🤖 已切换到模型：" + State.model, "ok");
  // 联动：打开模型面板，高亮当前模型
  openPanel("models");
  // 高亮定位到当前模型（面板渲染后滚动并闪烁；选择器需为合法 CSS）
  setTimeout(() => highlightInPanel("models", ".card-row[data-model-id=\"" + (State.model_id || "") + "\"]"), 400);
  return "已切换到模型：" + State.model;
}, undefined, false);

reg("fast", "切换快速/深度思考模式，用法：/fast on|off", "model", async (args) => {
  const on = args === "on" || args === "1" || args === "true";
  const off = args === "off" || args === "0" || args === "false";
  if (!on && !off) {
    State.deep_think = !State.deep_think;
  } else {
    State.deep_think = !on;
  }
  const btn = document.getElementById("btnDeep");
  if (btn) btn.classList.toggle("on", !State.deep_think);
  const mode = State.deep_think ? "深度思考" : "快速模式";
  toast("⚡ 已切换到" + mode, "ok");
  // 联动：打开模型面板
  openPanel("models");
  return "已切换到" + mode + "。";
}, undefined, true);

reg("persona", "查看/切换人格配置，用法：/persona [人格描述]", "model", async (args) => {
  if (!args) {
    // 查看当前人格
    const data = await getJSON("/api/soul").catch(() => ({}));
    const enabled = data.enabled ? "已启用" : "未启用";
    const preview = (data.content || "").slice(0, 120) + (data.content && data.content.length > 120 ? "..." : "");
    return "Soul 人格（" + enabled + "）\n" + preview + "\n\n用法：/persona 人格描述——替换 SOUL.md 内容为指定人格描述\n（或打开 Soul 面板手动编辑）";
  }
  // 以 args 作为新人格描述，保存到 SOUL.md
  const r = await postJSON("/api/soul", { content: args, enabled: true }).catch(() => ({}));
  if (r.ok) {
    toast("🧠 已切换人格：" + args.slice(0, 40), "ok");
    openPanel("soul");
    return "已切换人格为：" + args + "\n（新会话生效）";
  }
  toast("❌ 人格切换失败", "err");
  openPanel("soul");
  return "人格切换失败，请打开 Soul 面板手动编辑。";
}, undefined, false);

// =====================================================================
// 工具控制
// =====================================================================
reg("tools", "查看工具集状态并打开工具面板，用法：/tools [list|enable|disable]", "tool", async (args) => {
  const data = await getJSON("/api/toolsets").catch(() => ({ items: [] }));
  const toolsets = data.items || [];
  if (args === "open") {
    if (openPanel("tools")) {
      toast("🔧 已打开工具面板", "ok");
      return "已打开工具面板。";
    }
    return "找不到工具面板。";
  }
  if (args === "list" || !args) {
    let lines = ["工具集状态（共 " + toolsets.length + " 个）："];
    for (const t of toolsets) {
      const enabled = t.enabled !== false;
      lines.push("  " + (enabled ? "✅" : "❌") + " " + (t.label || t.name || t.id || "?"));
    }
    if (!args) {
      if (openPanel("tools")) {
        if (typeof window.__showToolsTab === "function") window.__showToolsTab("manage");
        toast("🔧 已打开工具面板", "ok");
      }
      lines.push("\n提示：用 /toolscatalog 可查看完整工具清单。");
    }
    return lines.join("\n");
  }
  const parts = args.split(/\s+/);
  if (parts.length >= 2) {
    const action = parts[0];
    const name = parts.slice(1).join(" ");
    const target = toolsets.find(t => (t.name || t.id || "").toLowerCase().includes(name.toLowerCase()));
    if (!target) { toast("❌ 未找到工具集：" + name, "err"); return "未找到工具集：" + name; }
    const tid = target.id || target.name;
    await postJSON("/api/toolsets/toggle", { name: tid, disabled: action !== "enable" }).catch(() => {});
    const actionText = action === "enable" ? "启用" : "禁用";
    toast("🔧 已" + actionText + "工具集：" + name, "ok");
    openPanel("tools");
    // 触发工具面板数据刷新（统一工具面板：清单 + 管理）
    const { refreshPanels } = await import("./views.js");
    if (typeof refreshPanels === "function") await refreshPanels();
    // 高亮定位到目标工具（合法 CSS 属性选择器；:contains 为 jQuery 专有，querySelector 会抛错）
    setTimeout(() => highlightInPanel("tools", ".card-row[data-toolset=\"" + tid + "\"]"), 400);
    return "已" + actionText + "工具集：" + name;
  }
  return "用法：/tools list 或 /tools enable 名称 或 /tools disable 名称";
}, undefined, false);

reg("skills", "查看已安装的技能列表，用法：/skills [list|open]", "tool", async (args) => {
  if (args === "open") {
    openPanel("skills");
    toast("🧩 已打开技能面板", "ok");
    return "已打开技能面板。";
  }
  const data = await getJSON("/api/skills").catch(() => ({ items: [] }));
  const items = data.items || [];
  if (items.length === 0) {
    toast("📦 没有已安装的技能，打开技能面板安装", "info");
    openPanel("skills");
    return "没有已安装的技能。已打开技能面板，可前往安装。";
  }
  const lines = ["已安装技能："];
  for (const s of items) {
    lines.push("  📦 " + (s.name || s.id || "?") + (s.description ? " — " + s.description : ""));
  }
  lines.push("使用 /skills open 打开技能面板");
  return lines.join("\n");
}, undefined, false);

reg("web", "开关联网搜索，用法：/web on|off", "tool", async (args) => {
  const on = args === "on" || args === "1" || args === "true";
  const off = args === "off" || args === "0" || args === "false";
  if (on) State.web_search = true;
  else if (off) State.web_search = false;
  else State.web_search = !State.web_search;
  const btn = document.getElementById("btnWeb");
  if (btn) btn.classList.toggle("on", State.web_search);
  const status = State.web_search ? "已启用联网搜索" : "已禁用联网搜索";
  toast("🌐 " + status, "ok");
  // 联动：打开工具面板
  openPanel("tools");
  return status;
}, undefined, true);

reg("image", "开关图像生成，用法：/image on|off", "tool", async (args) => {
  const on = args === "on" || args === "1" || args === "true";
  const off = args === "off" || args === "0" || args === "false";
  if (on) State.image_gen = true;
  else if (off) State.image_gen = false;
  else State.image_gen = !State.image_gen;
  const status = State.image_gen ? "已启用图像生成" : "已禁用图像生成";
  toast("🖼️ " + status, "ok");
  return status;
}, undefined, true);

reg("browse", "开关浏览器工具，用法：/browse on|off", "tool", async (args) => {
  const on = args === "on" || args === "1" || args === "true";
  const off = args === "off" || args === "0" || args === "false";
  if (on) State.browse_tool = true;
  else if (off) State.browse_tool = false;
  else State.browse_tool = !State.browse_tool;
  const status = State.browse_tool ? "已启用浏览器工具" : "已禁用浏览器工具";
  toast("🌐 " + status, "ok");
  return status;
}, undefined, true);

reg("code", "开关代码执行工具，用法：/code on|off", "tool", async (args) => {
  const on = args === "on" || args === "1" || args === "true";
  const off = args === "off" || args === "0" || args === "false";
  if (on) State.code_tool = true;
  else if (off) State.code_tool = false;
  else State.code_tool = !State.code_tool;
  const status = State.code_tool ? "已启用代码执行" : "已禁用代码执行";
  toast("💻 " + status, "ok");
  return status;
}, undefined, true);

reg("shell", "开关 Shell 工具，用法：/shell on|off", "tool", async (args) => {
  const on = args === "on" || args === "1" || args === "true";
  const off = args === "off" || args === "0" || args === "false";
  if (on) State.shell_tool = true;
  else if (off) State.shell_tool = false;
  else State.shell_tool = !State.shell_tool;
  const status = State.shell_tool ? "已启用 Shell 工具" : "已禁用 Shell 工具";
  toast("🖥️ " + status, "ok");
  return status;
}, undefined, true);

// =====================================================================
// 信息查询
// =====================================================================
reg("search", "统一搜索（跨会话/Wiki/记忆/看板/定时任务），用法：/search 关键词", "info", async (args) => {
  if (typeof openUnifiedSearch === "function") openUnifiedSearch();
  else if (typeof Chat !== "undefined" && Chat.openUnifiedSearch) Chat.openUnifiedSearch();
  return "请在弹出的搜索框中输入关键词搜索（Ctrl+Shift+F）";
}, undefined, false);

reg("usage", "查看当前会话 token 用量和成本（估算）", "info", async () => {
  const { total, cny } = formatUsage(State.usage);
  const inp = (State.usage.input || 0).toLocaleString();
  const out = (State.usage.output || 0).toLocaleString();
  return "当前会话 token 用量（估算，非供应商账单）：\n" +
    "输入  " + inp + " tok\n" +
    "输出  " + out + " tok\n" +
    "合计  " + total.toLocaleString() + " tok\n" +
    "估算成本 ≈ ¥" + cny.toFixed(4);
}, undefined, true);

reg("help", "显示所有可用的斜杠命令（帮助模态框）", "info", async () => {
  showHelpModal();
  return "";
}, undefined, true);

reg("version", "查看当前版本信息", "info", async () => {
  const info = await getJSON("/healthz").catch(() => ({}));
  const ver = info.version || "?";
  const model = info.model || "未设置";
  return "Hermes Desktop 版本：" + ver + "\n" +
    "当前模型：" + model + "\n" +
    "内核状态：" + (info.importable ? "✅ 就绪" : "❌ 未安装");
}, undefined, false);

reg("status", "查看系统状态概览", "info", async () => {
  const info = await getJSON("/healthz").catch(() => ({}));
  const model = State.model || info.model || "未设置";
  const web = State.web_search ? "✅ 开" : "❌ 关";
  const think = State.deep_think ? "✅ 开" : "❌ 关";
  const convId = State.conv_id || "无";
  const tok = (State.usage.input || 0) + (State.usage.output || 0);
  return "系统状态概览：\n" +
    "模型：" + model + "\n" +
    "联网搜索：" + web + "\n" +
    "深度思考：" + think + "\n" +
    "当前会话：" + convId + "\n" +
    "本次会话 token：" + tok.toLocaleString();
}, undefined, false);

reg("debug", "输出诊断信息（可复制）", "info", async () => {
  const info = await getJSON("/healthz").catch(() => ({}));
  const models = await getJSON("/api/models").catch(() => ({ items: [] }));
  const tools = await getJSON("/api/toolsets").catch(() => ({}));
  const dump = {
    version: info.version || "?",
    model: State.model || info.model || "?",
    conv_id: State.conv_id || null,
    tokens: State.usage,
    model_count: (models.items || []).length,
    tool_count: ((tools.toolsets || tools.items || []).length),
    deep_think: State.deep_think,
    web_search: State.web_search,
  };
  return "诊断信息（可复制）：\n" + JSON.stringify(dump, null, 2);
}, undefined, false);

// =====================================================================
// 系统管理
// =====================================================================
reg("memory", "查看/写入/打开记忆面板，用法：/memory [内容|open]", "manage", async (args) => {
  if (args === "open") {
    openPanel("memory");
    // 聚焦到记忆面板的输入框
    setTimeout(() => {
      const inp = document.querySelector("#view-memory input, #view-memory textarea, #view-memory [contenteditable]");
      if (inp) inp.focus();
    }, 300);
    toast("🧠 已打开记忆面板", "ok");
    return "已打开记忆面板。";
  }
  if (!args) {
    const data = await getJSON("/api/memory").catch(() => ({ items: [] }));
    const items = data.items || [];
    if (items.length === 0) return "没有记忆。用 /memory 内容 来写入一条记忆。";
    const lines = ["记忆列表："];
    for (const m of items.slice(0, 10)) {
      lines.push("  🧠 " + (typeof m === "string" ? m : (m.content || m.text || JSON.stringify(m))));
    }
    if (items.length > 10) lines.push("  ... 及其他 " + (items.length - 10) + " 条");
    return lines.join("\n");
  }
  await postJSON("/api/memory", { content: args }).catch(() => {});
  toast("🧠 已写入记忆", "ok");
  return "已写入记忆：" + args;
}, undefined, false);

reg("plugins", "查看插件列表，用法：/plugins [list|open]", "manage", async (args) => {
  if (args === "open") {
    openPanel("plugins");
    toast("🧩 已打开插件面板", "ok");
    return "已打开插件面板。";
  }
  const data = await getJSON("/api/plugins").catch(() => ({ packages: [] }));
  const pkgs = data.packages || [];
  if (pkgs.length === 0) {
    toast("📦 没有插件，打开插件面板查看", "info");
    openPanel("plugins");
    return "没有插件。已打开插件面板。";
  }
  return "插件列表（共 " + pkgs.length + " 个）：\n" +
    pkgs.slice(0, 20).map(p => "  📦 " + (p.name || "?")).join("\n") +
    (pkgs.length > 20 ? "\n  ... 及其他 " + (pkgs.length - 20) + " 个" : "") +
    "\n使用 /plugins open 打开插件面板";
}, undefined, false);

reg("logs", "查看 Hermes 运行日志，用法：/logs [open]", "manage", async (args) => {
  if (args === "open") {
    if (openPanel("logs")) {
      toast("📜 已打开日志面板", "ok");
      return "已打开日志面板。";
    }
    return "找不到日志面板。";
  }
  const data = await getJSON("/api/logs").catch(() => ({ logs: [] }));
  const logs = data.logs || [];
  if (!logs.length) {
    if (openPanel("logs")) toast("📜 已打开日志面板", "ok");
    return "暂无日志信息，已打开日志面板查看。";
  }
  const lines = logs.map(l => "  📜 " + l.label + (l.exists ? "" : "（尚未生成）")).join("\n");
  if (openPanel("logs")) toast("📜 已打开日志面板", "ok");
  return "日志文件：\n" + lines + "\n使用 /logs open 打开日志面板";
}, undefined, false);

reg("structured", "触发结构化输出 / 离线校验 JSON，用法：/structured [open]", "manage", async (args) => {
  if (args === "open") {
    if (openPanel("structured")) {
      toast("🔣 已打开结构化输出面板", "ok");
      return "已打开结构化输出面板。";
    }
    return "找不到结构化输出面板。";
  }
  if (openPanel("structured")) toast("🔣 已打开结构化输出面板", "ok");
  return "结构化输出：把指令交给模型返回 JSON（可选 JSON Schema 校验），或离线校验一段 JSON。\n使用 /structured open 打开面板。";
}, undefined, false);

reg("toolscatalog", "查看工具清单，用法：/toolscatalog [open]", "tool", async (args) => {
  if (openPanel("tools")) {
    // 切换到「工具清单」子面板（统一工具面板内的只读清单）
    if (typeof window.__showToolsTab === "function") window.__showToolsTab("catalog");
    toast("🔧 已打开工具清单（统一工具面板）", "ok");
    return "工具清单：列出 Hermes 注册表中全部工具（name / 工具集 / 入参 / 来源）。\n使用 /toolscatalog open 打开面板。";
  }
  return "找不到工具面板。";
}, undefined, false);

reg("cron", "打开定时任务面板", "manage", async () => {
  if (openPanel("cron")) {
    toast("⏰ 已打开定时任务面板", "ok");
    return "已打开定时任务面板。";
  }
  return "找不到定时任务面板。";
}, undefined, true);

reg("kanban", "打开看板/循环面板", "manage", async () => {
  if (openPanel("kanban")) {
    toast("📋 已打开看板面板", "ok");
    return "已打开看板面板。";
  }
  // 降级到循环面板
  if (openPanel("loops")) {
    toast("🔄 已打开循环面板", "ok");
    return "已打开循环面板。";
  }
  return "找不到看板面板。";
}, undefined, true);

reg("reset", "重置所有设置（确认后执行）", "manage", async () => {
  if (!confirm("确定要重置所有设置吗？此操作不可撤销。")) {
    return "已取消重置。";
  }
  State.model = null;
  State.model_id = null;
  State.deep_think = false;
  State.web_search = false;
  State.image_gen = false;
  State.browse_tool = false;
  State.code_tool = false;
  State.shell_tool = false;
  State.conv_id = null;
  State.usage = { input: 0, output: 0 };
  State.messages = [];
  const conv = document.getElementById("chat");
  if (conv) conv.innerHTML = "";
  const btnDeep = document.getElementById("btnDeep");
  if (btnDeep) btnDeep.classList.remove("on");
  const btnWeb = document.getElementById("btnWeb");
  if (btnWeb) btnWeb.classList.remove("on");
  const chip = document.getElementById("modelChip");
  if (chip) chip.textContent = "未选择";
  toast("🔄 已重置所有设置", "ok");
  return "已重置所有设置。";
}, undefined, true);

reg("compress", "压缩上下文窗口（释放 Token 空间）", "manage", async () => {
  // 提示用户压缩上下文
  if (!State.conv_id) { toast("❌ 当前没有活动会话", "err"); return "当前没有活动会话。"; }
  const r = await postJSON("/api/conversations/" + encodeURIComponent(State.conv_id) + "/compress", {})
    .catch(() => ({ ok: false }));
  if (r.ok) {
    toast("🗜️ 上下文已压缩", "ok");
    return "上下文已压缩，Token 空间已释放。";
  }
  toast("⚠️ 后端不支持压缩，将清空历史消息", "warn");
  // 降级：清空当前显示的上下文
  const conv = document.getElementById("chat");
  if (conv) {
    const bubbles = conv.querySelectorAll(".msg-row");
    // 保留最后一条用户消息+AI回复
    const keep = 2;
    for (let i = 0; i < bubbles.length - keep; i++) {
      bubbles[i].remove();
    }
  }
  return "上下文已压缩（保留最近一轮对话）。";
}, undefined, false);


// =====================================================================
// 面板导航（新）
// =====================================================================
// 小补全：/compact（/compress 别名）、/theme（明暗切换）、/workspace（工作区）
reg("compact", "压缩上下文窗口（/compress 的别名）", "manage", async () => {
  const c = findCommand("/compress");
  if (c && c.handler) return c.handler("");
  toast("⚠️ 无法执行压缩", "warn");
  return "压缩命令不可用。";
}, undefined, true);

reg("theme", "切换明暗主题", "model", async () => {
  toggleTheme();
  const dark = State.theme === "dark";
  toast(dark ? "🌙 已切换到深色主题" : "☀️ 已切换到浅色主题", "ok");
  return dark ? "已切换到深色主题。" : "已切换到浅色主题。";
}, undefined, true);

reg("workspace", "打开工作区文件浏览器", "manage", async () => {
  if (openPanel("workspace")) {
    toast("📁 已打开工作区", "ok");
    return "已打开工作区文件浏览器。";
  }
  return "找不到工作区面板。";
}, undefined, true);

reg("mcp", "打开 MCP 面板", "manage", async () => {
  if (openPanel("mcp")) {
    toast("⚙️ 已打开 MCP 面板", "ok");
    return "已打开 MCP 面板。";
  }
  return "找不到 MCP 面板。";
}, undefined, true);

reg("wiki", "打开 LLM Wiki 知识库面板", "manage", async () => {
  if (openPanel("wiki")) {
    toast("📚 已打开知识库面板", "ok");
    return "已打开知识库面板。";
  }
  return "找不到知识库面板。";
}, undefined, true);

reg("channel", "打开远程渠道面板", "manage", async () => {
  if (openPanel("channels")) {
    toast("📡 已打开远程渠道面板", "ok");
    return "已打开远程渠道面板。";
  }
  return "找不到远程渠道面板。";
}, undefined, true);

reg("loops", "打开循环框架面板", "manage", async () => {
  if (openPanel("loops")) {
    toast("🔄 已打开循环面板", "ok");
    return "已打开循环面板。";
  }
  return "找不到循环面板。";
}, undefined, true);

reg("delegate", "打开委派面板", "manage", async () => {
  if (openPanel("delegation")) {
    toast("👥 已打开委派面板", "ok");
    return "已打开委派面板。";
  }
  return "找不到委派面板。";
}, undefined, true);

reg("sysprompt", "打开系统提示词面板", "manage", async () => {
  if (openPanel("sysprompt")) {
    toast("⚙️ 已打开系统提示词面板", "ok");
    return "已打开系统提示词面板。";
  }
  return "找不到系统提示词面板。";
}, undefined, true);

reg("analytics", "打开用量分析面板", "manage", async () => {
  try {
    const { openAnalytics } = await import("./panels.js");
    if (typeof openAnalytics === "function") {
      openAnalytics();
      toast("📊 已打开用量分析面板", "ok");
      return "已打开用量分析面板。";
    }
  } catch (_) {}
  return "用量分析面板不可用。";
}, undefined, true);

// =====================================================================
// 内部工具
// =====================================================================
function updateUsageChip() {
  const chip = document.getElementById("usageChip");
  if (!chip) return;
  const { total, cny } = formatUsage(State.usage);
  chip.textContent = "📊 " + total.toLocaleString() + " tok"
    + (total ? " · ¥" + cny.toFixed(4) + "（估算）" : "");
}

// ------------------------------------------------------------------ 帮助模态框
let _helpModal = null;

function buildHelpModal() {
  const mask = el("div", { class: "cmd-help-mask hidden", id: "cmdHelpMask" }, [
    el("div", { class: "cmd-help-modal" }, [
      el("div", { class: "cmd-help-head" }, [
        el("span", { class: "cmd-help-title", text: "📖 斜杠命令参考" }),
        el("button", { class: "cmd-help-close", text: "✕",
          onclick: () => mask.classList.add("hidden") }),
      ]),
      el("div", { class: "cmd-help-body" }),
    ]),
  ]);
  mask.addEventListener("click", (e) => {
    if (e.target === mask) mask.classList.add("hidden");
  });
  document.body.appendChild(mask);
  return mask;
}

function showHelpModal() {
  if (!_helpModal || !document.body.contains(_helpModal)) {
    _helpModal = buildHelpModal();
  }
  const body = _helpModal.querySelector(".cmd-help-body");
  body.innerHTML = "";
  const catOrder = ["session", "model", "tool", "info", "manage"];
  for (const catKey of catOrder) {
    const cat = CATEGORIES[catKey];
    let cmds = COMMANDS.filter(c => c.category === catKey);
    if (catKey === "manage" && _dynamicCommands && _dynamicCommands.length > 0) {
      cmds = cmds.concat(_dynamicCommands);
    }
    if (cmds.length === 0) continue;
    const section = el("div", { class: "cmd-help-section" }, [
      el("div", { class: "cmd-help-cat", text: cat.icon + " " + cat.label }),
    ]);
    for (const c of cmds) {
      const usage = c.usage ? " " + c.usage : "";
      const row = el("div", { class: "cmd-help-row" }, [
        el("code", { class: "cmd-help-cmd", text: "/" + c.id }),
        el("span", { class: "cmd-help-desc", text: c.desc }),
        usage ? el("span", { class: "cmd-help-usage", text: usage }) : null,
      ]);
      section.appendChild(row);
    }
    body.appendChild(section);
  }
  // 底部提示
  body.appendChild(el("div", { class: "cmd-help-footer", text: "💡 在输入框中输入 / 可触发命令补全 · ↑↓ 导航 · Enter 执行 · ESC 关闭" }));
  _helpModal.classList.remove("hidden");
  // ESC 关闭
  const onKey = (e) => {
    if (e.key === "Escape") {
      _helpModal.classList.add("hidden");
      document.removeEventListener("keydown", onKey);
    }
  };
  document.addEventListener("keydown", onKey);
}

// =====================================================================
// 核心 API
// =====================================================================

/** 获取所有命令定义 */
export function getCommands() {
  return COMMANDS.slice();
}

/** 按分类获取命令 */
export function getCommandsByCategory() {
  const result = {};
  for (const c of COMMANDS) {
    if (!result[c.category]) result[c.category] = [];
    result[c.category].push(c);
  }
  return result;
}

/** 根据前缀获取补全建议 */
export function getCompletions(prefix) {
  if (!prefix || !prefix.startsWith("/")) return [];
  const query = prefix.slice(1).toLowerCase();
  let all = COMMANDS.slice();
  // 合并动态命令
  if (_dynamicCommands) {
    all = all.concat(_dynamicCommands);
  }
  if (!query) return all;
  return all.filter(c => c.id.toLowerCase().includes(query));
}

/** 根据完整命令文本查找匹配的命令 */
export function findCommand(text) {
  if (!text || !text.startsWith("/")) return null;
  const parts = text.slice(1).split(/\s+/);
  const cmdId = parts[0].toLowerCase();
  const found = COMMANDS.find(c => c.id.toLowerCase() === cmdId);
  if (found) return found;
  // 在动态命令中查找
  if (_dynamicCommands) {
    return _dynamicCommands.find(c => c.id.toLowerCase() === cmdId) || null;
  }
  return null;
}

/** 提取命令参数 */
export function extractArgs(text) {
  if (!text || !text.startsWith("/")) return "";
  const rest = text.slice(1).trim();
  const idx = rest.indexOf(" ");
  if (idx < 0) return "";
  return rest.slice(idx + 1).trim();
}

/** 执行命令，返回结果文本 */
export async function executeCommand(text) {
  const cmd = findCommand(text);
  if (!cmd) return null;
  const args = extractArgs(text);
  try {
    const result = await cmd.handler(args);
    return result;
  } catch (e) {
    toast("❌ 执行失败：" + (e.message || e), "err");
    return "执行失败：" + (e.message || e);
  }
}

/** 是否可能是已知命令（用于快速判断是否拦截） */
export function isKnownCommand(text) {
  return findCommand(text) !== null;
}

/** 检查命令是否仅前端执行 */
export function isLocalCommand(text) {
  const cmd = findCommand(text);
  return cmd ? cmd.localOnly : false;
}