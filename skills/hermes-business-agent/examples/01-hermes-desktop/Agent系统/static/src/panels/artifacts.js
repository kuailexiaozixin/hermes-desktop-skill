// @ts-check
/* =====================================================================
 * artifacts.js — artifacts 面板子模块
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { State } from "../state.js";
import { getJSON, postJSON, delJSON, parseSSE } from "../api.js";
import * as Chat from "../chat.js";
// ------------------------------------------------------------------ 产物抽屉
export async function openArtifacts() {
  $("#artifactDrawer").classList.remove("hidden");
  const body = $("#artifactBody"); body.innerHTML = "";
  let data;
  try { data = await getJSON("/api/artifacts"); }
  catch (e) { body.appendChild(el("div", { class: "muted", text: "加载失败：" + e.message })); return; }
  if (!data.items || !data.items.length) {
    body.appendChild(el("div", { class: "muted", text: "暂无产物（output/ 为空）" }));
    return;
  }
  for (const a of data.items) {
    const attachBtn = el("button", { class: "btn ghost sm ai-attach", text: "📎 附加到聊天",
      onclick: (e) => { e.stopPropagation(); attachArtifactToChat(a); } });
    const dlBtn = el("button", { class: "btn ghost sm", text: "⭳ 下载",
      onclick: (e) => { e.stopPropagation(); downloadArtifact(a); } });
    body.appendChild(el("div", { class: "art-item", onclick: () => previewArtifact(a) }, [
      el("div", { class: "ai-main", style: "flex:1 1 auto;min-width:0;" }, [
        el("div", { class: "ai-name", text: a.path }),
        el("div", { class: "ai-meta", text: `${(a.size / 1024).toFixed(1)} KB · ${new Date(a.mtime * 1000).toLocaleString()}` }),
      ]),
      el("div", { class: "ai-view", text: a.viewable ? "查看" : "不可预览" }),
      attachBtn, dlBtn,
    ]));
  }
}
export async function previewArtifact(a) {
  const body = $("#artifactBody");
  if (!a.viewable) { toast("该文件类型不可预览", "err"); return; }
  const prev = el("div", { class: "art-preview", text: "加载中…" });
  body.prepend(prev);
  try {
    const res = await fetch("/artifact/" + a.path);
    if (a.ext === ".png" || a.ext === ".jpg" || a.ext === ".jpeg" || a.ext === ".gif" || a.ext === ".webp") {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      prev.innerHTML = "";
      prev.appendChild(el("img", { src: url, alt: a.path }));
    } else {
      prev.textContent = await res.text();
    }
  } catch (e) { prev.textContent = "预览失败：" + e.message; }
}

// 把产物抽屉里的文件按路径登记为对话附件（免去重新上传，复用 /api/chat 注入逻辑）
async function attachArtifactToChat(a) {
  try {
    const r = await postJSON("/api/attachments/from-path", { path: a.path });
    if (!r.ok || !r.attachment) { toast("附加失败", "err"); return; }
    State.attachments = State.attachments.concat([r.attachment]);
    Chat.renderAttachments();
    toast(`已附加 ${r.attachment.name}`, "ok");
  } catch (e) { toast("附加失败：" + e.message, "err"); }
}

async function downloadArtifact(a) {
  try {
    const r = await fetch("/artifact/" + encodeURIComponent(a.path));
    if (!r.ok) { toast("下载失败", "err"); return; }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const fileName = a.path.split("/").pop() || a.path.split("\\").pop() || "artifact";
    const dl = el("a", { href: url, download: fileName });
    document.body.appendChild(dl); dl.click(); dl.remove(); URL.revokeObjectURL(url);
    toast("已下载 " + fileName, "ok");
  } catch (e) { toast("下载失败：" + e.message, "err"); }
}

