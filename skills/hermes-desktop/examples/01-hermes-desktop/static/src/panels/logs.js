// @ts-check
/* =====================================================================
 * logs.js — 日志面板子模块（只读查看 Hermes 日志）
 *   对齐真实 Hermes 的 `hermes logs`：列出 <HERMES_HOME>/logs/ 下已知日志，
 *   可按级别 / 组件 / 会话 / 时间过滤查看末尾内容。仅读取，不写不删。
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { getJSON } from "../api.js";

let _logsBody = null;     // 面板 body（重渲染用）
let _allLogs = [];        // /api/logs 返回的全部日志元信息
let _currentName = "agent";

// 级别配色（内联，避免额外改 CSS）
const LEVEL_COLOR = {
  DEBUG: "#8a8f98", INFO: "#3b82f6", WARNING: "#e0a106",
  ERROR: "#e5484d", CRITICAL: "#b5179e",
};

function _levelOf(line) {
  const m = /\s(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s/.exec(line);
  return m ? m[1] : null;
}

// 去掉 ANSI 转义码（颜色、清屏、光标移动）和破坏性控制字符，
// 只保留可打印字符与换行/制表符。后端已清理，前端再做最后一道防御。
function _sanitizeLine(line) {
  if (typeof line !== "string") line = String(line);
  return line
    .replace(/\x1b\[[0-9;]*[A-Za-z]/g, "")
    .replace(/[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]/g, "")
    .replace(/\r/g, "");
}

function _renderLine(line) {
  const clean = _sanitizeLine(line);
  const lv = _levelOf(clean);
  const span = el("span", { class: "log-line", text: clean || " " });
  if (lv && LEVEL_COLOR[lv]) span.style.color = LEVEL_COLOR[lv];
  return span;
}

export async function renderLogsPanel(body) {
  _logsBody = body;
  body.innerHTML = "";

  // 顶部说明（如实）
  const intro = el("div", { class: "muted small", style: "margin-bottom:10px;" }, [
    "Hermes 把运行日志写在数据目录的 logs/ 下（与真实内核一致）。日志在运行时才生成；",
    el("b", { text: "密钥已被脱敏，不会写入磁盘" }), "。本面板仅读取，不会修改或删除任何日志。",
  ]);
  body.appendChild(intro);

  // 日志文件选择区
  const fileRow = el("div", { class: "log-file-row" });
  body.appendChild(fileRow);

  // 过滤区
  const levelSel = el("select", { class: "form-input log-filter" }, [
    el("option", { value: "", text: "全部级别" }),
    el("option", { value: "DEBUG", text: "DEBUG" }),
    el("option", { value: "INFO", text: "INFO" }),
    el("option", { value: "WARNING", text: "WARNING" }),
    el("option", { value: "ERROR", text: "ERROR" }),
    el("option", { value: "CRITICAL", text: "CRITICAL" }),
  ]);
  const compSel = el("select", { class: "form-input log-filter" }, [
    el("option", { value: "", text: "全部组件" }),
    el("option", { value: "gateway", text: "gateway" }),
    el("option", { value: "agent", text: "agent" }),
    el("option", { value: "tools", text: "tools" }),
    el("option", { value: "cli", text: "cli" }),
    el("option", { value: "cron", text: "cron" }),
    el("option", { value: "gui", text: "gui" }),
  ]);
  const linesInput = el("input", { class: "form-input log-filter", type: "number",
    min: "10", max: "2000", value: "200", style: "width:90px;",
    title: "显示的末尾行数" });
  const sessionInput = el("input", { class: "form-input log-filter",
    placeholder: "会话 ID（可选）", style: "width:150px;" });
  const sinceInput = el("input", { class: "form-input log-filter",
    placeholder: "1h / 30m / 2d", style: "width:110px;",
    title: "只看该时间之后的行（可选）" });
  const refreshBtn = el("button", { class: "btn primary", text: "刷新" });

  const filterBar = el("div", { class: "log-filter-bar" }, [
    el("span", { class: "muted small", text: "级别" }), levelSel,
    el("span", { class: "muted small", text: "组件" }), compSel,
    el("span", { class: "muted small", text: "行数" }), linesInput,
    el("span", { class: "muted small", text: "会话" }), sessionInput,
    el("span", { class: "muted small", text: "时间" }), sinceInput,
    refreshBtn,
  ]);
  body.appendChild(filterBar);

  // 日志内容区
  const pre = el("pre", { class: "log-view" });
  body.appendChild(pre);

  async function loadView() {
    if (!_currentName) return;
    const q = new URLSearchParams({
      lines: String(parseInt(linesInput.value || "200", 10) || 200),
      level: levelSel.value, component: compSel.value,
      session: sessionInput.value, since: sinceInput.value,
    });
    const d = await getJSON("/api/logs/" + encodeURIComponent(_currentName) + "?" + q.toString())
      .catch(() => ({ ok: false, error: "网络错误" }));
    pre.innerHTML = "";
    if (!d || !d.ok) {
      pre.appendChild(el("div", { class: "muted", text: "加载失败：" + (d && d.error || "") }));
      return;
    }
    if (!d.exists) {
      pre.appendChild(el("div", { class: "muted", text: d.note || "该日志文件尚不存在（日志在运行时才会生成）。" }));
      return;
    }
    const lines = d.lines || [];
    if (!lines.length) {
      pre.appendChild(el("div", { class: "muted", text: "没有匹配的行。" }));
    } else {
      for (const ln of lines) pre.appendChild(_renderLine(ln));
    }
    const meta = el("div", { class: "muted small", style: "margin-top:6px;",
      text: `共 ${d.count} 行` +
        (d.level ? ` · 级别≥${d.level}` : "") +
        (d.component ? ` · 组件=${d.component}` : "") +
        (d.since ? ` · 时间≥${d.since}` : "") +
        (d.session ? ` · 会话=${d.session}` : "") });
    pre.appendChild(meta);
  }

  // 文件选择按钮（基于 /api/logs 列表）
  async function loadFiles() {
    const d = await getJSON("/api/logs").catch(() => ({ ok: false, error: "网络错误" }));
    fileRow.innerHTML = "";
    _allLogs = (d && d.logs) || [];
    if (!_allLogs.length) {
      fileRow.appendChild(el("div", { class: "muted", text: "暂无日志信息。" }));
      return;
    }
    // 默认选中第一个"存在"的日志，否则第一个
    let firstExisting = _allLogs.find((x) => x.exists);
    _currentName = (firstExisting || _allLogs[0]).name;
    for (const lg of _allLogs) {
      const sizeStr = lg.size < 1024 ? (lg.size + "B")
        : lg.size < 1024 * 1024 ? (lg.size / 1024).toFixed(1) + "KB"
        : (lg.size / 1024 / 1024).toFixed(1) + "MB";
      const btn = el("button", {
        class: "btn ghost log-file-btn" + (lg.name === _currentName ? " active" : ""),
        title: lg.label + "（" + lg.condition + "）",
        onclick: () => {
          _currentName = lg.name;
          $$(".log-file-btn", fileRow).forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          loadView();
        },
      }, [
        el("span", { text: lg.label }),
        el("span", { class: "muted small", text: lg.exists ? (" · " + sizeStr) : " · 未生成" }),
      ]);
      fileRow.appendChild(btn);
    }
    await loadView();
  }

  refreshBtn.addEventListener("click", loadView);
  // 回车即刷新（会话/时间输入框）
  [sessionInput, sinceInput, linesInput].forEach((inp) =>
    inp.addEventListener("keydown", (e) => { if (e.key === "Enter") loadView(); }));

  await loadFiles();
}
