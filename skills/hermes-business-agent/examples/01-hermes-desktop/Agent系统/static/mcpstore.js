/* MCP 商店 widget（对标 skillstore.js）
 * 自包含 vanilla JS，无 CDN 依赖。支持多实例：window.initMcpStore(rootId)
 * 双标签：MCP 商店（精选目录 + LobeHub 增补）/ 我的 MCP（config.yaml.mcp_servers 管理）。
 * 启用开关复用全局 .skill-toggle（components.py 定义，与技能/Loop 浮窗一致）。
 */
(function () {
  "use strict";

  var CSS = [
    // 对标 业务示例 设置界面视觉：主色蓝 #2563eb
    ".mcp-store{--primary:#2563eb;--primary-hover:#1d4ed8;--primary-soft:rgba(37,99,235,.12);}",
    ".mcp-store{font-size:13px;}",
    ".mcp-store .ms-toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:16px;}",
    ".mcp-store .ms-tabs{display:inline-flex;background:var(--bg-muted,#f1f5f9);border-radius:10px;padding:4px;}",
    ".mcp-store .ms-tab{border:none;background:transparent;padding:7px 15px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;color:var(--text-secondary,#64748b);transition:color .15s;}",
    ".mcp-store .ms-tab.active{background:var(--bg-card,#fff);color:var(--primary,#2563eb);box-shadow:0 1px 3px rgba(0,0,0,.08);}",
    ".mcp-store .ms-search{flex:1;min-width:160px;max-width:320px;padding:8px 12px;border:1px solid var(--border,#e2e8f0);border-radius:10px;font-size:13px;outline:none;background:var(--bg-card,#fff);color:inherit;}",
    ".mcp-store .ms-search:focus{border-color:var(--primary,#2563eb);}",
    ".mcp-store .ms-select{padding:8px 10px;border:1px solid var(--border,#e2e8f0);border-radius:10px;font-size:13px;background:var(--bg-card,#fff);color:inherit;}",
    ".mcp-store .ms-chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;}",
    ".mcp-store .ms-chip{white-space:nowrap;border:1px solid var(--border,#e2e8f0);background:var(--bg-card,#fff);border-radius:999px;padding:6px 15px;font-size:12.5px;cursor:pointer;color:var(--text-secondary,#64748b);}",
    ".mcp-store .ms-chip.active{background:var(--primary,#2563eb);border-color:var(--primary,#2563eb);color:#fff;}",
    ".mcp-store .ms-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:20px;}",
    ".mcp-store .ms-card{border:1px solid var(--border-strong,#cbd5e1);border-radius:14px;padding:16px;background:var(--bg-card,#fff);display:flex;flex-direction:column;gap:10px;min-height:136px;box-shadow:0 1px 3px rgba(15,23,42,.07);transition:box-shadow .18s,transform .18s;cursor:pointer;}",
    ".mcp-store .ms-card:hover{box-shadow:0 8px 24px rgba(15,23,42,.10);transform:translateY(-2px);}",
    ".mcp-store .ms-card-head{display:flex;align-items:flex-start;gap:8px;}",
    ".mcp-store .ms-name{font-weight:700;font-size:14px;color:var(--text-primary,#0f172a);word-break:break-all;}",
    ".mcp-store .ms-owner{font-size:11px;color:var(--text-tertiary,#94a3b8);}",
    ".mcp-store .ms-desc{font-size:12.5px;color:var(--text-secondary,#64748b);line-height:1.6;flex:1;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}",
    ".mcp-store .ms-meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;}",
    ".mcp-store .ms-badge{font-size:10.5px;padding:2px 8px;border-radius:999px;background:var(--bg-muted,#f1f5f9);color:var(--text-secondary,#64748b);}",
    ".mcp-store .ms-badge.key{background:#fef3c7;color:#92400e;}",
    ".mcp-store .ms-badge.builtin{background:var(--primary-soft);color:var(--primary,#2563eb);}",
    ".mcp-store .ms-badge.off{background:#fee2e2;color:#dc2626;}",
    ".mcp-store .ms-foot{display:flex;justify-content:space-between;align-items:center;margin-top:auto;padding-top:10px;border-top:1px solid var(--border,#e2e8f0);}",
    ".mcp-store .ms-count{font-size:11px;color:var(--text-tertiary,#94a3b8);}",
    ".mcp-store .ms-btn{border:none;border-radius:8px;padding:6px 14px;font-size:12px;cursor:pointer;background:var(--primary,#2563eb);color:#fff;transition:filter .15s;}",
    ".mcp-store .ms-btn:disabled{opacity:.55;cursor:default;}",
    ".mcp-store .ms-btn.ghost{background:transparent;border:1px solid var(--border,#e2e8f0);color:var(--text-secondary,#64748b);}",
    ".mcp-store .ms-btn.danger{background:transparent;border:1px solid #fca5a5;color:#dc2626;}",
    ".mcp-store .ms-cmd{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;color:var(--text-tertiary,#94a3b8);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}",
    ".mcp-store .ms-empty{padding:36px 0;text-align:center;color:var(--text-tertiary,#94a3b8);font-size:13px;grid-column:1/-1;}",
    ".mcp-store .ms-more{display:block;margin:16px auto 0;}",
    ".mcp-store .ms-detail-head h4{margin:0 0 12px;font-size:15px;color:var(--text-primary,#0f172a);}",
    ".mcp-store .ms-detail-row{display:flex;gap:12px;align-items:baseline;padding:7px 0;border-bottom:1px dashed var(--border,#e2e8f0);font-size:13px;}",
    ".mcp-store .ms-detail-label{flex:0 0 84px;color:var(--text-tertiary,#94a3b8);font-size:12px;}",
    ".mcp-store .ms-detail-val{color:var(--text-primary,#0f172a);word-break:break-all;}",
    ".mcp-store .ms-detail-val a{color:var(--primary,#2563eb);text-decoration:none;}",
    ".mcp-store .ms-detail-val a:hover{text-decoration:underline;}",
    ".mcp-store .ms-detail-desc{margin-top:12px;font-size:13px;line-height:1.7;color:var(--text-primary,#0f172a);white-space:pre-wrap;word-break:break-word;}",
    ".mcp-store .ms-detail-body{margin-top:12px;border-top:1px solid var(--border,#e2e8f0);padding-top:10px;}",
    ".mcp-store .ms-detail-loading{font-size:12.5px;color:var(--text-tertiary,#94a3b8);}",
    ".mcp-store .ms-detail-pre{margin:0;background:var(--bg-muted,#f1f5f9);border:1px solid var(--border,#e2e8f0);border-radius:8px;padding:12px;max-height:40vh;overflow:auto;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;line-height:1.6;white-space:pre-wrap;word-break:break-word;color:var(--text-primary,#0f172a);}",
    ".ms-toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1e293b;color:#fff;padding:10px 18px;border-radius:10px;font-size:13px;z-index:4000;opacity:0;transition:opacity .25s;pointer-events:none;}",
    ".ms-toast.show{opacity:1;}",
    ".ms-modal-mask{position:fixed;inset:0;background:rgba(15,23,42,.45);z-index:3800;display:flex;align-items:center;justify-content:center;}",
    ".ms-modal{background:var(--bg-card,#fff);border-radius:14px;padding:20px;width:min(480px,92vw);max-height:84vh;overflow:auto;box-shadow:0 20px 50px rgba(0,0,0,.25);}",
    ".ms-modal h4{margin:0 0 12px;font-size:15px;color:var(--text-primary,#0f172a);}",
    ".ms-modal label{display:block;font-size:12px;color:var(--text-secondary,#64748b);margin:10px 0 4px;}",
    ".ms-modal input,.ms-modal textarea{width:100%;box-sizing:border-box;padding:7px 10px;border:1px solid var(--border,#e2e8f0);border-radius:8px;font-size:12.5px;font-family:ui-monospace,Menlo,Consolas,monospace;background:var(--bg-card,#fff);color:inherit;}",
    ".ms-modal .ms-modal-foot{display:flex;justify-content:flex-end;gap:10px;margin-top:16px;}",
    ".ms-modal .ms-hint{font-size:11px;color:var(--text-tertiary,#94a3b8);margin-top:4px;}"
  ].join("\n");

  function ensureStyle() {
    if (document.getElementById("mcpstore-style")) return;
    var st = document.createElement("style");
    st.id = "mcpstore-style";
    st.textContent = CSS;
    document.head.appendChild(st);
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function toast(msg) {
    var t = document.querySelector(".ms-toast");
    if (!t) {
      t = document.createElement("div");
      t.className = "ms-toast";
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(t._h);
    t._h = setTimeout(function () { t.classList.remove("show"); }, 2600);
  }

  function closeModal() {
    var m = document.querySelector(".ms-modal-mask");
    if (m) m.remove();
  }

  function openModal(html) {
    closeModal();
    var mask = document.createElement("div");
    mask.className = "ms-modal-mask";
    mask.innerHTML = '<div class="ms-modal">' + html + "</div>";
    mask.addEventListener("click", function (e) { if (e.target === mask) closeModal(); });
    document.body.appendChild(mask);
    return mask;
  }

  function createStore(rootId) {
    var root = document.getElementById(rootId);
    if (!root || root._msInit) return;
    root._msInit = true;

    var state = {
      tab: rootId.indexOf("Settings") >= 0 ? "mine" : "market",
      q: "", category: "", sort: "installCount",
      page: 1, pageSize: 24, pages: 0, loading: false,
      catLabels: {}, categories: [], installed: {}, installedLoaded: false
    };

    root.innerHTML =
      '<div class="ms-toolbar">' +
      '  <div class="ms-tabs">' +
      '    <button class="ms-tab" data-tab="market">MCP 商店</button>' +
      '    <button class="ms-tab" data-tab="mine">我的 MCP</button>' +
      "  </div>" +
      '  <input class="ms-search" placeholder="搜索 MCP 服务器…" />' +
      '  <select class="ms-select" data-sort><option value="installCount">按热门</option><option value="name">按名称</option></select>' +
      '  <button class="ms-btn ghost" data-manual>手动添加</button>' +
      "</div>" +
      '<div class="ms-chips"></div>' +
      '<div class="ms-grid"></div>' +
      '<button class="ms-btn ghost ms-more" style="display:none;">加载更多</button>';

    var elTabs = root.querySelectorAll(".ms-tab");
    var elSearch = root.querySelector(".ms-search");
    var elSort = root.querySelector("[data-sort]");
    var elChips = root.querySelector(".ms-chips");
    var elGrid = root.querySelector(".ms-grid");
    var elMore = root.querySelector(".ms-more");

    function catLabel(c) { return state.catLabels[c] || c; }

    function marketCard(it) {
      var installedName = state.installed[it.slug] ? it.slug : null;
      var badges = "";
      if (it.category) badges += '<span class="ms-badge">' + esc(catLabel(it.category)) + "</span>";
      if (it.runtime) badges += '<span class="ms-badge">' + esc(it.runtime) + "</span>";
      if (it.envRequired && it.envRequired.length) badges += '<span class="ms-badge key">需 Key</span>';
      var btn;
      if (installedName) {
        btn = '<button class="ms-btn ghost" disabled>已安装</button>';
      } else if (it.hasDef) {
        btn = '<button class="ms-btn" data-install="' + esc(it.slug) + '">安装</button>';
      } else {
        btn = '<button class="ms-btn" data-lobehub="' + esc(it.slug) + '">安装</button>';
      }
      var _dd = {
        name: it.name || "", owner: it.owner || "",
        description: it.description || "", category: it.category || "",
        runtime: it.runtime || "", installCount: it.installCount || 0,
        homepage: it.homepage || "", slug: it.slug || "", source: it.source || "",
        envRequired: (it.envRequired && it.envRequired.length) ? it.envRequired.join(", ") : "",
        command: (it.command ? it.command + " " + (it.args || []).join(" ") : "") || ""
      };
      return (
        '<div class="ms-card" data-detail="' + esc(JSON.stringify(_dd)) + '">' +
        '  <div class="ms-card-head"><div><div class="ms-name">' + esc(it.name) + "</div>" +
        (it.owner ? '<div class="ms-owner">' + esc(it.owner) + "</div>" : "") + "</div></div>" +
        '  <div class="ms-desc">' + esc(it.description || "（暂无描述）") + "</div>" +
        '  <div class="ms-meta">' + badges + "</div>" +
        '  <div class="ms-foot"><span class="ms-count">' +
        (it.installCount ? "热度 " + Number(it.installCount).toLocaleString() : esc(it.source === "lobehub" ? "LobeHub" : "精选")) +
        "</span>" + btn + "</div></div>"
      );
    }

    function mineCard(it) {
      var badges = "";
      if (it.builtin) badges += '<span class="ms-badge builtin">系统内置</span>';
      if (!it.enabled) badges += '<span class="ms-badge off">已停用</span>';
      var cmd = it.command ? esc(it.command + " " + (it.args || []).join(" ")) : (it.url ? esc(it.url) : "（未配置启动命令）");
      var envKeys = Object.keys(it.env || {});
      if (envKeys.length) badges += '<span class="ms-badge key">env×' + envKeys.length + "</span>";
      var _md = {
        name: it.name || "", description: it.description || "",
        category: it.category || "", source: "本机已配置",
        command: it.command ? (it.command + " " + (it.args || []).join(" ")) : (it.url || ""),
        builtin: it.builtin ? "系统内置" : "", enabled: it.enabled === false ? "已停用" : "已启用"
      };
      return (
        '<div class="ms-card" data-detail="' + esc(JSON.stringify(_md)) + '">' +
        '  <div class="ms-card-head" style="justify-content:space-between;width:100%;">' +
        '    <div class="ms-name">' + esc(it.name) + "</div>" +
        '    <label class="skill-toggle"><input type="checkbox" data-enable="' + esc(it.name) + '" ' +
        (it.enabled ? "checked" : "") + (it.builtin ? " disabled" : "") + '/><span class="skill-toggle-slider"></span></label>' +
        "  </div>" +
        '  <div class="ms-cmd" title="' + cmd + '">' + cmd + "</div>" +
        '  <div class="ms-meta">' + badges + "</div>" +
        '  <div class="ms-foot"><span></span><span style="display:flex;gap:8px;">' +
        '    <button class="ms-btn ghost" data-edit="' + esc(it.name) + '">编辑</button>' +
        (it.builtin ? "" : '<button class="ms-btn danger" data-remove="' + esc(it.name) + '">移除</button>') +
        "  </span></div></div>"
      );
    }

    function refreshInstalledIndex(cb) {
      fetch("/api/mcp-store/installed").then(function (r) { return r.json(); }).then(function (d) {
        state.installed = {};
        (d.items || []).forEach(function (it) { state.installed[it.name] = it; });
        if (cb) cb(d.items || []);
      }).catch(function () { if (cb) cb([]); });
    }

    function renderChips() {
      if (state.tab !== "market") { elChips.innerHTML = ""; return; }
      var html = '<button class="ms-chip' + (state.category ? "" : " active") + '" data-cat="">全部</button>';
      state.categories.forEach(function (c) {
        html += '<button class="ms-chip' + (state.category === c ? " active" : "") + '" data-cat="' + esc(c) + '">' + esc(catLabel(c)) + "</button>";
      });
      elChips.innerHTML = html;
    }

    function ensureInstalled(cb) {
      // 「已安装」索引只在首次/切换后/安装移除后刷新，加载更多时复用缓存，避免每页多一次往返。
      if (state.installedLoaded) { cb(); return; }
      refreshInstalledIndex(function (items) { state.installedLoaded = true; cb(items); });
    }

    function renderMarket(append) {
      state.loading = true;
      if (!append) elGrid.innerHTML = '<div class="ms-empty">加载中…</div>';
      var params = "q=" + encodeURIComponent(state.q) + "&category=" + encodeURIComponent(state.category) +
        "&page=" + state.page + "&pageSize=" + state.pageSize + "&sort=" + encodeURIComponent(state.sort);
      function doFetch() {
        fetch("/api/mcp-store/servers?" + params).then(function (r) { return r.json(); }).then(function (d) {
          state.loading = false;
          state.categories = d.categories || state.categories;
          state.catLabels = d.categoryLabels || state.catLabels;
          state.pages = d.pages || 0;
          renderChips();
          var html = (d.items || []).map(marketCard).join("");
          if (append) {
            if (html) elGrid.insertAdjacentHTML("beforeend", html);
          } else {
            elGrid.innerHTML = html || '<div class="ms-empty">未找到匹配的 MCP 服务器</div>';
          }
          elMore.style.display = (state.page < state.pages && (d.items || []).length) ? "block" : "none";
        }).catch(function () {
          state.loading = false;
          elGrid.innerHTML = '<div class="ms-empty">目录加载失败，请检查网络后重试</div>';
        });
      }
      if (append) {
        doFetch();   // 加载更多：复用已缓存的「已安装」索引，不再多一次往返
      } else {
        ensureInstalled(doFetch);
      }
    }

    function renderMine() {
      elGrid.innerHTML = '<div class="ms-empty">加载中…</div>';
      elMore.style.display = "none";
      renderChips();
      refreshInstalledIndex(function (items) {
        var q = state.q.toLowerCase();
        if (q) items = items.filter(function (it) { return it.name.toLowerCase().indexOf(q) >= 0; });
        elGrid.innerHTML = items.map(mineCard).join("") ||
          '<div class="ms-empty">尚未配置 MCP 服务器，切到「MCP 商店」安装</div>';
      });
    }

    function render() {
      elTabs.forEach(function (b) { b.classList.toggle("active", b.getAttribute("data-tab") === state.tab); });
      if (state.tab === "market") renderMarket(false); else renderMine();
    }

    // ── 安装（有定义）：需 Key 时先弹 env 收集 ──
    function doInstall(slug, env) {
      fetch("/api/mcp-store/install", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug: slug, env: env || {} })
      }).then(function (r) { return r.json(); }).then(function (d) {
        if (d.ok) { toast("已安装 " + slug); closeModal(); state.installedLoaded = false; render(); }
        else if (d.envRequired && d.envRequired.length) { openEnvModal(slug, d.envRequired); }
        else toast(d.error || "安装失败");
      }).catch(function () { toast("安装请求失败"); });
    }

    // ── LobeHub 条目安装：先按 slug 动态拉详情页取真实启动配置（一键安装全站 MCP）──
    function installFromLobehub(slug) {
      toast("正在从 LobeHub 获取安装配置…");
      fetch("/api/mcp-store/meta/" + encodeURIComponent(slug)).then(function (r) { return r.json(); }).then(function (d) {
        if (d && d.ok && d.command) {
          var envKeys = (d.envRequired && d.envRequired.length) ? d.envRequired : Object.keys(d.env || {});
          if (envKeys.length) { openEnvModal(slug, envKeys); }
          else { doInstall(slug, {}); }
        } else {
          openManualModal({
            name: slug,
            homepage: (d && d.homepage) || ("https://lobehub.com/zh/mcp/" + slug),
            owner: d && d.owner, category: d && d.category
          });
        }
      }).catch(function () {
        openManualModal({ name: slug, homepage: "https://lobehub.com/zh/mcp/" + slug });
      });
    }

    function openEnvModal(slug, keys) {
      var fields = keys.map(function (k) {
        return "<label>" + esc(k) + '</label><input data-env="' + esc(k) + '" placeholder="填入 ' + esc(k) + '" />';
      }).join("");
      var mask = openModal(
        "<h4>安装 " + esc(slug) + "</h4>" +
        '<div class="ms-hint">该 MCP 需要以下环境变量（API Key），仅保存在本机 config.yaml。</div>' +
        fields +
        '<div class="ms-modal-foot"><button class="ms-btn ghost" data-cancel>取消</button>' +
        '<button class="ms-btn" data-ok>确认安装</button></div>'
      );
      mask.querySelector("[data-cancel]").onclick = closeModal;
      mask.querySelector("[data-ok]").onclick = function () {
        var env = {};
        mask.querySelectorAll("[data-env]").forEach(function (i) { env[i.getAttribute("data-env")] = i.value.trim(); });
        var missing = keys.filter(function (k) { return !env[k]; });
        if (missing.length) { toast("请填写：" + missing.join(", ")); return; }
        doInstall(slug, env);
      };
    }

    // ── 手动添加 / 配置安装（LobeHub 无定义条目预填名称） ──
    function openManualModal(preset) {
      preset = preset || {};
      var mask = openModal(
        "<h4>" + (preset.name ? "配置安装 " + esc(preset.name) : "手动添加 MCP 服务器") + "</h4>" +
        "<label>服务器名</label><input data-f=\"name\" value=\"" + esc(preset.name || "") + "\" placeholder=\"例如 filesystem\" />" +
        "<label>启动命令（stdio 传输；远程服务器留空填下方 URL）</label><input data-f=\"command\" value=\"" + esc(preset.command || "") + "\" placeholder=\"npx / uvx / python\" />" +
        "<label>参数（每行一个）</label><textarea data-f=\"args\" rows=\"3\" placeholder=\"-y&#10;@modelcontextprotocol/server-filesystem&#10;D:/data\">" + esc((preset.args || []).join("\n")) + "</textarea>" +
        "<label>环境变量（每行 KEY=VALUE，可留空）</label><textarea data-f=\"env\" rows=\"2\"></textarea>" +
        "<label>URL（HTTP/SSE 远程传输；与启动命令二选一）</label><input data-f=\"url\" value=\"" + esc(preset.url || "") + "\" placeholder=\"https://example.com/mcp\" />" +
        "<label>请求头（可选，每行 KEY=VALUE）</label><textarea data-f=\"headers\" rows=\"2\"></textarea>" +
        (preset.owner ? '<div class="ms-hint">发布者：' + esc(preset.owner) + "</div>" : "") +
        (preset.category ? '<div class="ms-hint">分类：' + esc(preset.category) + "</div>" : "") +
        (preset.homepage ? '<div class="ms-hint">启动参数可参考主页：' + esc(preset.homepage) + "</div>" : "") +
        '<div class="ms-modal-foot"><button class="ms-btn ghost" data-cancel>取消</button>' +
        '<button class="ms-btn" data-ok>保存并安装</button></div>'
      );
      mask.querySelector("[data-cancel]").onclick = closeModal;
      mask.querySelector("[data-ok]").onclick = function () {
        var val = function (f) { return mask.querySelector('[data-f="' + f + '"]').value; };
        var name = val("name").trim(), command = val("command").trim(), url = val("url").trim();
        if (!name) { toast("服务器名必填"); return; }
        if (!command && !url) { toast("启动命令与 URL 至少填一项"); return; }
        var args = val("args").split("\n").map(function (s) { return s.trim(); }).filter(Boolean);
        var env = {}, envLines = val("env").split("\n");
        envLines.forEach(function (line) { var i = line.indexOf("="); if (i > 0) env[line.slice(0, i).trim()] = line.slice(i + 1).trim(); });
        var headers = {}, hLines = val("headers").split("\n");
        hLines.forEach(function (line) { var i = line.indexOf("="); if (i > 0) headers[line.slice(0, i).trim()] = line.slice(i + 1).trim(); });
        var payload = { name: name };
        if (command) { payload.command = command; payload.args = args; }
        if (url) payload.url = url;
        if (Object.keys(env).length) payload.env = env;
        if (Object.keys(headers).length) payload.headers = headers;
        fetch("/api/mcp-store/install", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        }).then(function (r) { return r.json(); }).then(function (d) {
          if (d.ok) { toast("已保存 " + name); closeModal(); state.tab = "mine"; render(); }
          else toast(d.error || "保存失败");
        }).catch(function () { toast("保存请求失败"); });
      };
    }

    // ── 我的 MCP：编辑 ──
    function openEditModal(name) {
      var it = state.installed[name];
      if (!it) return;
      var envLines = Object.keys(it.env || {}).map(function (k) { return k + "=" + it.env[k]; }).join("\n");
      var headersLines = Object.keys(it.headers || {}).map(function (k) { return k + "=" + it.headers[k]; }).join("\n");
      var mask = openModal(
        "<h4>编辑 " + esc(name) + "</h4>" +
        "<label>启动命令（stdio；远程服务器留空填下方 URL）</label><input data-f=\"command\" value=\"" + esc(it.command || "") + "\" />" +
        "<label>参数（每行一个）</label><textarea data-f=\"args\" rows=\"3\">" + esc((it.args || []).join("\n")) + "</textarea>" +
        "<label>环境变量（每行 KEY=VALUE）</label><textarea data-f=\"env\" rows=\"2\">" + esc(envLines) + "</textarea>" +
        "<label>URL（HTTP/SSE 远程传输）</label><input data-f=\"url\" value=\"" + esc(it.url || "") + "\" />" +
        "<label>请求头（可选，每行 KEY=VALUE）</label><textarea data-f=\"headers\" rows=\"2\">" + esc(headersLines) + "</textarea>" +
        '<div class="ms-modal-foot"><button class="ms-btn ghost" data-cancel>取消</button>' +
        '<button class="ms-btn" data-ok>保存</button></div>'
      );
      mask.querySelector("[data-cancel]").onclick = closeModal;
      mask.querySelector("[data-ok]").onclick = function () {
        var val = function (f) { return mask.querySelector('[data-f="' + f + '"]').value; };
        var command = val("command").trim(), url = val("url").trim();
        var args = val("args").split("\n").map(function (s) { return s.trim(); }).filter(Boolean);
        var env = {}, envLines2 = val("env").split("\n");
        envLines2.forEach(function (line) { var i = line.indexOf("="); if (i > 0) env[line.slice(0, i).trim()] = line.slice(i + 1).trim(); });
        var headers = {}, hLines = val("headers").split("\n");
        hLines.forEach(function (line) { var i = line.indexOf("="); if (i > 0) headers[line.slice(0, i).trim()] = line.slice(i + 1).trim(); });
        var payload = {};
        if (command) payload.command = command;
        if (url) payload.url = url;
        payload.args = args;
        payload.env = env;
        if (Object.keys(headers).length) payload.headers = headers;
        if (!command && !url) { toast("启动命令与 URL 至少保留一项"); return; }
        fetch("/api/mcp-store/installed/" + encodeURIComponent(name) + "/save", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        }).then(function (r) { return r.json(); }).then(function (d) {
          if (d.ok) { toast("已保存 " + name); closeModal(); render(); }
          else toast(d.error || "保存失败");
        }).catch(function () { toast("保存请求失败"); });
      };
    }

    // ── 详情弹窗 ──
    function showMcpDetail(d) {
      function row(label, val, link) {
        if (!val) return "";
        var v = link
          ? '<a href="' + esc(val) + '" target="_blank" rel="noopener">' + esc(val) + "</a>"
          : esc(String(val));
        return '<div class="ms-detail-row"><span class="ms-detail-label">' + esc(label) +
          '</span><span class="ms-detail-val">' + v + "</span></div>";
      }
      var fieldBody =
        row("作者", d.owner) + row("分类", d.category) + row("运行环境", d.runtime) +
        row("来源", d.source) + row("热度", d.installCount) + row("所需 Key", d.envRequired) +
        row("主页", d.homepage, true) + row("目录", d.dir) + row("状态", d.enabled) + row("类型", d.builtin);
      var mask = openModal(
        '<div class="ms-detail-head"><h4>' + esc(d.name || "未知") + "</h4></div>" +
        fieldBody +
        (d.description ? '<div class="ms-detail-desc">' + esc(d.description) + "</div>" : "") +
        '<div class="ms-detail-body" id="msDetailBody"><div class="ms-detail-loading">加载详情…</div></div>' +
        '<div class="ms-modal-foot"><button class="ms-btn ghost" data-close>关闭</button></div>'
      );
      mask.querySelector("[data-close]").onclick = closeModal;
      var bodyEl = mask.querySelector("#msDetailBody");
      var slug = d.slug;
      if (!slug) {
        // 我的 MCP：本地 data-detail 已含 command/url，直接展示
        bodyEl.innerHTML = d.command ? '<pre class="ms-detail-pre">' + esc(d.command) + "</pre>" : "";
        return;
      }
      // 市场 MCP：按 slug 拉取 meta 详细配置（command/args/env）
      fetch("/api/mcp-store/meta/" + encodeURIComponent(slug))
        .then(function (r) { return r.json(); })
        .then(function (md) {
          if (md && md.ok) {
            var lines = [];
            if (md.command) lines.push("启动命令: " + md.command);
            if (md.args && md.args.length) lines.push("参数: " + md.args.join(" "));
            if (md.env && Object.keys(md.env).length) {
              lines.push("环境变量:");
              Object.keys(md.env).forEach(function (k) {
                lines.push("  " + k + (md.env[k] ? "=" + md.env[k] : "（需填写）"));
              });
            }
            if (md.homepage) lines.push("主页: " + md.homepage);
            bodyEl.innerHTML = lines.length
              ? '<pre class="ms-detail-pre">' + esc(lines.join("\n")) + "</pre>"
              : '<div class="ms-detail-loading">未获取到详细配置</div>';
          } else {
            bodyEl.innerHTML = '<div class="ms-detail-loading">详情拉取失败：' + esc((md && md.error) || "未知") + "</div>";
          }
        })
        .catch(function () { bodyEl.innerHTML = '<div class="ms-detail-loading">详情加载失败</div>'; });
    }

    // ── 事件绑定 ──
    elTabs.forEach(function (b) {
      b.onclick = function () { state.tab = b.getAttribute("data-tab"); state.page = 1; render(); };
    });
    elSearch.oninput = function () {
      clearTimeout(elSearch._h);
      elSearch._h = setTimeout(function () { state.q = elSearch.value.trim(); state.page = 1; render(); }, 300);
    };
    elSort.onchange = function () { state.sort = elSort.value; state.page = 1; render(); };
    root.querySelector("[data-manual]").onclick = function () { openManualModal(); };
    elChips.addEventListener("click", function (e) {
      var c = e.target.closest("[data-cat]");
      if (!c) return;
      state.category = c.getAttribute("data-cat");
      state.page = 1;
      render();
    });
    elMore.onclick = function () {
      if (state.loading || state.page >= state.pages) return;
      state.page += 1;
      renderMarket(true);
    };
    elGrid.addEventListener("click", function (e) {
      var t;
      if ((t = e.target.closest("[data-install]"))) {
        var slug = t.getAttribute("data-install");
        // 先查目录条目是否需 Key
        fetch("/api/mcp-store/servers?q=" + encodeURIComponent(slug) + "&pageSize=50").then(function (r) { return r.json(); }).then(function (d) {
          var it = (d.items || []).filter(function (x) { return x.slug === slug; })[0];
          if (it && it.envRequired && it.envRequired.length) openEnvModal(slug, it.envRequired);
          else doInstall(slug, {});
        }).catch(function () { doInstall(slug, {}); });
      } else if ((t = e.target.closest("[data-lobehub]"))) {
        installFromLobehub(t.getAttribute("data-lobehub"));
      } else if ((t = e.target.closest("[data-config]"))) {
        var s2 = t.getAttribute("data-config");
        fetch("/api/mcp-store/servers?q=" + encodeURIComponent(s2) + "&pageSize=50").then(function (r) { return r.json(); }).then(function (d) {
          var it = (d.items || []).filter(function (x) { return x.slug === s2; })[0] || { slug: s2 };
          openManualModal({ name: it.slug, homepage: it.homepage });
        }).catch(function () { openManualModal({ name: s2 }); });
      } else if ((t = e.target.closest("[data-remove]"))) {
        var n = t.getAttribute("data-remove");
        if (!window.confirm("确定移除 MCP 服务器 " + n + " 吗？")) return;
        fetch("/api/mcp-store/installed/" + encodeURIComponent(n), { method: "DELETE" })
          .then(function (r) { return r.json(); }).then(function (d) {
            if (d.ok) { toast("已移除 " + n); state.installedLoaded = false; render(); } else toast(d.error || "移除失败");
          }).catch(function () { toast("移除请求失败"); });
      } else if ((t = e.target.closest("[data-edit]"))) {
        openEditModal(t.getAttribute("data-edit"));
      } else if ((t = e.target.closest(".ms-card")) && t.getAttribute("data-detail")) {
        try { showMcpDetail(JSON.parse(t.getAttribute("data-detail"))); } catch (_e) {}
      }
    });
    elGrid.addEventListener("change", function (e) {
      var t = e.target.closest("[data-enable]");
      if (!t) return;
      var n = t.getAttribute("data-enable");
      var enabled = t.checked;
      fetch("/api/mcp-store/installed/" + encodeURIComponent(n) + "/enable", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: enabled })
      }).then(function (r) { return r.json(); }).then(function (d) {
        if (d.ok) toast((enabled ? "已启用 " : "已停用 ") + n);
        else { t.checked = !enabled; toast(d.error || "操作失败"); }
      }).catch(function () { t.checked = !enabled; toast("请求失败"); });
    });

    render();
  }

  window.initMcpStore = function (rootId) {
    ensureStyle();
    createStore(rootId);
  };

  if (document.getElementById("mcpStoreRoot")) {
    window.initMcpStore("mcpStoreRoot");
  } else {
    document.addEventListener("DOMContentLoaded", function () {
      if (document.getElementById("mcpStoreRoot")) window.initMcpStore("mcpStoreRoot");
    });
  }
})();
