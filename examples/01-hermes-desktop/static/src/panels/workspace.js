// @ts-check
/* =====================================================================
 * workspace.js — workspace 面板子模块
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { State } from "../state.js";
import { getJSON, postJSON, delJSON, parseSSE } from "../api.js";
import * as Views from "../views.js";
// ------------------------------------------------------------------ 工作区文件浏览器（G4）
// 受限目录浏览：仅能访问「授权根」（默认=应用目录+主目录+常见目录，可自定义）。
// 左侧可展开目录树（懒加载），右侧为目录内容网格 / 文件预览编辑；支持新建/重命名/
// 删除/下载/附加到聊天。所有后端路径均受根约束，越界返回 403。
let _wsState = { roots: [], nodes: {}, current: null };

function _wsKey(root, rel) { return root.path + "::" + (rel || ""); }

export async function renderWorkspacePanel(body) {
  body.innerHTML = "";
  const wrap = el("div", { class: "ws" });
  const treeCol = el("div", { class: "ws-tree" });
  const treeHead = el("div", { class: "ws-tree-head" }, [
    el("span", { text: "📂 工作区" }),
    el("button", { class: "btn ghost sm", title: "把一个本机目录加入授权列表", text: "＋ 授权目录",
      onclick: wsAddRootDialog }),
  ]);
  const rootsEl = el("div", { class: "ws-roots", id: "wsRoots" });
  treeCol.appendChild(treeHead);
  treeCol.appendChild(rootsEl);

  const mainCol = el("div", { class: "ws-main" });
  const bar = el("div", { class: "ws-bar" });
  const crumb = el("div", { class: "ws-crumb", id: "wsCrumb" });
  const tools = el("div", { class: "ws-tools" }, [
    el("button", { class: "btn ghost sm", text: "📁 新建文件夹", onclick: () => wsNewFolder() }),
    el("button", { class: "btn ghost sm", text: "📄 新建文件", onclick: () => wsNewFile() }),
    el("button", { class: "btn ghost sm", text: "🔄 刷新", onclick: () => wsRefresh() }),
    el("button", { class: "btn ghost sm", text: "📌 固定为对话上下文", title: "把当前打开的文件夹绑定为当前会话的固定背景，之后每轮自动注入",
      onclick: () => wsBindContext() }),
  ]);
  bar.appendChild(crumb);
  bar.appendChild(tools);
  const content = el("div", { class: "ws-content", id: "wsContent" });
  mainCol.appendChild(bar);
  mainCol.appendChild(content);

  wrap.appendChild(treeCol);
  wrap.appendChild(mainCol);
  body.appendChild(wrap);
  _wsState.nodes = {};
  await wsLoadRoots();
}

async function wsLoadRoots() {
  const rootsEl = $("#wsRoots");
  if (!rootsEl) return;
  rootsEl.innerHTML = "<div class='muted'>加载授权目录…</div>";
  let r;
  try { r = await getJSON("/api/workspace/roots"); }
  catch (e) {
    rootsEl.innerHTML = "";
    rootsEl.appendChild(el("div", { class: "muted", text: "加载失败：" + e.message }));
    return;
  }
  _wsState.roots = (r.roots || []).map((x) => ({ ...x }));
  rootsEl.innerHTML = "";
  if (!_wsState.roots.length) {
    rootsEl.appendChild(el("div", { class: "muted", text: "暂无授权目录" }));
    return;
  }
  for (const root of _wsState.roots) {
    rootsEl.appendChild(wsRootNode(root));
  }
  const first = _wsState.roots[0];
  if (first) {
    const node = _wsState.nodes[_wsKey(first, "")];
    if (node) wsToggleNode(node);
    await wsOpenDir(first, "");
  }
}

function wsRootNode(root) {
  const item = el("div", { class: "ws-node ws-root-node" });
  const toggle = el("span", { class: "ws-toggle", text: "▸" });
  const label = el("span", { class: "ws-node-label", text: "📂 " + root.label });
  const childrenBox = el("div", { class: "ws-node-children hidden" });
  item.appendChild(toggle);
  item.appendChild(label);
  if (root.custom) {
    item.appendChild(el("button", { class: "ws-node-del", title: "移除授权", text: "×",
      onclick: (ev) => { ev.stopPropagation(); wsRemoveRoot(root); } }));
  }
  item.appendChild(childrenBox);
  const node = { root, rel: "", isRoot: true, toggle, childrenBox, expanded: false, loaded: false };
  _wsState.nodes[_wsKey(root, "")] = node;
  toggle.addEventListener("click", (ev) => { ev.stopPropagation(); wsToggleNode(node); });
  label.addEventListener("click", () => { wsOpenDir(root, ""); });
  return item;
}

function wsToggleNode(node) {
  node.expanded = !node.expanded;
  node.toggle.textContent = node.expanded ? "▾" : "▸";
  node.childrenBox.classList.toggle("hidden", !node.expanded);
  if (node.expanded && !node.loaded) wsLoadChildren(node);
}

async function wsLoadChildren(node) {
  node.loaded = true;
  node.childrenBox.innerHTML = "<div class='muted'>读取中…</div>";
  let r;
  try {
    r = await getJSON("/api/workspace/list?root=" + encodeURIComponent(node.root.path) +
      "&path=" + encodeURIComponent(node.rel));
  } catch (e) {
    node.childrenBox.innerHTML = "";
    node.childrenBox.appendChild(el("div", { class: "muted", text: "读取失败：" + e.message }));
    return;
  }
  const entries = r.entries || [];
  node.childrenBox.innerHTML = "";
  if (!entries.length) {
    node.childrenBox.appendChild(el("div", { class: "muted", text: "（空目录）" }));
    return;
  }
  for (const e of entries) {
    if (e.is_dir) node.childrenBox.appendChild(wsDirNode(node.root, e.rel, e.name.replace(/\/$/, "")));
  }
}

function wsDirNode(root, rel, name) {
  const item = el("div", { class: "ws-node ws-dir-node" });
  const toggle = el("span", { class: "ws-toggle", text: "▸" });
  const label = el("span", { class: "ws-node-label", text: "📁 " + name });
  const childrenBox = el("div", { class: "ws-node-children hidden" });
  item.appendChild(toggle); item.appendChild(label); item.appendChild(childrenBox);
  const node = { root, rel, isRoot: false, toggle, childrenBox, expanded: false, loaded: false };
  _wsState.nodes[_wsKey(root, rel)] = node;
  toggle.addEventListener("click", (ev) => { ev.stopPropagation(); wsToggleNode(node); });
  label.addEventListener("click", () => { wsOpenDir(root, rel); });
  return item;
}

function wsFileLeaf(root, rel, name) {
  const item = el("div", { class: "ws-node ws-file-leaf" });
  item.appendChild(el("span", { class: "ws-toggle", text: "·" }));
  item.appendChild(el("span", { class: "ws-node-label", text: "📄 " + name }));
  item.addEventListener("click", () => wsOpenFile(root, rel));
  return item;
}

async function wsOpenDir(root, rel) {
  _wsState.current = { root, rel, is_dir: true };
  wsUpdateCrumb(root, rel);
  const content = $("#wsContent");
  if (!content) return;
  content.innerHTML = '<div class="ws-skeleton" style="padding:16px;"><div style="height:16px;background:#eee;border-radius:4px;margin-bottom:12px;width:40%;"></div>' +
        '<div style="height:12px;background:#f0f0f0;border-radius:4px;margin-bottom:8px;width:90%;"></div>' +
        '<div style="height:12px;background:#f0f0f0;border-radius:4px;margin-bottom:8px;width:85%;"></div>' +
        '<div style="height:12px;background:#f0f0f0;border-radius:4px;margin-bottom:8px;width:70%;"></div>' +
        '<div style="height:12px;background:#f0f0f0;border-radius:4px;width:60%;"></div></div>';
  let r;
  try {
    r = await getJSON("/api/workspace/list?root=" + encodeURIComponent(root.path) +
      "&path=" + encodeURIComponent(rel));
  } catch (e) {
    content.innerHTML = "";
    content.appendChild(el("div", { class: "muted", text: "读取失败：" + e.message }));
    return;
  }
  content.innerHTML = "";
  content.appendChild(el("div", { class: "ws-dir-head",
    text: "📁 " + (rel || root.label) + "  （" + (r.entries || []).length + " 项）" }));
  // 搜索过滤
  const filterBar = el("div", { class: "ws-filter-bar", style: "margin:8px 0;display:flex;gap:8px;align-items:center;" });
  const filterInput = el("input", { class: "ws-filter-input", type: "text", placeholder: "🔍 过滤文件…", style: "flex:1;padding:4px 8px;border:1px solid #ddd;border-radius:4px;font-size:13px;",
    oninput: () => {
      const q = filterInput.value.toLowerCase().trim();
      grid.querySelectorAll(".ws-file-row").forEach(row => {
        const name = row.querySelector(".ws-file-name")?.textContent?.toLowerCase() || "";
        row.style.display = !q || name.includes(q) ? "" : "none";
      });
    } });
  const sortSel = el("select", { class: "ws-sort-select", style: "padding:4px 8px;border:1px solid #ddd;border-radius:4px;font-size:13px;",
    onchange: () => { const cur = _wsState.current; if (cur) wsOpenDir(cur.root, cur.rel); } }, [
    el("option", { value: "name", text: "按名称" }),
    el("option", { value: "size", text: "按大小" }),
    el("option", { value: "time", text: "按时间" }),
  ]);
  filterBar.appendChild(filterInput);
  filterBar.appendChild(sortSel);
  content.appendChild(filterBar);
  const batchBar = el("div", { class: "ws-batch-bar", style: "display:none;margin:6px 0;padding:6px 10px;background:var(--accent-soft,#e8f0fe);border-radius:6px;align-items:center;gap:8px;font-size:13px;" });
  const batchSel = el("span", { class: "ws-batch-count", text: "已选 0 项" });
  const batchBtn0 = el("button", { class: "btn ghost sm", text: "☑ 全选", onclick: () => wsBatchToggleAll(grid, true) });
  const batchBtn1 = el("button", { class: "btn ghost sm", text: "☐ 取消全选", onclick: () => wsBatchToggleAll(grid, false) });
  const batchBtn2 = el("button", { class: "btn ghost sm", text: "📎 批量附加", onclick: () => wsBatchAttach(grid, root) });
  const batchBtn3 = el("button", { class: "btn ghost sm danger", text: "🗑 批量删除", onclick: () => wsBatchDelete(grid, root) });
  batchBar.append(batchSel, batchBtn0, batchBtn1, batchBtn2, batchBtn3);
  content.appendChild(batchBar);
  const entries = r.entries || [];
  const grid = el("div", { class: "ws-grid", _entries: entries, _root: root });
  grid._batchBar = batchBar; grid._batchSel = batchSel;
  if (!entries.length) {
    var emptyBox = el("div", { style: "text-align:center;padding:40px 20px;color:#999;" }, [
      el("div", { style: "font-size:48px;margin-bottom:12px;", text: "📂" }),
      el("div", { style: "font-size:14px;", text: "此目录为空" }),
      el("div", { style: "font-size:12px;margin-top:6px;color:#bbb;", text: "点击上方「新建文件」或「新建文件夹」开始" }),
    ]);
    grid.appendChild(emptyBox);
  }
  for (const e of entries) {
    const row = el("div", { class: "ws-file-row" });
    row.addEventListener("contextmenu", (ev) => { ev.preventDefault(); ev.stopPropagation(); wsShowContextMenu(ev, root, e.rel, e.is_dir); });
    const cb = el("input", { type: "checkbox", class: "ws-file-cb", style: "margin:0 6px 0 0;cursor:pointer;display:none;",
      onchange: () => wsUpdateBatchBar() });
    const name = el("div", { class: "ws-file-name" }, [cb,
      el("span", { class: "ws-file-ic", text: e.is_dir ? "📁" : wsFileIcon(e.name) }),
      el("span", { text: e.name.replace(/\/$/, "") }),
      e.is_git ? el("span", { class: "ws-git-badge", title: "Git 仓库", text: "⌥git" }) : null,
    ]);
    name.addEventListener("click", () => e.is_dir ? wsOpenDir(root, e.rel) : wsOpenFile(root, e.rel));
    row.appendChild(name);
    row.appendChild(el("div", { class: "ws-file-meta",
      text: wsFmtSize(e.size) + (e.mtime ? " · " + wsFmtTime(e.mtime) : "") }));
    const acts = el("div", { class: "ws-file-acts" });
    if (!e.is_dir) {
      acts.appendChild(el("button", { class: "btn ghost xs", text: "附加", title: "作为附件发给 AI",
        onclick: (ev) => { ev.stopPropagation(); wsAttach(root, e.rel); } }));
      acts.appendChild(el("button", { class: "btn ghost xs", text: "下载",
        onclick: (ev) => { ev.stopPropagation(); wsDownload(root, e.rel); } }));
    }
    if (e.is_dir) {
      acts.appendChild(el("button", { class: "btn ghost xs", text: "📌 设为上下文", title: "绑定为当前会话固定文件夹上下文",
        onclick: (ev) => { ev.stopPropagation(); wsBindContext({ root, rel: e.rel }); } }));
    }
    // 低频操作合并到"更多"菜单
    const moreBtn = el("button", { class: "btn ghost xs", text: "⋯更多",
      onclick: (ev) => { ev.stopPropagation(); wsShowMoreMenu(ev.target, root, e.rel, e.is_dir); } });
    acts.appendChild(moreBtn);
    row.appendChild(acts);
    grid.appendChild(row);
  }
  content.appendChild(grid);
}

async function wsOpenFile(root, rel) {
  _wsState.current = { root, rel, is_dir: false };
  wsUpdateCrumb(root, rel);
  const content = $("#wsContent");
  if (!content) return;
  content.innerHTML = "<div class='muted'>读取中…</div>";
  let r;
  try {
    r = await getJSON("/api/workspace/read?root=" + encodeURIComponent(root.path) +
      "&path=" + encodeURIComponent(rel));
  } catch (e) {
    content.innerHTML = "";
    content.appendChild(el("div", { class: "muted", text: "读取失败：" + e.message }));
    return;
  }
  content.innerHTML = "";
  if (!r.is_text) {
    content.appendChild(el("div", { class: "ws-preview-nontext" }, [
      el("div", { text: "📦 " + (r.path || rel) + (r.too_large ? "（文件过大，仅可下载）" : "（二进制文件，不可预览）") }),
      el("button", { class: "btn primary", text: "⬇ 下载", onclick: () => wsDownload(root, rel) }),
    ]));
    return;
  }
  const code = r.content || "";
  const pre = el("pre", { class: "ws-editor", style: "margin:0;padding:12px;overflow:auto;flex:1;background:#f8f9fa;border:1px solid #e0e0e0;border-radius:4px;font:13px/1.6 'Cascadia Code','Fira Code','Consolas',monospace;white-space:pre;tab-size:2;" });
  const codeEl = el("code", { style: "font:inherit;color:#333;" });
  codeEl.innerHTML = wsHighlight(code);
  pre.appendChild(codeEl);
  const ta = el("textarea", { class: "ws-editor", spellcheck: "false", style: "display:none;flex:1;padding:12px;font:13px/1.6 'Cascadia Code','Consolas',monospace;resize:none;border:1px solid #e0e0e0;border-radius:4px;tab-size:2;" });
  ta.value = code;
  const saveBtn = el("button", { class: "btn ghost sm hidden", text: "💾 保存",
    onclick: () => wsSave(root, rel, ta.value) });
  const bar = el("div", { class: "ws-editor-bar" }, [
    el("span", { class: "muted", text: rel }),
    el("button", { class: "btn ghost sm", text: "✏ 编辑",
      onclick: () => { pre.style.display = "none"; ta.style.display = ""; ta.readOnly = false; ta.focus(); saveBtn.classList.remove("hidden"); } }),
    saveBtn,
    el("button", { class: "btn ghost sm", text: "🔍 预览",
      onclick: () => { ta.style.display = "none"; pre.style.display = ""; } }),
    el("button", { class: "btn ghost sm", text: "附加到聊天", onclick: () => wsAttach(root, rel) }),
    el("button", { class: "btn ghost sm", text: "下载", onclick: () => wsDownload(root, rel) }),
    el("button", { class: "btn ghost sm danger", text: "重命名", onclick: () => wsRename(root, rel) }),
    el("button", { class: "btn ghost sm danger", text: "删除", onclick: () => wsDelete(root, rel, false) }),
  ]);
  content.appendChild(bar);
  content.appendChild(pre);
  content.appendChild(ta);
}

function wsUpdateCrumb(root, rel) {
  const crumb = $("#wsCrumb");
  if (!crumb) return;
  crumb.innerHTML = "";
  crumb.appendChild(el("span", { class: "ws-crumb-root", text: "📂 " + root.label,
    onclick: () => wsOpenDir(root, "") }));
  if (rel) {
    const parts = rel.split("/");
    let acc = "";
    for (const p of parts) {
      acc = acc ? acc + "/" + p : p;
      crumb.appendChild(el("span", { class: "ws-crumb-sep", text: " / " }));
      crumb.appendChild(el("span", { class: "ws-crumb-part", text: p,
        onclick: () => wsOpenDir(root, acc) }));
    }
  }
}

async function wsSave(root, rel, content) {
  try {
    await postJSON("/api/workspace/write", { root: root.path, path: rel, content });
    toast("已保存 " + rel, "ok");
  } catch (e) { toast("保存失败：" + e.message, "err"); }
}

async function wsNewFolder() {
  const cur = _wsState.current;
  if (!cur) { toast("请先在左侧选择一个目录", "warn"); return; }
  // Bug D: 如果当前打开的是文件，取其父目录；否则保底用根目录
  const base = cur.is_dir ? cur.rel : (cur.rel ? cur.rel.includes("/") ? cur.rel.slice(0, cur.rel.lastIndexOf("/")) : "" : "");
  const name = window.prompt("新建文件夹名称：", "新建文件夹");
  if (!name) return;
  const rel = (base ? base + "/" : "") + name.trim();
  try {
    await postJSON("/api/workspace/mkdir", { root: cur.root.path, path: rel });
    toast("已创建 " + rel, "ok");
    // Bug D: 创建后打开父目录（而非未知状态）
    _wsState.current = { root: cur.root, rel: base, is_dir: true };
    await wsOpenDir(cur.root, base);
  } catch (e) { toast("创建失败：" + e.message, "err"); }
}

async function wsNewFile() {
  const cur = _wsState.current;
  if (!cur || !cur.is_dir) { toast("请先在左侧选择一个目录", "warn"); return; }
  const name = window.prompt("新建文件名称：", "新建文件.txt");
  if (!name) return;
  const rel = (cur.rel ? cur.rel + "/" : "") + name.trim();
  // 检查是否已存在
  try {
    const r = await getJSON("/api/workspace/list?root=" + encodeURIComponent(cur.root.path) +
      "&path=" + encodeURIComponent(cur.rel));
    const exists = (r.entries || []).some(e => e.name === name.trim() || e.name === name.trim() + "/");
    if (exists) {
      if (!window.confirm("文件 \"" + name.trim() + "\" 已存在，是否覆盖？")) return;
    }
  } catch (_) { /* 检查失败则直接尝试创建 */ }
  try {
    await postJSON("/api/workspace/write", { root: cur.root.path, path: rel, content: "" });
    toast("已创建 " + rel, "ok");
    // Bug C: 打开新文件后，current 恢复为目录，避免下次新建锚定到文件路径
    await wsOpenFile(cur.root, rel);
    _wsState.current = { root: cur.root, rel: cur.rel, is_dir: true };
  } catch (e) { toast("创建失败：" + e.message, "err"); }
}

async function wsRename(root, rel) {
  const base = rel.includes("/") ? rel.slice(0, rel.lastIndexOf("/")) : "";
  const old = rel.includes("/") ? rel.slice(rel.lastIndexOf("/") + 1) : rel;
  const name = window.prompt("重命名为：", old);
  if (!name || name.trim() === old) return;
  const dst = (base ? base + "/" : "") + name.trim();
  try {
    await postJSON("/api/workspace/rename", { root: root.path, src: rel, dst });
    toast("已重命名", "ok");
    // Bug B: 重命名后重新打开父目录而非旧路径，避免 404
    _wsState.current = { root, rel: base, is_dir: true };
    await wsOpenDir(root, base);
  } catch (e) { toast("重命名失败：" + e.message, "err"); }
}

async function wsDelete(root, rel, isDir) {
  if (!window.confirm("确定删除 " + rel + " ？" + (isDir ? "（含其下所有内容，不可恢复）" : ""))) return;
  try {
    await postJSON("/api/workspace/delete", { root: root.path, path: rel });
    toast("已删除 " + rel, "ok");
    // Bug B: 删除后重新打开父目录而非已删除路径，避免 404
    const base = rel.includes("/") ? rel.slice(0, rel.lastIndexOf("/")) : "";
    _wsState.current = { root, rel: base, is_dir: true };
    await wsOpenDir(root, base);
  } catch (e) { toast("删除失败：" + e.message, "err"); }
}

async function wsAttach(root, rel) {
  try {
    const r = await postJSON("/api/workspace/attach", { root: root.path, path: rel });
    if (!r.ok || !r.attachment) { toast("附加失败", "err"); return; }
    State.attachments = (State.attachments || []).concat([r.attachment]);
    Chat.renderAttachments();
    toast("已附加到聊天：" + r.attachment.name, "ok");
    Views.showView("chat");
  } catch (e) { toast("附加失败：" + e.message, "err"); }
}

// G6：把工作区某文件夹绑定为当前会话的固定上下文（每轮自动注入其内容）
export async function wsBindContext(target) {
  const cur = target || _wsState.current;
  if (!cur || !cur.is_dir) { toast("请先在工作区打开一个文件夹（目录），再绑定为上下文", "warn"); return; }
  if (!window.confirm("把此文件夹绑定为当前会话的固定上下文？\n之后每一轮对话都会自动带上该文件夹内的文本文件内容（受安全与大小限制）。")) return;
  let cid = State.conv_id;
  if (!cid) {
    try {
      const r = await postJSON("/api/conversations", { title: "" });
      cid = r.item.id; State.conv_id = cid;
    } catch (e) { toast("创建会话失败：" + e.message, "err"); return; }
  }
  try {
    const r = await postJSON("/api/context-folder", { conv_id: cid, root: cur.root.path, rel: cur.rel });
    if (!r.ok) { toast("绑定失败：" + (r.error || ""), "err"); return; }
    State.context_folder = r.context_folder || null;
    Chat.renderContextFolder(State.context_folder);
    const disp = (r.context_folder && (r.context_folder.display || r.context_folder.rel)) || cur.rel;
    toast("已绑定为会话上下文：" + disp, "ok");
    Views.showView("chat");
  } catch (e) { toast("绑定失败：" + e.message, "err"); }
}

function wsDownload(root, rel) {
  const a = el("a", { href: "/api/workspace/download?root=" + encodeURIComponent(root.path) +
    "&path=" + encodeURIComponent(rel), download: rel.split("/").pop() || "file" });
  document.body.appendChild(a); a.click(); a.remove();
}

async function wsAddRootDialog() {
  const p = window.prompt("输入要授权的本机目录绝对路径（例如 D:\\我的项目）：", "");
  if (!p) return;
  const label = window.prompt("给这个目录起个名字（可选，留空用文件夹名）：", "");
  try {
    const r = await postJSON("/api/workspace/roots", { path: p, label });
    toast("已添加授权目录", "ok");
    _wsState.roots = r.roots || _wsState.roots;
    await wsLoadRoots();
  } catch (e) { toast("添加失败：" + e.message, "err"); }
}

async function wsRemoveRoot(root) {
  if (!window.confirm("取消授权 " + root.label + " ？\n（默认目录不可移除）")) return;
  try {
    const r = await delJSON("/api/workspace/roots", { path: root.path });
    toast("已移除", "ok");
    _wsState.roots = r.roots || _wsState.roots;
    await wsLoadRoots();
  } catch (e) { toast("移除失败：" + e.message, "err"); }
}

let _wsRefreshLock = false;
async function wsRefresh() {
  if (_wsRefreshLock) return;
  _wsRefreshLock = true;
  try {
    const cur = _wsState.current;
    if (!cur) return;
    if (cur.is_dir) await wsOpenDir(cur.root, cur.rel);
    else await wsOpenFile(cur.root, cur.rel);
    const keys = Object.keys(_wsState.nodes);
    for (const k of keys) {
      const n = _wsState.nodes[k];
      n.loaded = false;
      if (n.expanded) {
        n.childrenBox.innerHTML = "<div class='muted'>读取中…</div>";
        await wsLoadChildren(n);
      }
    }
  } finally {
    _wsRefreshLock = false;
  }
}

function wsShowMoreMenu(btn, root, rel, isDir) {
  // 移除已有菜单
  document.querySelectorAll(".ws-more-menu").forEach(m => m.remove());
  const menu = el("div", { class: "ws-more-menu", style: "position:fixed;background:#fff;border:1px solid #ddd;border-radius:6px;box-shadow:0 4px 12px rgba(0,0,0,0.15);padding:4px 0;z-index:9999;min-width:120px;" });
  menu.appendChild(el("div", { class: "ws-more-item", style: "padding:6px 16px;cursor:pointer;font-size:13px;",
    text: "✏ 重命名", onclick: (ev) => { ev.stopPropagation(); menu.remove(); wsRename(root, rel); } }));
  menu.appendChild(el("div", { class: "ws-more-item", style: "padding:6px 16px;cursor:pointer;font-size:13px;color:#e74c3c;",
    text: "🗑 删除", onclick: (ev) => { ev.stopPropagation(); menu.remove(); wsDelete(root, rel, isDir); } }));
  document.body.appendChild(menu);
  const rect = btn.getBoundingClientRect();
  menu.style.left = Math.min(rect.left, window.innerWidth - menu.offsetWidth - 8) + "px";
  menu.style.top = (rect.bottom + 4) + "px";
  // 点击外部关闭
  setTimeout(() => {
    const closer = (ev2) => { if (!menu.contains(ev2.target)) { menu.remove(); document.removeEventListener("click", closer); } };
    document.addEventListener("click", closer);
  }, 0);
}


// 右键上下文菜单
function wsShowContextMenu(ev, root, rel, isDir) {
  document.querySelectorAll(".ws-more-menu").forEach(function(m) { m.remove(); });
  var menu = el("div", { class: "ws-more-menu", style: "position:fixed;background:#fff;border:1px solid #ddd;border-radius:6px;box-shadow:0 4px 16px rgba(0,0,0,0.18);padding:4px 0;z-index:9999;min-width:140px;font-size:13px;" });
  var items = [];
  if (!isDir) {
    items.push({ text: "📎 附加到聊天", action: function() { wsAttach(root, rel); } });
    items.push({ text: "⬇ 下载", action: function() { wsDownload(root, rel); } });
  } else {
    items.push({ text: "📌 设为上下文", action: function() { wsBindContext({ root: root, rel: rel }); } });
  }
  items.push({ text: "✏ 重命名", action: function() { wsRename(root, rel); } });
  items.push({ text: "🗑 删除", action: function() { wsDelete(root, rel, isDir); }, danger: true });
  for (var i = 0; i < items.length; i++) {
    var it = items[i];
    if (i > 0 && i === items.length - 1) {
      menu.appendChild(el("div", { style: "height:1px;background:#eee;margin:4px 0;" }));
    }
    menu.appendChild(el("div", { class: "ws-more-item", style: "padding:7px 16px;cursor:pointer;font-size:13px;" + (it.danger ? ";color:#e74c3c" : ""),
      text: it.text, onclick: function(ev2) { ev2.stopPropagation(); menu.remove(); it.action(); } }));
  }
  document.body.appendChild(menu);
  // 向右偏移40px，避免遮挡文件名
  var left = ev.clientX + 40, top = ev.clientY;
  requestAnimationFrame(function() {
    var mr = menu.getBoundingClientRect();
    if (left + mr.width > window.innerWidth) left = window.innerWidth - mr.width - 8;
    if (top + mr.height > window.innerHeight) top = window.innerHeight - mr.height - 8;
    menu.style.left = left + "px"; menu.style.top = top + "px";
  });
  var closer = function(ev2) { if (!menu.contains(ev2.target)) { menu.remove(); document.removeEventListener("click", closer); } };
  setTimeout(function() { document.addEventListener("click", closer); }, 0);
}
// 批量操作
function wsUpdateBatchBar() {
  var grid = document.querySelector(".ws-grid");
  if (!grid) return;
  var cbs = grid.querySelectorAll(".ws-file-cb");
  var checked = Array.from(cbs).filter(function(cb) { return cb.checked; });
  var bar = grid._batchBar; if (!bar) return;
  if (checked.length > 0) { bar.style.display = "flex"; grid._batchSel.textContent = "已选 " + checked.length + " 项"; }
  else { bar.style.display = "none"; }
}
function wsBatchToggleAll(grid, checked) {
  grid.querySelectorAll(".ws-file-cb").forEach(function(cb) {
    var row = cb.closest(".ws-file-row");
    if (row && row.style.display !== "none") cb.checked = checked;
  });
  wsUpdateBatchBar();
}
async function wsBatchAttach(grid, root) {
  var cbs = grid.querySelectorAll(".ws-file-cb:checked");
  if (!cbs.length) { toast("请先勾选要附加的文件", "warn"); return; }
  var rels = [];
  var entries = grid._entries || [];
  cbs.forEach(function(cb) {
    var row = cb.closest(".ws-file-row");
    var nameEl = row ? row.querySelector(".ws-file-name") : null;
    if (!nameEl) return;
    var name = (nameEl.textContent || "").trim();
    for (var ei = 0; ei < entries.length; ei++) {
      var e = entries[ei];
      if (e.is_dir) continue;
      if (name.indexOf(e.name.replace(/\/$/, "")) >= 0) { rels.push(e.rel); break; }
    }
  });
  if (!rels.length) { toast("没有可附加的文件", "warn"); return; }
  for (var ri = 0; ri < rels.length; ri++) {
    try {
      var r = await postJSON("/api/workspace/attach", { root: root.path, path: rels[ri] });
      if (r.ok && r.attachment) State.attachments = (State.attachments || []).concat([r.attachment]);
    } catch (e) { toast("附加失败：" + rels[ri], "err"); }
  }
  Chat.renderAttachments();
  toast("已附加 " + rels.length + " 个文件到聊天", "ok");
  Views.showView("chat");
}
async function wsBatchDelete(grid, root) {
  var cbs = grid.querySelectorAll(".ws-file-cb:checked");
  if (!cbs.length) { toast("请先勾选要删除的文件/目录", "warn"); return; }
  var names = [];
  var entries = grid._entries || [];
  cbs.forEach(function(cb) {
    var row = cb.closest(".ws-file-row");
    var nameEl = row ? row.querySelector(".ws-file-name") : null;
    if (!nameEl) return;
    var name = (nameEl.textContent || "").trim().replace(/^[^\s]+\s*/, "");
    names.push(name);
  });
  if (!window.confirm("确定删除以下 " + names.length + " 项？\n" + names.join("\n"))) return;
  cbs.forEach(function(cb) {
    var row = cb.closest(".ws-file-row");
    var nameEl = row ? row.querySelector(".ws-file-name") : null;
    if (!nameEl) return;
    var name = (nameEl.textContent || "").trim().replace(/^[^\s]+\s*/, "");
    for (var ei = 0; ei < entries.length; ei++) {
      var e = entries[ei];
      if (name.indexOf(e.name.replace(/\/$/, "")) >= 0) {
        (async function(rel) {
          try { await postJSON("/api/workspace/delete", { root: root.path, path: rel }); }
          catch (ex) { toast("删除失败：" + rel, "err"); }
        })(e.rel);
        break;
      }
    }
  });
  toast("已删除 " + cbs.length + " 项", "ok");
  var cur = _wsState.current;
  if (cur) await wsOpenDir(cur.root, cur.rel);
}
// 文件排序
function wsSortGrid(grid, by) {
  // 改为后端排序：重新加载当前目录（避免 DOM 重排，排序准确）
  const cur = _wsState.current;
  if (!cur) return;
  wsOpenDir(cur.root, cur.rel);
}

function wsFmtSize(sz) {
  if (sz == null) return "";
  if (sz < 1024) return sz + " B";
  if (sz < 1024 * 1024) return (sz / 1024).toFixed(1) + " KB";
  return (sz / 1024 / 1024).toFixed(1) + " MB";
}
function wsFmtTime(ts) {
  try { return new Date(ts * 1000).toLocaleString(); } catch (_) { return ""; }
}
// 文件类型图标：根据扩展名显示不同图标
const _FILE_ICONS = {
  ".py": "🐍", ".js": "🟨", ".ts": "🔷", ".jsx": "⚛️", ".tsx": "⚛️",
  ".html": "🌐", ".css": "🎨", ".scss": "🎨", ".less": "🎨",
  ".json": "📋", ".xml": "📋", ".yaml": "📋", ".yml": "📋", ".toml": "📋",
  ".md": "📝", ".txt": "📄", ".csv": "📊", ".log": "📋",
  ".jpg": "🖼️", ".jpeg": "🖼️", ".png": "🖼️", ".gif": "🖼️", ".svg": "🖼️",
  ".pdf": "📕", ".doc": "📘", ".docx": "📘", ".xls": "📗", ".xlsx": "📗",
  ".zip": "📦", ".tar": "📦", ".gz": "📦", ".7z": "📦", ".rar": "📦",
  ".sh": "💻", ".bat": "💻", ".ps1": "💻",
  ".env": "🔒", ".gitignore": "🙈", ".yml": "⚙️", ".yaml": "⚙️",
  ".sql": "🗄️", ".db": "🗄️", ".sqlite": "🗄️",
  ".exe": "⚡", ".dll": "⚡",
}
function wsFileIcon(name) {
  if (!name) return "📄";
  const ext = name.includes(".") ? "." + name.split(".").pop().toLowerCase() : "";
  return _FILE_ICONS[ext] || _FILE_ICONS[name.toLowerCase()] || "📄";
}
// 简单语法高亮（关键词着色 + 注释/字符串）
function wsHighlight(text) {
  if (!text) return "";
  var s = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  var lines = s.split("\n");
  return lines.map(function(line) {
    if (/^\s*(#|\/\/)/.test(line)) return '<span style="color:#999">' + line + '</span>';
    var h = line;
    h = h.replace(/(["'\`])(?:(?!\1|\\).)*\1/g, '<span style="color:#0a8">$&</span>');
    h = h.replace(/\b(\d+\.?\d*)\b/g, '<span style="color:#905">$1</span>');
    var kws = ["def ","class ","return ","import ","from ","if ","else ","elif ","for ","while ","try ","except ","finally ","with ","as ","pass ","break ","continue ","and ","or ","not ","in ","is ","None ","True ","False ","async ","await ","yield ","lambda ","raise ","global ","nonlocal ","del ","print(","const ","let ","var ","function ","export ","default ","typeof ","new ","this ","throw ","catch ","switch ","case "];
    for (var ki = 0; ki < kws.length; ki++) {
      var k = kws[ki];
      var esc = k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      try { var re = new RegExp("(?<=^|\\s)" + esc + "(?=\\s|$|\\()", "g"); h = h.replace(re, '<span style="color:#a67f59;font-weight:500">$&</span>'); } catch(_) {}
    }
    h = h.replace(/(^|\s)(@\w+)/g, '$1<span style="color:#e8a317">$2</span>');
    h = h.replace(/(\s+)(#.*)$/g, '$1<span style="color:#999">$2</span>');
    return h;
  }).join("\n");
}

// ==================================================================
// 新功能面板（hermes_features 13 模块）
// ==================================================================
