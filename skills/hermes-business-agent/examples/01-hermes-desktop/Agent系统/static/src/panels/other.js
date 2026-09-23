// @ts-check
/* =====================================================================
 * other.js — other 面板子模块
 * ===================================================================== */
import { $, $$, el, esc, toast } from "../dom.js";
import { State } from "../state.js";
import { getJSON, postJSON, delJSON, parseSSE } from "../api.js";
import * as Views from "../views.js";
import { sendMessage } from "../chat.js";
import { relTime } from "../util.js";
// ---- Goals 常驻目标（复用内核 Hermes Goals：按会话、state.db 持久化、裁判循环） ----
export async function renderGoalsPanel(body) {
  body.innerHTML = '';
  const cid = State.conv_id || '';
  body.appendChild(el('div', { class: 'section-title', text: '目标（常驻 · 按会话）' }));
  body.appendChild(el('div', { class: 'muted small', text: '为「当前会话」设定一个长期目标。每轮对话后，Hermes 会用裁判模型判断是否已被满足；未满足时你可以在下方或对话区点「继续目标」推进下一轮（不会自动连跑）。目标保存在本机数据目录，仅对该会话有效。' }));
  if (!cid) {
    body.appendChild(el('div', { class: 'muted', text: '请先开始或选择一个会话，再设定目标。' }));
    return;
  }
  const d = await getJSON('/api/features/goals?conv_id=' + encodeURIComponent(cid)).catch(() => ({ ok: false }));
  if (!d || !d.ok) {
    body.appendChild(el('div', { class: 'muted', text: '目标加载失败：' + ((d && d.error) || '') }));
    return;
  }
  if (!d.available) {
    body.appendChild(el('div', { class: 'muted', text: '内核 Goals 模块不可用：' + (d.error || '') }));
    return;
  }
  const st = d.state;
  if (!st) {
    const ta = el('textarea', { class: 'editor', rows: 3, placeholder: '描述你的目标…\n（可附内联契约：verify: … / constraints: … / boundaries: … / stop when: …）' });
    const mt = el('input', { type: 'number', class: 'form-input', style: 'width:90px;', value: 20, min: 1, max: 200, title: '最大轮次' });
    body.appendChild(el('div', { class: 'field' }, [
      el('label', { text: '设定本会话目标' }), ta,
      el('div', { class: 'field-inline' }, [el('span', { class: 'muted small', text: '最大轮次（防无限续跑）' }), mt]),
      el('button', { class: 'btn primary', text: '设定目标', onclick: async () => {
        if (!ta.value.trim()) { toast('请输入目标内容', 'err'); return; }
        const r = await postJSON('/api/features/goals', { conv_id: cid, text: ta.value.trim(), max_turns: parseInt(mt.value) || 20 }).catch(e => ({ ok: false, error: e.message }));
        if (r.ok) { toast('目标已设定', 'ok'); renderGoalsPanel(body); } else toast(r.error || '设定失败', 'err');
      } }),
    ]));
    return;
  }

  // 状态条
  const statusLabel = { active: '进行中', paused: '已暂停', done: '已完成', cleared: '已清除' }[st.status] || st.status;
  const statusCls = { active: 'on', paused: 'warn', done: 'on', cleared: '' }[st.status] || '';
  body.appendChild(el('div', { class: 'goal-status-bar' }, [
    el('span', { class: 'badge ' + statusCls, text: statusLabel }),
    el('span', { class: 'muted small', text: `轮次 ${st.turns_used}/${st.max_turns}` }),
  ]));
  body.appendChild(el('div', { class: 'goal-text', text: st.goal }));
  if (st.last_verdict) {
    body.appendChild(el('div', { class: 'muted small', text: `上次裁判：${st.last_verdict}${st.last_reason ? ' — ' + st.last_reason : ''}` }));
  }
  if (st.is_waiting) {
    body.appendChild(el('div', { class: 'muted small', text: '⏳ 目标已泊车（等待外部条件）：' + (st.waiting_reason || '') }));
  }
  if (st.has_contract) {
    const cd = st.contract || {};
    const labels = { outcome: '目标', verification: '验收', constraints: '约束', boundaries: '边界', stop_when: '停止条件' };
    const lines = [];
    for (const k of ['outcome', 'verification', 'constraints', 'boundaries', 'stop_when']) {
      if (cd[k] && cd[k].trim()) lines.push(el('div', { class: 'cr-desc', text: `${labels[k]}：${cd[k]}` }));
    }
    if (lines.length) {
      body.appendChild(el('div', { class: 'section-subtitle', text: '完成契约' }));
      body.appendChild(el('div', { class: 'goal-contract' }, lines));
    }
  }
  // 子目标
  if (st.subgoals && st.subgoals.length) {
    body.appendChild(el('div', { class: 'section-subtitle', text: '子目标' }));
    const sg = el('div', { class: 'card-list' });
    st.subgoals.forEach((s, i) => {
      sg.appendChild(el('div', { class: 'card-row' }, [
        el('div', { class: 'cr-main' }, [el('div', { class: 'cr-title', text: `${i + 1}. ${s}` })]),
        el('div', { class: 'cr-actions' }, [el('button', { class: 'btn ghost sm danger', text: '移除', onclick: async () => {
          const r = await postJSON('/api/features/goals/subgoal/remove', { conv_id: cid, index: i + 1 }).catch(e => ({ ok: false, error: e.message }));
          if (r.ok) { toast('已移除', 'ok'); renderGoalsPanel(body); } else toast(r.error || '失败', 'err');
        } })]),
      ]));
    });
    body.appendChild(sg);
  }
  const sgInp = el('input', { class: 'form-input', placeholder: '新增子目标（判定时一并考量）' });
  body.appendChild(el('div', { class: 'field' }, [el('label', { text: '添加子目标' }), sgInp, el('button', { class: 'btn primary sm', text: '添加', onclick: async () => {
    if (!sgInp.value.trim()) { toast('请输入子目标', 'err'); return; }
    const r = await postJSON('/api/features/goals/subgoal', { conv_id: cid, text: sgInp.value.trim() }).catch(e => ({ ok: false, error: e.message }));
    if (r.ok) { toast('已添加', 'ok'); renderGoalsPanel(body); } else toast(r.error || '失败', 'err');
  } })]));

  // 操作按钮
  const actions = el('div', { class: 'actions-row', style: 'margin-top:12px;' });
  if (st.status === 'active') {
    actions.appendChild(el('button', { class: 'btn ghost sm', text: '暂停', onclick: async () => {
      const r = await postJSON('/api/features/goals/pause', { conv_id: cid, reason: 'user-paused' }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast('已暂停', 'ok'); renderGoalsPanel(body); } else toast(r.error || '失败', 'err');
    } }));
    actions.appendChild(el('button', { class: 'btn ghost sm', text: '标记完成', onclick: async () => {
      const r = await postJSON('/api/features/goals/mark-done', { conv_id: cid, reason: 'user marked done' }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast('已标记完成', 'ok'); renderGoalsPanel(body); } else toast(r.error || '失败', 'err');
    } }));
    // G1：目标评测——把当前会话最后一条助手回复交给裁判模型评估完成度
    actions.appendChild(el('button', { class: 'btn ghost sm', text: '评测', onclick: async () => {
      try {
        const conv = await getJSON('/api/conversations/' + encodeURIComponent(cid)).catch(() => null);
        const msgs = (conv && conv.messages) || [];
        let last = '';
        for (let i = msgs.length - 1; i >= 0; i--) {
          if (msgs[i].role === 'assistant') { last = msgs[i].text || msgs[i].html || msgs[i].content || ''; break; }
        }
        const r = await postJSON('/api/features/goals/evaluate', { conv_id: cid, last_response: last }).catch(e => ({ ok: false, error: e.message }));
        if (!r || !r.ok) { toast((r && r.error) ? r.error : '评测失败', 'err'); return; }
        if (r.decision && r.decision.verdict) {
          toast('评测结论：' + r.decision.verdict + (r.decision.message ? ' — ' + r.decision.message : ''), 'ok');
        } else {
          toast('已评测（本轮无新结论）', 'ok');
        }
        renderGoalsPanel(body);
      } catch (e) { toast('评测失败：' + e.message, 'err'); }
    } }));
  } else if (st.status === 'paused') {
    actions.appendChild(el('button', { class: 'btn primary sm', text: '继续', onclick: async () => {
      const r = await postJSON('/api/features/goals/resume', { conv_id: cid }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast('已继续', 'ok'); renderGoalsPanel(body); } else toast(r.error || '失败', 'err');
    } }));
  }
  actions.appendChild(el('button', { class: 'btn ghost sm danger', text: '清除目标', onclick: async () => {
    if (!confirm('清除当前会话目标？')) return;
    const r = await postJSON('/api/features/goals/clear', { conv_id: cid }).catch(e => ({ ok: false, error: e.message }));
    if (r.ok) { toast('已清除', 'ok'); renderGoalsPanel(body); } else toast(r.error || '失败', 'err');
  } }));
  body.appendChild(actions);

  if (st.status === 'active' && d.judge_available === false) {
    body.appendChild(el('div', { class: 'muted small', style: 'margin-top:8px;', text: 'ℹ 当前未配置裁判模型(goal_judge)，目标仅作记录；完成与否需你手动判断并点「标记完成」。' }));
  }
}

// ---- Checkpoints 对话快照 ----
export async function renderCheckpointsPanel(body) {
  const convs = await getJSON('/api/conversations').catch(() => ({ ok: false }));
  if (!convs || !convs.ok) { body.appendChild(el('div', { class: 'muted', text: '加载失败' })); return; }
  const convItems = convs.items || [];
  body.appendChild(el('div', { class: 'section-title', text: '对话快照管理' }));
  body.appendChild(el('div', { class: 'muted small', text: '保存/恢复/对比对话历史快照。选择会话后查看和管理其快照。' }));
  const sel = el('select', { class: 'form-input' });
  sel.appendChild(el('option', { value: '', text: '选择会话…' }));
  for (const conv of convItems) sel.appendChild(el('option', { value: conv.id, text: conv.title || conv.id }));
  const wrap = el('div', { style: 'margin-top:12px;' });
  body.appendChild(el('div', { class: 'field' }, [el('label', { text: '选择会话' }), sel])); body.appendChild(wrap);
  sel.addEventListener('change', async () => {
    const cid = sel.value; if (!cid) { wrap.innerHTML = ''; return; }
    wrap.innerHTML = '<div class="muted">加载中…</div>';
    const d = await getJSON('/api/features/checkpoints/' + cid).catch(() => ({ ok: false }));
    wrap.innerHTML = '';
    if (!d || !d.ok) { wrap.appendChild(el('div', { class: 'muted', text: '加载失败' })); return; }
    const items = d.items || [];
    wrap.appendChild(el('div', { class: 'actions-row' }, [el('button', { class: 'btn primary', text: '创建快照', onclick: async () => {
      const label = prompt('快照标签（可选）：');
      const r = await postJSON('/api/features/checkpoints/' + cid, { label: label || '' }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast('快照已创建', 'ok'); sel.dispatchEvent(new Event('change')); } else toast(r.error || '创建失败', 'err');
    } })]));
    if (!items.length) { wrap.appendChild(el('div', { class: 'muted', text: '暂无快照' })); return; }
    const list = el('div', { class: 'card-list' });
    for (const cp of items) {
      const row = el('div', { class: 'card-row' });
      row.appendChild(el('div', { class: 'cr-main' }, [el('div', { class: 'cr-title' }, [el('span', { text: cp.label }), el('span', { class: 'badge', text: cp.msg_count + ' 条消息' })]), el('div', { class: 'cr-desc', text: cp.created })]));
      row.appendChild(el('div', { class: 'cr-actions' }, [
        el('button', { class: 'btn ghost sm', text: '恢复', onclick: async () => {
          if (!confirm('恢复快照将替换当前会话消息，确定？')) return;
          const r = await postJSON('/api/features/checkpoints/' + cid + '/' + cp.id + '/restore').catch(e => ({ ok: false, error: e.message }));
          if (r.ok) { toast('已恢复：' + r.label, 'ok'); } else toast(r.error || '恢复失败', 'err');
        } }),
        el('button', { class: 'btn ghost sm danger', text: '删除', onclick: async () => {
          if (!confirm('删除快照「' + cp.label + '」？')) return;
          const r = await postJSON('/api/features/checkpoints/' + cid + '/' + cp.id + '/delete').catch(e => ({ ok: false, error: e.message }));
          if (r.ok) { toast('已删除', 'ok'); sel.dispatchEvent(new Event('change')); } else toast('失败', 'err');
        } }),
      ]));
      list.appendChild(row);
    }
    wrap.appendChild(list);
  });
}

// ---- MOA 多智能体混合（Hermes 原生：复用内核 moa_config，配置落 config.yaml） ----
export async function renderMoaPanel(body) {
  body.innerHTML = '';
  const d = await getJSON('/api/features/moa').catch(() => ({ ok: false }));
  body.appendChild(el('div', { class: 'section-title', text: '多智能体混合（MOA）' }));
  if (!d || !d.ok) {
    body.appendChild(el('div', { class: 'muted', text: '加载失败：' + ((d && d.error) || '未知错误') }));
    return;
  }
  if (d.available === false) {
    body.appendChild(el('div', { class: 'tag err', text: '内核 hermes_cli.moa_config 不可用，MOA 功能暂不可用' }));
    return;
  }
  body.appendChild(el('div', { class: 'muted small', text: 'MOA 让多个「参考模型」各自对当前任务给建议，再由一个「聚合模型」综合成最终回答。配置保存在本机 config.yaml，激活后当前模型自动走 MOA。' }));

  if (d.active_in_agent) {
    body.appendChild(el('div', { class: 'tag ok', text: '● 当前已激活 MOA 预设：' + (d.agent_model || '') }));
  } else {
    body.appendChild(el('div', { class: 'muted small', text: '当前未以 MOA 运行（使用普通模型）。点某预设的「设为当前模型」即可激活。' }));
  }

  const presets = JSON.parse(JSON.stringify(d.presets || {}));
  let defaultPresetLocal = d.default_preset || '';
  const activePreset = d.active_preset || '';

  const listEl = el('div', { class: 'card-list' });
  body.appendChild(listEl);

  function slotRow(container, slot, onRemove) {
    const row = el('div', { class: 'field-inline' });
    const p = el('input', { class: 'form-input', style: 'width:130px;', placeholder: 'provider', value: slot.provider || '' });
    const m = el('input', { class: 'form-input', style: 'flex:1;', placeholder: 'model', value: slot.model || '' });
    p.oninput = () => slot.provider = p.value;
    m.oninput = () => slot.model = m.value;
    row.appendChild(p); row.appendChild(m);
    if (onRemove) row.appendChild(el('button', { class: 'btn ghost sm danger', text: '✕', onclick: onRemove }));
    container.appendChild(row);
  }

  function buildPresetCard(name) {
    const p = presets[name] || (presets[name] = {});
    if (!Array.isArray(p.reference_models)) p.reference_models = [];
    if (!p.aggregator) p.aggregator = { provider: '', model: '' };
    if (typeof p.fanout !== 'string') p.fanout = 'per_iteration';
    if (typeof p.max_tokens !== 'number') p.max_tokens = 4096;

    const card = el('div', { class: 'card-row' });
    const main = el('div', { class: 'cr-main' });
    main.appendChild(el('div', { class: 'cr-title' }, [
      el('span', { text: name }),
      (name === defaultPresetLocal) ? el('span', { class: 'badge', text: '默认' }) : null,
      (name === activePreset) ? el('span', { class: 'badge ok', text: '激活' }) : null,
    ].filter(Boolean)));

    const enCb = el('input', { type: 'checkbox', checked: !!p.enabled });
    enCb.onchange = () => p.enabled = enCb.checked;
    main.appendChild(el('div', { class: 'field-inline' }, [enCb, el('span', { text: '启用此预设' })]));

    main.appendChild(el('div', { class: 'field' }, [el('label', { text: '参考模型（多个，各自给建议）' })]));
    const refsBox = el('div', {});
    p.reference_models.forEach((slot, i) => {
      slotRow(refsBox, slot, () => { p.reference_models.splice(i, 1); rerender(); });
    });
    main.appendChild(refsBox);
    main.appendChild(el('button', { class: 'btn ghost sm', text: '+ 添加参考模型', onclick: () => { p.reference_models.push({ provider: '', model: '' }); rerender(); } }));

    main.appendChild(el('div', { class: 'field' }, [el('label', { text: '聚合模型（综合成最终回答）' })]));
    const aggBox = el('div', {});
    slotRow(aggBox, p.aggregator, null);
    main.appendChild(aggBox);

    const fanSel = el('select', { class: 'form-input' });
    for (const f of ['per_iteration', 'user_turn']) fanSel.appendChild(el('option', { value: f, text: f, selected: p.fanout === f }));
    fanSel.onchange = () => p.fanout = fanSel.value;
    main.appendChild(el('div', { class: 'field' }, [el('label', { text: 'fanout（参考模型重跑时机）' }), fanSel]));

    const rmt = el('input', { type: 'number', class: 'form-input', style: 'width:90px;', placeholder: '不限', value: (p.reference_max_tokens != null ? p.reference_max_tokens : '') });
    rmt.oninput = () => p.reference_max_tokens = rmt.value === '' ? null : (parseInt(rmt.value) || null);
    main.appendChild(el('div', { class: 'field' }, [el('label', { text: '参考模型最大输出 token（空=不限，降低延迟）' }), rmt]));

    const mt = el('input', { type: 'number', class: 'form-input', style: 'width:90px;', value: p.max_tokens || 4096 });
    mt.oninput = () => p.max_tokens = parseInt(mt.value) || 4096;
    main.appendChild(el('div', { class: 'field' }, [el('label', { text: '聚合模型最大输出 token' }), mt]));

    const actions = el('div', { class: 'cr-actions' });
    actions.appendChild(el('button', { class: 'btn ghost sm', text: '设为默认', onclick: async () => { defaultPresetLocal = name; await saveAll(); } }));
    actions.appendChild(el('button', { class: 'btn primary sm', text: (name === activePreset ? '已激活' : '设为当前模型'), onclick: async () => {
      const r = await postJSON('/api/features/moa/activate', { name }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast('已激活 MOA：' + name, 'ok'); renderMoaPanel(body); } else toast('激活失败：' + (r.error || ''), 'err');
    } }));
    if (name === activePreset) actions.appendChild(el('button', { class: 'btn ghost sm', text: '取消激活', onclick: async () => {
      const r = await postJSON('/api/features/moa/deactivate', {}).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast('已取消激活', 'ok'); renderMoaPanel(body); } else toast('失败：' + (r.error || ''), 'err');
    } }));
    actions.appendChild(el('button', { class: 'btn ghost sm danger', text: '删除', onclick: async () => {
      if (!confirm('删除 MOA 预设「' + name + '」？')) return;
      const r = await postJSON('/api/features/moa/delete', { name }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast('已删除', 'ok'); renderMoaPanel(body); } else toast('删除失败：' + (r.error || ''), 'err');
    } }));
    main.appendChild(actions);
    card.appendChild(main);
    return card;
  }

  function rerender() {
    listEl.innerHTML = '';
    Object.keys(presets).forEach(name => listEl.appendChild(buildPresetCard(name)));
  }

  async function saveAll() {
    const payload = { presets, default_preset: defaultPresetLocal, active_preset: activePreset };
    const r = await postJSON('/api/features/moa', payload).catch(e => ({ ok: false, error: e.message }));
    if (r.ok) toast('已保存 MOA 预设', 'ok'); else toast('保存失败：' + (r.error || ''), 'err');
  }

  rerender();

  const newName = el('input', { class: 'form-input', placeholder: '新预设名（如 my_moa）', style: 'width:160px;' });
  body.appendChild(el('div', { class: 'field-inline', style: 'margin-top:10px;' }, [
    newName,
    el('button', { class: 'btn ghost sm', text: '+ 新增预设', onclick: () => {
      const n = (newName.value || '').trim();
      if (!n) { toast('请输入预设名', 'err'); return; }
      if (presets[n]) { toast('预设已存在', 'err'); return; }
      presets[n] = { enabled: true, reference_models: [{ provider: '', model: '' }], aggregator: { provider: '', model: '' }, fanout: 'per_iteration', max_tokens: 4096, reference_max_tokens: null };
      rerender();
    } }),
  ]));
  body.appendChild(el('div', { class: 'actions-row', style: 'margin-top:6px;' }, [
    el('button', { class: 'btn primary', text: '保存全部预设', onclick: saveAll }),
  ]));

  // 一次性 MOA 单轮（无需切换当前模型）：编码为标记串后作为普通消息发送
  body.appendChild(el('div', { class: 'section-title', style: 'margin-top:16px;', text: '用 MOA 跑一句话（不改当前模型）' }));
  const onePrompt = el('textarea', { class: 'editor', rows: 2, placeholder: '输入一句话，用当前默认 MOA 预设跑一次' });
  body.appendChild(onePrompt);
  body.appendChild(el('div', { class: 'actions-row' }, [
    el('button', { class: 'btn ghost sm', text: '生成并发送', onclick: async () => {
      const prompt = onePrompt.value.trim();
      if (!prompt) { toast('请输入内容', 'err'); return; }
      const r = await postJSON('/api/features/moa/encode', { prompt, preset: defaultPresetLocal }).catch(e => ({ ok: false, error: e.message }));
      if (!r.ok) { toast('编码失败：' + (r.error || ''), 'err'); return; }
      const ta = $("#prompt");
      if (ta) ta.textContent = r.encoded;
      if (typeof sendMessage === 'function') sendMessage();
      else toast('请手动把标记串粘贴到对话框发送', 'warn');
    } }),
  ]));
}

// ---- Projects 项目管理（Hermes 原生 projects.db） ----
export async function renderProjectsPanel(body) {
  const d = await getJSON('/api/features/projects').catch(() => ({ ok: false }));
  if (!d || !d.ok) {
    if (d && d.available === false) {
      body.appendChild(el('div', { class: 'tag err', text: '内核 hermes_cli.projects_db 不可用，项目管理暂不可用' }));
    } else {
      body.appendChild(el('div', { class: 'muted', text: '加载失败' }));
    }
    return;
  }
  body.appendChild(el('div', { class: 'section-title', text: '项目管理（Hermes 原生）' }));
  body.appendChild(el('div', { class: 'muted small', text: '项目 = 命名的工作区（可含多个文件夹），用于把桌面会话分组到项目；可绑定看板(board)。活动项目标有 ★。' }));

  // 新建项目
  const np = el('input', { class: 'form-input', placeholder: '项目名称（必填）', style: 'margin-bottom:4px;' });
  const nd = el('textarea', { class: 'editor', rows: 2, placeholder: '描述（可选）' });
  const nf = el('input', { class: 'form-input', placeholder: '主文件夹路径（可选，首个文件夹即主仓库）', style: 'margin-bottom:4px;' });
  const na = el('input', { class: 'form-input', placeholder: '看板 slug（可选，绑定看板）', style: 'margin-bottom:4px;' });
  const setActive = el('input', { type: 'checkbox' });
  body.appendChild(el('div', { class: 'field' }, [
    el('label', { text: '新建项目' }), np, nd, nf, na,
    el('label', { class: 'check', style: 'display:flex;align-items:center;gap:6px;margin:4px 0;' }, [setActive, el('span', { text: '创建后设为当前项目' })]),
    el('button', { class: 'btn primary', text: '创建', onclick: async () => {
      if (!np.value.trim()) { toast('请输入项目名称', 'err'); return; }
      const r = await postJSON('/api/features/projects', {
        name: np.value.trim(), description: nd.value.trim(),
        folders: nf.value.trim() ? [nf.value.trim()] : [],
        primary_path: nf.value.trim() || null,
        board_slug: na.value.trim() || null,
        set_active: setActive.checked,
      }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast('已创建', 'ok'); renderProjectsPanel(body); } else toast(r.error || '创建失败', 'err');
    } }),
  ]));

  // 列表
  const items = d.items || [];
  const list = el('div', { class: 'card-list' });
  for (const p of items) {
    const folderCount = (p.folders || []).length;
    const meta = [
      p.slug ? el('span', { class: 'badge', text: p.slug }) : null,
      p.active ? el('span', { class: 'badge', text: '★ 当前' }) : null,
      folderCount ? el('span', { class: 'badge', text: folderCount + ' 文件夹' }) : null,
      p.board_slug ? el('span', { class: 'badge', text: '板:' + p.board_slug }) : null,
    ].filter(Boolean);
    const row = el('div', { class: 'card-row' });
    row.appendChild(el('div', { class: 'cr-main' }, [
      el('div', { class: 'cr-title' }, [el('span', { text: p.name }), ...meta]),
      el('div', { class: 'cr-desc', text: (p.primary_path || p.description || '') }),
    ]));
    row.appendChild(el('div', { class: 'cr-actions' }, [
      el('button', { class: 'btn ghost sm', text: '详情', onclick: () => showProjectDetail(p.id, body) }),
      p.active ? null : el('button', { class: 'btn ghost sm', text: '设为当前', onclick: async () => {
        const r = await postJSON('/api/features/projects/' + p.id + '/activate', {}).catch(e => ({ ok: false, error: e.message }));
        if (r.ok) { toast('已设为当前', 'ok'); renderProjectsPanel(body); } else toast(r.error || '失败', 'err');
      } }),
      el('button', { class: 'btn ghost sm danger', text: '删除', onclick: async () => {
        if (!confirm('删除项目「' + p.name + '」？此操作不可恢复。')) return;
        const r = await postJSON('/api/features/projects/' + p.id + '/delete').catch(e => ({ ok: false, error: e.message }));
        if (r.ok) { toast('已删除', 'ok'); renderProjectsPanel(body); } else toast(r.error || '失败', 'err');
      } }),
    ].filter(Boolean)));
    list.appendChild(row);
  }
  if (!items.length) list.appendChild(el('div', { class: 'muted', text: '暂无项目，在上方创建' }));
  body.appendChild(list);
}

async function showProjectDetail(pid, body) {
  const d = await getJSON('/api/features/projects').catch(() => ({ ok: false }));
  const p = d && d.items ? d.items.find(x => x.id === pid) : null;
  if (!p) { toast('项目不存在', 'err'); return; }
  const ov = el('div', { class: 'ov' });
  const box = el('div', { class: 'ov-box', style: 'max-height:82vh;overflow:auto;width:620px;' });
  box.appendChild(el('div', { class: 'section-title' }, [
    el('span', { text: p.name }),
    p.active ? el('span', { class: 'badge', text: '★ 当前' }) : null,
    p.slug ? el('span', { class: 'badge', text: p.slug }) : null,
  ].filter(Boolean)));
  box.appendChild(el('div', { class: 'muted small', text: (p.description || '（无描述）') }));

  // 编辑字段
  const mk = (label, val, ph) => {
    const inp = el('input', { class: 'form-input', value: val || '', placeholder: ph || '' });
    return { inp, field: el('div', { class: 'field' }, [el('label', { text: label }), inp]) };
  };
  const nameF = mk('名称', p.name);
  const descF = mk('描述', p.description);
  const iconF = mk('图标(emoji)', p.icon, '如 🚀');
  const colorF = mk('颜色', p.color, '如 #2a7');
  const boardF = mk('看板 slug', p.board_slug, '绑定看板（可选）');
  const primaryF = mk('主文件夹', p.primary_path, '绝对路径');
  box.appendChild(el('div', { class: 'field', style: 'margin-top:10px;' }, [el('label', { text: '编辑项目' })]));
  [nameF, descF, iconF, colorF, boardF, primaryF].forEach(x => box.appendChild(x.field));
  box.appendChild(el('button', { class: 'btn primary', text: '保存', onclick: async () => {
    const r = await postJSON('/api/features/projects/' + p.id + '/update', {
      name: nameF.inp.value.trim(), description: descF.inp.value.trim(),
      icon: iconF.inp.value.trim(), color: colorF.inp.value.trim(),
      board_slug: boardF.inp.value.trim(), primary_path: primaryF.inp.value.trim(),
    }).catch(e => ({ ok: false, error: e.message }));
    if (r.ok) { toast('已保存', 'ok'); ov.remove(); showProjectDetail(p.id, body); } else toast(r.error || '保存失败', 'err');
  } }));

  // 文件夹
  box.appendChild(el('div', { class: 'field', style: 'margin-top:14px;' }, [el('label', { text: '文件夹' })]));
  const folderList = el('div', { class: 'card-list' });
  for (const f of (p.folders || [])) {
    const frow = el('div', { class: 'card-row' });
    frow.appendChild(el('div', { class: 'cr-main' }, [
      el('div', { class: 'cr-title' }, [el('span', { text: f.path }), f.is_primary ? el('span', { class: 'badge', text: '主' }) : null].filter(Boolean)),
      f.label ? el('div', { class: 'cr-desc', text: f.label }) : null,
    ].filter(Boolean)));
    frow.appendChild(el('div', { class: 'cr-actions' }, [
      el('button', { class: 'btn ghost sm danger', text: '移除', onclick: async () => {
        const r = await postJSON('/api/features/projects/' + p.id + '/remove-folder', { path: f.path }).catch(e => ({ ok: false, error: e.message }));
        if (r.ok) { ov.remove(); showProjectDetail(p.id, body); } else toast(r.error || '失败', 'err');
      } }),
    ]));
    folderList.appendChild(frow);
  }
  if (!(p.folders || []).length) folderList.appendChild(el('div', { class: 'muted', text: '暂无文件夹' }));
  box.appendChild(folderList);
  const fp = el('input', { class: 'form-input', placeholder: '添加文件夹路径', style: 'margin-top:6px;' });
  const fpPrimary = el('input', { type: 'checkbox' });
  box.appendChild(el('div', { class: 'field' }, [
    fp,
    el('label', { class: 'check', style: 'display:flex;align-items:center;gap:6px;margin:4px 0;' }, [fpPrimary, el('span', { text: '设为主文件夹' })]),
    el('button', { class: 'btn ghost sm', text: '添加文件夹', onclick: async () => {
      if (!fp.value.trim()) { toast('请输入路径', 'err'); return; }
      const r = await postJSON('/api/features/projects/' + p.id + '/add-folder', { path: fp.value.trim(), primary: fpPrimary.checked }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { ov.remove(); showProjectDetail(p.id, body); } else toast(r.error || '添加失败', 'err');
    } }),
  ]));

  // 操作
  box.appendChild(el('div', { style: 'display:flex;gap:8px;margin-top:14px;' }, [
    p.active ? null : el('button', { class: 'btn primary', text: '设为当前项目', onclick: async () => {
      const r = await postJSON('/api/features/projects/' + p.id + '/activate', {}).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast('已设为当前', 'ok'); ov.remove(); showProjectDetail(p.id, body); } else toast(r.error || '失败', 'err');
    } }),
    el('button', { class: 'btn ghost danger', text: '删除项目', onclick: async () => {
      if (!confirm('删除项目「' + p.name + '」？此操作不可恢复。')) return;
      const r = await postJSON('/api/features/projects/' + p.id + '/delete').catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast('已删除', 'ok'); ov.remove(); renderProjectsPanel(body); } else toast(r.error || '失败', 'err');
    } }),
    el('button', { class: 'btn ghost', text: '关闭', onclick: () => ov.remove() }),
  ].filter(Boolean)));

  ov.appendChild(box);
  ov.addEventListener('click', (e) => { if (e.target === ov) ov.remove(); });
  document.body.appendChild(ov);
}

// ---- Bundles 捆绑包（Hermes 原生） ----
export async function renderBundlesPanel(body) {
  const d = await getJSON('/api/features/bundles').catch(() => ({ ok: false }));
  if (!d || !d.ok) { body.appendChild(el('div', { class: 'muted', text: '加载失败' })); return; }
  if (d.available === false) {
    body.appendChild(el('div', { class: 'section-title', text: '技能捆绑包' }));
    body.appendChild(el('div', { class: 'muted small', text: '（Hermes 内核 skill_bundles 不可用，功能暂不可用）' }));
    return;
  }
  body.appendChild(el('div', { class: 'section-title', text: '技能捆绑包（Hermes 原生）' }));
  body.appendChild(el('div', { class: 'muted small', text: '把多个技能打包成一个「/<名称>」斜杠命令：在对话里输入 /<名称> 即可一次加载这些技能。（数据存于 Hermes 原生的 skill-bundles 目录，与内核 / 命令行 / 对话斜杠命令一致。）' }));
  const items = d.items || [];
  const nn = el('input', { class: 'form-input', placeholder: '捆绑包名称（即斜杠命令 /名称）', style: 'margin-bottom:4px;' });
  const nd = el('input', { class: 'form-input', placeholder: '描述（可选）', style: 'margin-bottom:4px;' });
  const ns = el('input', { class: 'form-input', placeholder: '技能 ID，逗号分隔', style: 'margin-bottom:4px;' });
  const ni = el('textarea', { class: 'form-input', placeholder: '额外注入指令（可选，调用时附在技能内容前）', style: 'margin-bottom:4px;' });
  const ow = el('label', { class: 'muted small', style: 'display:block;margin-bottom:6px;' }, [el('input', { type: 'checkbox', style: 'margin-right:6px;' }), document.createTextNode('覆盖同名已存在的捆绑包')]);
  body.appendChild(el('div', { class: 'field' }, [el('label', { text: '创建捆绑包' }), nn, nd, ns, ni, ow, el('button', { class: 'btn primary', text: '创建', onclick: async () => {
    if (!nn.value.trim() || !ns.value.trim()) { toast('请填写名称和技能列表', 'err'); return; }
    const skills = ns.value.split(',').map(s => s.trim()).filter(Boolean);
    const r = await postJSON('/api/features/bundles', {
      name: nn.value.trim(), skills, description: nd.value.trim(),
      instruction: ni.value.trim(), overwrite: ow.querySelector('input').checked,
    }).catch(e => ({ ok: false, error: e.message }));
    if (r.ok) { toast('已创建', 'ok'); renderBundlesPanel(body); }
    else if (r.exists) { toast(r.error + '（可勾选覆盖）', 'err'); }
    else toast(r.error || '创建失败', 'err');
  } })]));
  const list = el('div', { class: 'card-list' });
  for (const b of items) {
    const row = el('div', { class: 'card-row' });
    const sub = [b.slug ? ('/' + b.slug) : '', (b.skills || []).length + ' 个技能'].filter(Boolean).join(' · ');
    row.appendChild(el('div', { class: 'cr-main' }, [el('div', { class: 'cr-title' }, [el('span', { text: b.name }), el('span', { class: 'badge', text: sub })]),
      el('div', { class: 'cr-desc', text: b.description || (b.skills || []).join(', ') }),
      b.instruction ? el('div', { class: 'cr-desc muted small', text: '指令：' + b.instruction }) : null].filter(Boolean)));
    row.appendChild(el('div', { class: 'cr-actions' }, [el('button', { class: 'btn ghost sm danger', text: '卸载', onclick: async () => {
      if (!confirm('卸载捆绑包「' + b.name + '」？')) return;
      const r = await postJSON('/api/features/bundles/uninstall', { name: b.name }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast(r.missing ? '已卸载（原本不存在）' : '已卸载', 'ok'); renderBundlesPanel(body); } else toast('失败', 'err');
    } })]));
    list.appendChild(row);
  }
  if (!items.length) list.appendChild(el('div', { class: 'muted', text: '暂无捆绑包' }));
  body.appendChild(list);
  body.appendChild(el('div', { class: 'actions-row', style: 'margin-top:10px;' }, [el('button', { class: 'btn ghost sm', text: '重新扫描', onclick: async () => {
    const r = await postJSON('/api/features/bundles/reload').catch(e => ({ ok: false, error: e.message }));
    if (r && r.ok) { toast('已重新扫描', 'ok'); renderBundlesPanel(body); } else toast('扫描失败', 'err');
  } })]));
}

// ---- Security Audit 安全审计（Hermes 原生） ----
export async function renderSecurityPanel(body) {
  body.appendChild(el('div', { class: 'section-title', text: '安全审计（Hermes 原生）' }));
  body.appendChild(el('div', { class: 'muted small', text: '复用 Hermes 原生供应链安全审计（hermes security audit）：对三个攻击面——venv 已装依赖 / 插件声明依赖 / config.yaml 里钉版本号的 MCP 服务器——比对 OSV.dev 已知漏洞；并叠加已知投毒包检测（hermes doctor 同源）。查询 OSV.dev 需要联网。' }));
  // 扫描范围勾选（对应内核三个攻击面）
  const mkChk = (label, key) => {
    const cb = el('input', { type: 'checkbox', id: 'sa-' + key });
    return { wrap: el('label', { class: 'chk', style: 'margin-right:14px;display:inline-flex;align-items:center;gap:4px;' }, [cb, el('span', { text: label })]), cb };
  };
  const skVenv = mkChk('跳过 venv', 'venv');
  const skPlugins = mkChk('跳过插件', 'plugins');
  const skMcp = mkChk('跳过 MCP', 'mcp');
  body.appendChild(el('div', { class: 'field', style: 'margin-top:8px;' }, [skVenv.wrap, skPlugins.wrap, skMcp.wrap]));
  const result = el('div', { style: 'margin-top:12px;' });
  body.appendChild(el('div', { class: 'actions-row' }, [el('button', { class: 'btn primary', text: '运行审计', onclick: async () => {
    const opts = {
      skip_venv: skVenv.cb.checked,
      skip_plugins: skPlugins.cb.checked,
      skip_mcp: skMcp.cb.checked,
    };
    result.innerHTML = '<div class="muted">审计中…（比对 OSV.dev）</div>';
    const r = await postJSON('/api/features/security-audit', opts).catch(e => ({ ok: false, available: true, error: e.message }));
    result.innerHTML = '';
    if (!r || r.available === false) {
      result.appendChild(el('div', { class: 'muted', text: (r && r.error) ? ('安全审计不可用：' + r.error) : '安全审计不可用' }));
      return;
    }
    // OSV.dev 联网失败提示（仍展示投毒包检测结果）
    if (r.osv_error) {
      result.appendChild(el('div', { class: 'tag warn', style: 'margin-bottom:8px;', text: '⚠ ' + r.osv_error }));
    }
    // 供应链漏洞（OSV.dev）
    const fc = r.finding_count || 0;
    const total = r.total_components_scanned || 0;
    if (fc === 0 && !r.osv_error) {
      result.appendChild(el('div', { class: 'tag ok', style: 'margin-bottom:8px;', text: `未发现已知漏洞 ✅（已扫描 ${total} 个组件）` }));
    } else if (fc > 0) {
      result.appendChild(el('div', { style: 'font-weight:bold;margin-bottom:6px;', text: `发现 ${fc} 个已知漏洞（扫描 ${total} 个组件）` }));
      for (const f of (r.findings || [])) {
        const sev = (f.severity || 'UNKNOWN').toUpperCase();
        const sevCls = 'tag sev-' + sev.toLowerCase();
        result.appendChild(el('div', { class: 'card-row' }, [
          el('div', { class: 'cr-main' }, [
            el('div', { class: 'cr-title' }, [
              el('span', { class: sevCls, text: f.severity_label || sev }),
              el('span', { text: ` ${f.package}==${f.version}` }),
              el('span', { class: 'muted small', text: `  (${f.ecosystem} · ${f.source})` }),
            ]),
            el('div', { class: 'cr-desc', text: `${f.vuln_id}${f.summary ? ' — ' + f.summary : ''}` }),
            (f.fixed_versions && f.fixed_versions.length) ? el('div', { class: 'cr-desc muted small', text: '修复版本：' + f.fixed_versions.join(', ') }) : null,
          ]),
        ].filter(Boolean)));
      }
    }
    // 已知投毒包（hermes doctor 同源，纯 metadata）
    const adv = r.advisories || [];
    if (adv.length) {
      result.appendChild(el('div', { style: 'font-weight:bold;margin-top:12px;color:#e06c75;', text: `⚠ 发现 ${adv.length} 个已知投毒包` }));
      for (const a of adv) {
        result.appendChild(el('div', { class: 'card-row' }, [
          el('div', { class: 'cr-main' }, [
            el('div', { class: 'cr-title' }, [
              el('span', { class: 'tag sev-critical', text: a.severity_label || a.severity }),
              el('span', { text: ` ${a.package}==${a.installed_version}` }),
            ]),
            el('div', { class: 'cr-desc', text: a.title }),
            el('div', { class: 'cr-desc muted small', text: a.url }),
            (a.remediation && a.remediation.length) ? el('div', { class: 'cr-desc muted small', text: '处置：' + a.remediation.join(' ') }) : null,
          ].filter(Boolean)),
        ]));
      }
    } else {
      result.appendChild(el('div', { class: 'tag ok', style: 'margin-top:12px;', text: '未发现已知投毒包 ✅' }));
    }
  } })]));
  body.appendChild(result);
}

// ---- Blueprints 自动化蓝图（Hermes 原生 cron.blueprint_catalog）----
export async function renderBlueprintsPanel(body) {
  body.innerHTML = '';
  const d = await getJSON('/api/features/blueprints').catch(() => ({ ok: false }));
  if (!d || !d.ok) { body.appendChild(el('div', { class: 'muted', text: '加载失败' })); return; }
  if (d.available === false) {
    body.appendChild(el('div', { class: 'section-title', text: '自动化蓝图 (Automation Blueprints)' }));
    body.appendChild(el('div', { class: 'tag warn', style: 'margin-top:8px;', text: (d.error || 'Blueprint 模块不可用（cron 未安装？）') }));
    return;
  }
  body.appendChild(el('div', { class: 'section-title', text: '自动化蓝图 (Automation Blueprints)' }));
  body.appendChild(el('div', { class: 'muted small', text: '内置自动化模板：选一个 → 填表 → 生成真实定时任务（落入本应用「定时任务中心」）。' }));
  const items = d.items || [];
  const list = el('div', { class: 'card-list' });
  for (const bp of items) {
    const tags = (bp.tags || []).map(t => el('span', { class: 'tag', text: String(t) }));
    const card = el('div', { class: 'card-row' });
    card.appendChild(el('div', { class: 'cr-main' }, [
      el('div', { class: 'cr-title' }, [
        el('span', { text: bp.title }),
        el('span', { class: 'badge on', text: bp.category }),
      ]),
      el('div', { class: 'cr-desc', text: bp.description }),
      el('div', { class: 'muted small', style: 'margin-top:4px;', text: '计划：' + (bp.scheduleHuman || bp.schedule || '') }),
      el('div', { class: 'cr-tags', style: 'margin-top:4px;' }, tags),
    ]));
    card.appendChild(el('div', { class: 'cr-actions' }, [
      el('button', { class: 'btn ghost sm', text: '设置', onclick: () => _renderBlueprintForm(body, bp) }),
    ]));
    list.appendChild(card);
  }
  if (!items.length) list.appendChild(el('div', { class: 'muted', text: '暂无蓝图' }));
  body.appendChild(list);
}

function _renderBlueprintForm(body, bp) {
  const form = el('div', { class: 'field', style: 'margin-top:12px;border:1px solid var(--border);padding:12px;border-radius:8px;' });
  form.appendChild(el('div', { class: 'section-title', text: bp.title }));
  form.appendChild(el('div', { class: 'muted small', text: bp.description }));
  const inputs = {};
  for (const f of (bp.fields || [])) {
    const id = 'bpf-' + f.name;
    const def = (f.name === 'deliver' && (f.options || []).indexOf('local') !== -1) ? 'local' : (f.default == null ? '' : String(f.default));
    let input;
    if (f.type === 'enum' || f.type === 'weekdays') {
      input = el('select', { class: 'form-input', id });
      for (const opt of (f.options || [])) {
        const o = el('option', { value: String(opt), text: String(opt) });
        if (String(opt) === String(def)) o.selected = true;
        input.appendChild(o);
      }
    } else if (f.type === 'time') {
      input = el('input', { class: 'form-input', id, type: 'time', value: def });
    } else {
      input = el('input', { class: 'form-input', id, type: 'text', value: def, placeholder: f.help || '' });
    }
    inputs[f.name] = input;
    form.appendChild(el('div', { class: 'field' }, [
      el('label', { text: f.label + (f.help ? '（' + f.help + '）' : '') }),
      input,
    ]));
  }
  const msg = el('div', { class: 'muted small', style: 'margin-top:8px;' });
  form.appendChild(el('div', { class: 'actions-row', style: 'margin-top:8px;' }, [
    el('button', { class: 'btn primary', text: '生成定时任务', onclick: async () => {
      const values = {};
      for (const f of (bp.fields || [])) values[f.name] = inputs[f.name].value;
      const r = await postJSON('/api/features/blueprints/fill', { key: bp.key, values }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok && r.job) {
        msg.className = 'tag ok';
        msg.textContent = '已创建定时任务 #' + r.job.id + '：' + (r.job.schedule_display || '') + '，交付：' + (r.job.deliver || '');
        toast('已生成定时任务', 'ok');
      } else if (r.kind === 'validation') {
        msg.className = 'tag warn';
        msg.textContent = '填写有误：' + (r.error || '');
      } else {
        msg.className = 'tag warn';
        msg.textContent = '失败：' + (r.error || '未知错误');
      }
    } }),
    el('button', { class: 'btn ghost sm', text: '返回', onclick: () => renderBlueprintsPanel(body) }),
  ]));
  form.appendChild(msg);
  body.innerHTML = '';
  body.appendChild(form);
}

// ---- Batch 批量处理（Hermes 原生 Batch Runner）----
export async function renderBatchPanel(body) {
  body.appendChild(el('div', { class: 'section-title', text: '批量处理（Hermes Batch Runner）' }));
  body.appendChild(el('div', { class: 'muted small', text: 'Hermes 原生批量处理：用 {prompt} 数据集驱动多个隔离的 Agent 会话，生成 ShareGPT 轨迹（训练 / 评测数据）。桌面端单进程串行执行（不使用多进程），每条输入都会真实调用模型。' }));

  // 内核可用性检查 → 降级
  const dist = await getJSON('/api/features/batch/distributions').catch(() => ({ ok: false, available: false }));
  if (!dist || dist.available === false) {
    body.appendChild(el('div', { class: 'tag warn', text: 'Batch Runner 不可用：' + ((dist && dist.error) || 'batch_runner 模块未安装') }));
    return;
  }

  // 输入模式
  const modeSel = el('select', { class: 'input' }, [
    el('option', { value: 'jsonl', text: 'JSONL 数据集（每行 {"prompt": "..."}）' }),
    el('option', { value: 'template', text: '模板 + 多输入（展开为数据集）' }),
  ]);
  const jsonlTa = el('textarea', { class: 'editor', rows: 6, placeholder: '每行一条 JSON：{"prompt": "..."}' });
  const inpTa = el('textarea', { class: 'editor', rows: 4, placeholder: '每行一条输入，或粘贴 JSON 数组 ["文本", ...] / [{id,text}, ...]' });
  const tmplTa = el('textarea', { class: 'editor', rows: 3, placeholder: '提示词模板，用 {input} 占位（仅模板模式）' });
  const tmplBox = el('div', { class: 'field' }, [el('label', { text: '输入与模板（模板模式）' }), inpTa, tmplTa]);
  tmplBox.style.display = 'none';

  modeSel.onchange = () => {
    const tpl = modeSel.value === 'template';
    jsonlTa.parentElement.style.display = tpl ? 'none' : '';
    tmplBox.style.display = tpl ? '' : 'none';
  };

  // 配置
  const distSel = el('select', { class: 'input' });
  for (const d of (dist.items || [])) {
    distSel.appendChild(el('option', { value: d.key, text: d.key + (d.description ? ' — ' + d.description : '') }));
  }
  distSel.value = (dist.items || []).some(d => d.key === 'safe') ? 'safe' : ((dist.items || [])[0] || {}).key || '';
  const reSel = el('select', { class: 'input' }, [
    el('option', { value: '', text: '（默认 / 不指定）' }),
    el('option', { value: 'none', text: 'none' }),
    el('option', { value: 'minimal', text: 'minimal' }),
    el('option', { value: 'low', text: 'low' }),
    el('option', { value: 'medium', text: 'medium' }),
    el('option', { value: 'high', text: 'high' }),
    el('option', { value: 'xhigh', text: 'xhigh' }),
    el('option', { value: 'max', text: 'max' }),
    el('option', { value: 'ultra', text: 'ultra' }),
  ]);
  const runName = el('input', { class: 'input', value: 'desktop_batch', placeholder: 'run_name（输出目录名）' });
  const modelIn = el('input', { class: 'input', value: 'inclusionai/ling-3.0-flash:free', placeholder: '模型' });
  const baseUrl = el('input', { class: 'input', value: 'https://openrouter.ai/api/v1', placeholder: 'base_url' });
  const maxIter = el('input', { class: 'input', value: '10', placeholder: 'max_iterations' });

  const cfgBox = el('div', { class: 'field' }, [
    el('label', { text: '配置' }),
    el('div', { class: 'grid-2' }, [
      el('div', {}, [el('label', { class: 'small', text: 'run_name' }), runName]),
      el('div', {}, [el('label', { class: 'small', text: 'toolset distribution' }), distSel]),
      el('div', {}, [el('label', { class: 'small', text: '模型（默认 OpenRouter 免费）' }), modelIn]),
      el('div', {}, [el('label', { class: 'small', text: 'base_url' }), baseUrl]),
      el('div', {}, [el('label', { class: 'small', text: 'max_iterations' }), maxIter]),
      el('div', {}, [el('label', { class: 'small', text: 'reasoning_effort' }), reSel]),
    ]),
  ]);

  body.appendChild(el('div', { class: 'field' }, [el('label', { text: '输入模式' }), modeSel]));
  body.appendChild(el('div', { class: 'field' }, [el('label', { text: '数据集（JSONL 模式）' }), jsonlTa]));
  body.appendChild(tmplBox);
  body.appendChild(cfgBox);

  const result = el('div', { style: 'margin-top:12px;' });
  body.appendChild(el('div', { class: 'actions-row' }, [el('button', { class: 'btn primary', text: '开始批量', onclick: async () => {
    const rows = buildBatchRows(modeSel.value, jsonlTa.value, inpTa.value, tmplTa.value);
    if (!rows.length) { toast('请至少提供一条有效 prompt', 'err'); return; }
    const opts = {
      run_name: runName.value.trim() || 'desktop_batch',
      model: modelIn.value.trim(),
      base_url: baseUrl.value.trim(),
      max_iterations: parseInt(maxIter.value, 10) || 10,
      distribution: distSel.value,
      reasoning_effort: reSel.value || null,
    };
    result.innerHTML = '<div class="muted">提交中…</div>';
    const r = await postJSON('/api/features/batch/run', { rows, opts })
      .catch(e => ({ ok: false, error: e.message }));
    result.innerHTML = '';
    if (!r || !r.ok) {
      result.appendChild(el('div', { class: 'tag warn', text: '启动失败：' + ((r && r.error) || '未知错误') }));
      return;
    }
    result.appendChild(el('div', { class: 'tag ok', text: `已启动：${r.run_name}（${r.total} 条）run_id=${r.run_id}` }));
    pollBatch(r.run_id, result);
  } })]));
  body.appendChild(result);
}

function buildBatchRows(mode, jsonlVal, inpVal, tmplVal) {
  if (mode === 'template') {
    let inputs = [];
    const raw = inpVal.trim();
    if (!raw) return [];
    try { inputs = JSON.parse(raw); } catch { inputs = raw.split('\n').map(s => s.trim()).filter(Boolean); }
    const tmpl = tmplVal;
    const rows = [];
    for (const it of inputs) {
      const text = (typeof it === 'string') ? it : (it.text || it.prompt || '');
      if (!text) continue;
      rows.push({ prompt: tmpl.replace(/\{input\}/g, text) });
    }
    return rows;
  }
  // jsonl 模式
  const rows = [];
  for (const line of jsonlVal.split('\n')) {
    const s = line.trim();
    if (!s) continue;
    try {
      const o = JSON.parse(s);
      const p = o.prompt || o.text || '';
      if (p) rows.push({ prompt: p });
    } catch { /* 跳过非法行 */ }
  }
  return rows;
}

let _batchTimer = null;
function pollBatch(run_id, result) {
  if (_batchTimer) clearTimeout(_batchTimer);
  _batchTimer = setTimeout(async () => {
    const s = await getJSON(`/api/features/batch/status/${run_id}`).catch(e => ({ ok: false, error: e.message }));
    if (!s || !s.ok) {
      result.appendChild(el('div', { class: 'muted', text: '状态获取失败：' + ((s && s.error) || '') }));
      return;
    }
    // 进度
    const pct = s.total ? Math.round((s.processed / s.total) * 100) : 0;
    let prog = result.querySelector('.batch-prog');
    if (!prog) {
      prog = el('div', { class: 'batch-prog' });
      result.appendChild(prog);
    }
    prog.innerHTML = `<div class="muted">进度：${s.processed}/${s.total}（${pct}%）— 状态：${s.status}</div>`;

    if (s.status === 'running') { pollBatch(run_id, result); return; }

    // 终态：渲染结果
    const wrap = el('div', { style: 'margin-top:10px;' });
    for (const item of (s.results || [])) {
      const badgeCls = item.success ? 'on' : (item.status === 'discarded' ? '' : 'off');
      wrap.appendChild(el('div', { class: 'card-row' }, [
        el('div', { class: 'cr-main' }, [
          el('div', { class: 'cr-title' }, [
            el('span', { text: '#' + item.prompt_index }),
            el('span', { class: 'badge ' + badgeCls, text: item.status }),
          ]),
          el('div', { class: 'cr-desc', text: item.prompt }),
          item.success
            ? el('div', { class: 'cr-desc', text: (item.output || '').slice(0, 300) + (item.api_calls != null ? `  [api_calls=${item.api_calls}]` : '') })
            : el('div', { class: 'cr-desc', style: 'color:var(--danger)', text: '错误：' + (item.error || '未知') }),
        ]),
      ]));
    }
    // 统计
    const st = s.statistics || {};
    const ts = st.tool_stats || {};
    const tsStr = Object.entries(ts).map(([k, v]) => `${k}:${v.count}(✓${v.success}/✗${v.failure})`).join('  ') || '无';
    wrap.appendChild(el('div', { class: 'tag', text: `统计：总数 ${st.total || 0} / 失败 ${st.failed || 0} / 无推理被丢弃 ${st.discarded_no_reasoning || 0} / 耗时 ${st.duration_sec || 0}s` }));
    wrap.appendChild(el('div', { class: 'muted small', text: '工具统计：' + tsStr }));
    if (s.output_dir) wrap.appendChild(el('div', { class: 'muted small', text: '轨迹输出目录：' + s.output_dir }));
    result.appendChild(wrap);
  }, 1000);
}

// ---- Journey 旅程（复用内核 Hermes 学习图谱：agent.learning_graph / learning_mutations） ----
export async function renderJourneyPanel(body) {
  body.innerHTML = '';
  const d = await getJSON('/api/features/journey').catch(() => ({ ok: false }));
  body.appendChild(el('div', { class: 'section-title', text: '学习旅程（Hermes 学到的技能与记忆）' }));
  if (!d || !d.ok) { body.appendChild(el('div', { class: 'muted', text: '加载失败' })); return; }
  // 内核不可用 → 诚实降级，绝不编造事件
  if (d.available === false) {
    body.appendChild(el('div', { class: 'tag warn', text: '旅程功能不可用（内核 agent.learning_graph 未加载）' }));
    body.appendChild(el('div', { class: 'muted small', text: (d.error || 'Hermes 内核未安装或当前环境无法读取学习图谱。') }));
    return;
  }
  // 概要统计（来自内核 stats）
  const s = d.stats || {};
  const summary = el('div', { class: 'muted small', style: 'margin:6px 0 12px;' });
  summary.innerHTML = `学到的技能 <b>${s.learned_skills != null ? s.learned_skills : 0}</b> · 记忆节点 <b>${s.memory_nodes != null ? s.memory_nodes : 0}</b> · 其中 Agent 创建 <b>${s.agent_created != null ? s.agent_created : 0}</b> · 曾使用 <b>${s.used != null ? s.used : 0}</b> · 连接边 <b>${(d.edges || []).length}</b>`;
  body.appendChild(summary);
  // 分类簇
  const clusters = d.clusters || [];
  if (clusters.length) {
    const cs = el('div', { style: 'display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;' });
    for (const c of clusters) cs.appendChild(el('span', { class: 'tag', text: `${c.category}: ${c.count}` }));
    body.appendChild(cs);
  }
  // 节点时间线（按 timestamp 倒序，新→旧）
  const nodes = (d.nodes || []).slice().sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));
  if (!nodes.length) {
    body.appendChild(el('div', { class: 'muted', text: '暂无学习记录——多用一段时间 Hermes，你学到的技能和记忆会逐渐在这里形成时间线。（数据来自本机 HERMES_HOME 的 skills/ 与 memories/）' }));
    return;
  }
  for (const n of nodes) {
    const isMem = n.kind === 'memory';
    const icon = isMem ? '✎' : '◆';
    const kindLabel = isMem ? '记忆' : '技能';
    const meta = [kindLabel];
    if (n.category) meta.push('分类·' + n.category);
    if (!isMem && n.useCount) meta.push('使用 ' + n.useCount + ' 次');
    if (n.timestamp) meta.push(relTime(n.timestamp));
    body.appendChild(el('div', { class: 'card-row', style: 'border-left:3px solid var(--accent);margin-bottom:8px;padding-left:12px;' }, [
      el('div', { class: 'cr-main' }, [
        el('div', { class: 'cr-title' }, [el('span', { text: icon + ' ' + (n.label || n.id) })]),
        el('div', { class: 'cr-desc', text: meta.join(' · ') }),
      ]),
      el('div', { class: 'cr-actions' }, [
        el('button', { class: 'btn ghost sm', text: '编辑', onclick: async () => {
          const det = await getJSON('/api/features/journey/node/' + encodeURIComponent(n.id)).catch(() => ({ ok: false }));
          if (!det || !det.ok) { toast('获取内容失败：' + ((det && det.message) || ''), 'err'); return; }
          const next = prompt('编辑「' + (n.label || n.id) + '」内容：', det.content || '');
          if (next === null) return;
          const r = await postJSON('/api/features/journey/edit', { node_id: n.id, content: next }).catch(e => ({ ok: false, message: e.message }));
          if (r && r.ok) { toast('已更新', 'ok'); renderJourneyPanel(body); } else toast('更新失败：' + ((r && r.message) || ''), 'err');
        } }),
        el('button', { class: 'btn ghost sm danger', text: '删除', onclick: async () => {
          if (!confirm('删除「' + (n.label || n.id) + '」？技能将被归档（可恢复），记忆将被移除。')) return;
          const r = await postJSON('/api/features/journey/delete', { node_id: n.id }).catch(e => ({ ok: false, message: e.message }));
          if (r && r.ok) { toast('已删除', 'ok'); renderJourneyPanel(body); } else toast('删除失败：' + ((r && r.message) || ''), 'err');
        } }),
      ]),
    ]));
  }
}

// ---- Backup 备份 ----
export async function renderBackupPanel(body) {
  body.appendChild(el('div', { class: 'section-title', text: '备份/恢复' }));
  body.appendChild(el('div', { class: 'muted small', text: '将整个 Hermes 数据目录打包为 ZIP 归档文件。' }));
  const status = el('div', { style: 'margin-top:12px;' });
  body.appendChild(el('div', { class: 'actions-row' }, [el('button', { class: 'btn primary', text: '创建备份', onclick: async () => {
    status.innerHTML = '<div class="muted">备份中…</div>';
    const r = await postJSON('/api/features/backup').catch(e => ({ ok: false, error: e.message }));
    status.innerHTML = '';
    if (!r || !r.ok) { status.appendChild(el('div', { class: 'muted', text: '备份失败' })); return; }
    status.appendChild(el('div', { class: 'tag ok', text: '备份完成：' + r.name + ' (' + r.size_mb + ' MB)' }));
    loadList();
  } })]));
  const list = el('div', { class: 'card-list' });
  body.appendChild(list);
  async function loadList() {
    const d = await getJSON('/api/features/backup').catch(() => ({ ok: false }));
    list.innerHTML = '';
    if (!d || !d.ok) { list.appendChild(el('div', { class: 'muted', text: '加载失败' })); return; }
    const items = d.items || [];
    if (!items.length) { list.appendChild(el('div', { class: 'muted', text: '暂无备份' })); return; }
    for (const b of items) {
      const row = el('div', { class: 'card-row' });
      row.appendChild(el('div', { class: 'cr-main' }, [el('div', { class: 'cr-title' }, [el('span', { text: b.name }), el('span', { class: 'badge', text: b.size_mb + ' MB' })]), el('div', { class: 'cr-desc', text: b.created })]));
      row.appendChild(el('div', { class: 'cr-actions' }, [
        el('button', { class: 'btn ghost sm', text: '恢复', onclick: async () => {
          if (!confirm('恢复将覆盖当前数据，确定？')) return;
          const r = await postJSON('/api/features/backup/restore', { name: b.name }).catch(e => ({ ok: false, error: e.message }));
          if (r.ok) toast('已恢复' + (r.pre_restore_snapshot ? '（已自动做恢复前快照 ' + r.pre_restore_snapshot + '，可在「状态快照」回滚）' : ''), 'ok'); else toast('恢复失败：' + (r.error || ''), 'err');
        } }),
        el('button', { class: 'btn ghost sm danger', text: '删除', onclick: async () => {
          if (!confirm('删除备份文件？')) return;
          const r = await postJSON('/api/features/backup/delete', { name: b.name }).catch(e => ({ ok: false, error: e.message }));
          if (r.ok) { toast('已删除', 'ok'); loadList(); } else toast('失败', 'err');
        } }),
      ]));
      list.appendChild(row);
    }
  }
  loadList();
}

// ---- State Snapshots 状态快照（Hermes 原生：轻量核心状态快速回滚） ----
export async function renderSnapshotsPanel(body) {
  body.appendChild(el('div', { class: 'section-title', text: '状态快照（Hermes 原生）' }));
  body.appendChild(el('div', { class: 'muted small', text: '对配置 / 会话库 / 看板等核心状态做轻量快速备份，可一键回滚。与「对话快照」(单会话消息) 和「完整备份」(全量 ZIP 归档) 不同。' }));
  const warn = el('div', { class: 'snapshot-warn' }, [
    el('b', { text: '恢复会覆盖当前配置 / 会话 / 看板等核心状态。' }),
    el('span', { text: '建议先关闭应用再恢复；恢复后请重启应用，state.db 等变更才会完全生效。' }),
  ]);
  body.appendChild(warn);

  const status = el('div', { style: 'margin-top:12px;' });
  body.appendChild(el('div', { class: 'actions-row' }, [
    el('input', { class: 'form-input', placeholder: '快照标签（可选）', id: 'snapLabel', style: 'max-width:220px;' }),
    el('button', { class: 'btn primary', text: '创建快照', onclick: async () => {
      const label = (document.getElementById('snapLabel')?.value || '').trim();
      status.innerHTML = '<div class="muted">快照中…</div>';
      const r = await postJSON('/api/features/snapshots', { label }).catch(e => ({ ok: false, error: e.message }));
      status.innerHTML = '';
      if (!r || !r.ok) { status.appendChild(el('div', { class: 'tag err', text: '创建失败：' + (r?.error || '') })); return; }
      status.appendChild(el('div', { class: 'tag ok', text: '快照已创建：' + r.id }));
      loadList();
    } }),
    el('button', { class: 'btn ghost', text: '清理旧快照(保留20)', onclick: async () => {
      if (!confirm('将删除最旧的、超出 20 个的快照，确定？')) return;
      const r = await postJSON('/api/features/snapshots/prune', { keep: 20 }).catch(e => ({ ok: false, error: e.message }));
      if (r && r.ok) toast('已清理 ' + (r.deleted || 0) + ' 个旧快照', 'ok'); else toast('清理失败：' + (r?.error || ''), 'err');
      loadList();
    } }),
  ]));
  body.appendChild(status);

  const list = el('div', { class: 'card-list' });
  body.appendChild(list);
  async function loadList() {
    const d = await getJSON('/api/features/snapshots').catch(() => ({ ok: false }));
    list.innerHTML = '';
    if (!d || !d.ok) { list.appendChild(el('div', { class: 'muted', text: '加载失败：' + (d?.error || '') })); return; }
    if (d.available === false) { list.appendChild(el('div', { class: 'muted', text: '内核快照功能不可用' })); return; }
    const items = d.snapshots || [];
    if (!items.length) { list.appendChild(el('div', { class: 'muted', text: '暂无状态快照（先点「创建快照」）' })); return; }
    for (const s of items) {
      const sz = s.total_size >= 1024 * 1024 ? (s.total_size / 1024 / 1024).toFixed(1) + ' MB'
                : s.total_size >= 1024 ? (s.total_size / 1024).toFixed(0) + ' KB' : s.total_size + ' B';
      const row = el('div', { class: 'card-row' });
      row.appendChild(el('div', { class: 'cr-main' }, [
        el('div', { class: 'cr-title' }, [
          el('span', { text: s.id }),
          s.label ? el('span', { class: 'badge', text: s.label }) : null,
          el('span', { class: 'badge', text: s.file_count + ' 文件' }),
          el('span', { class: 'badge', text: sz }),
        ].filter(Boolean)),
        el('div', { class: 'cr-desc', text: (s.files || []).slice(0, 6).join('  ·  ') + ((s.files || []).length > 6 ? '  …' : '') }),
      ]));
      row.appendChild(el('div', { class: 'cr-actions' }, [
        el('button', { class: 'btn ghost sm', text: '恢复', onclick: async () => {
          if (!confirm('恢复将覆盖当前核心状态（配置/会话/看板等）。\n建议先关闭应用；恢复后请重启应用。\n确定恢复「' + s.id + '」？')) return;
          const r = await postJSON('/api/features/snapshots/restore', { id: s.id }).catch(e => ({ ok: false, error: e.message }));
          if (r && r.ok) toast('已恢复，请重启应用以使 state.db 等变更生效', 'ok'); else toast('恢复失败：' + (r?.error || ''), 'err');
          loadList();
        } }),
      ]));
      list.appendChild(row);
    }
  }
  loadList();
}

// ---- Profiles 配置管理 ----
export async function renderProfilesPanel(body) {
  const d = await getJSON('/api/features/profiles').catch(() => ({ ok: false }));
  if (!d || !d.ok) { body.appendChild(el('div', { class: 'muted', text: '加载失败' })); return; }
  if (d.available === false) {
    body.appendChild(el('div', { class: 'section-title', text: '配置管理（Profiles）' }));
    body.appendChild(el('div', { class: 'muted small', text: d.note || 'Profiles 功能不可用（hermes_cli 未安装）。' }));
    return;
  }
  body.appendChild(el('div', { class: 'section-title', text: '配置管理（Profiles）' }));
  body.appendChild(el('div', { class: 'muted small', text: '每个 Profile 是一个完全独立的 Hermes 实例（独立 HERMES_HOME）。default 即当前实例本身。' }));
  const items = d.items || []; const current = d.current || 'default';

  // 新建（可选克隆自已有 Profile）
  const nn = el('input', { class: 'form-input', placeholder: 'Profile 名称（小写字母/数字/-/_）' });
  const cloneSel = el('select', { class: 'form-input' });
  cloneSel.appendChild(el('option', { value: '', text: '（不克隆，空白 Profile）' }));
  for (const p of items) {
    if (p.name !== 'default') cloneSel.appendChild(el('option', { value: p.name, text: '克隆自：' + p.name }));
  }
  body.appendChild(el('div', { class: 'field' }, [
    el('label', { text: '新建 Profile' }), nn, cloneSel,
    el('button', { class: 'btn primary', text: '创建', onclick: async () => {
      const name = nn.value.trim();
      if (!name) { toast('请输入名称', 'err'); return; }
      const r = await postJSON('/api/features/profiles', { name, clone_from: cloneSel.value || null })
        .catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast('已创建：' + r.name + (r.note ? '（' + r.note + '）' : ''), 'ok'); renderProfilesPanel(body); }
      else toast(r.error || '创建失败', 'err');
    } })
  ]));

  // 导入 Profile 归档
  const ip = el('input', { class: 'form-input', placeholder: '归档路径（tar.gz）' });
  const iname = el('input', { class: 'form-input', placeholder: '导入后的名称（留空=自动推断）' });
  body.appendChild(el('div', { class: 'field' }, [
    el('label', { text: '导入 Profile' }), ip, iname,
    el('button', { class: 'btn ghost', text: '导入', onclick: async () => {
      const ap = ip.value.trim();
      if (!ap) { toast('请输入归档路径', 'err'); return; }
      const r = await postJSON('/api/features/profiles/import', { archive_path: ap, name: iname.value.trim() }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) { toast('已导入：' + (r.path || ''), 'ok'); renderProfilesPanel(body); }
      else toast('失败：' + (r.error || ''), 'err');
    } })
  ]));

  const list = el('div', { class: 'card-list' });
  for (const p of items) {
    const isCurrent = p.name === current;
    const isDefault = !!p.is_default;
    const meta = [];
    if (p.model) meta.push('模型 ' + (p.provider ? p.provider + '/' : '') + p.model);
    if (p.skill_count) meta.push(p.skill_count + ' 技能');
    if (p.gateway_running) meta.push('网关运行中');
    if (p.description) meta.push(p.description);
    const row = el('div', { class: 'card-row' });
    row.appendChild(el('div', { class: 'cr-main' }, [
      el('div', { class: 'cr-title' }, [
        el('span', { text: p.name }),
        isCurrent ? el('span', { class: 'badge on', text: '当前' }) : null,
        isDefault ? el('span', { class: 'badge', text: 'default' }) : null,
      ]),
      el('div', { class: 'cr-desc', text: [p.path, meta.join(' · ')].filter(Boolean).join(' · ') }),
    ]));
    row.appendChild(el('div', { class: 'cr-actions' }, [
      !isCurrent ? el('button', { class: 'btn ghost sm', text: '切换', onclick: async () => {
        const r = await postJSON('/api/features/profiles/switch', { name: p.name }).catch(e => ({ ok: false, error: e.message }));
        if (r.ok) { toast('已切换：' + p.name + '（下次启动生效）', 'ok'); renderProfilesPanel(body); }
        else toast('切换失败：' + (r.error || ''), 'err');
      } }) : null,
      !isCurrent && !isDefault ? el('button', { class: 'btn ghost sm danger', text: '删除', onclick: async () => {
        if (!confirm('删除 Profile「' + p.name + '」？将停止其网关与后端进程并移除目录。')) return;
        const r = await postJSON('/api/features/profiles/delete', { name: p.name }).catch(e => ({ ok: false, error: e.message }));
        if (r.ok) { toast('已删除：' + p.name, 'ok'); renderProfilesPanel(body); }
        else toast('失败：' + (r.error || ''), 'err');
      } }) : null,
      el('button', { class: 'btn ghost sm', text: '导出', onclick: async () => {
        const out = prompt('导出归档路径（留空=<name>.tar.gz）', p.name + '.tar.gz');
        if (out === null) return;
        const finalPath = out.trim() || (p.name + '.tar.gz');
        const r = await postJSON('/api/features/profiles/export', { name: p.name, output_path: finalPath }).catch(e => ({ ok: false, error: e.message }));
        if (r.ok) { toast('已导出：' + (r.path || finalPath), 'ok'); }
        else toast('导出失败：' + (r.error || ''), 'err');
      } }),
      !isDefault ? el('button', { class: 'btn ghost sm', text: '重命名', onclick: async () => {
        const nn = prompt('重命名「' + p.name + '」为新名称：', p.name);
        if (!nn || nn === p.name) return;
        const r = await postJSON('/api/features/profiles/rename', { old_name: p.name, new_name: nn }).catch(e => ({ ok: false, error: e.message }));
        if (r.ok) { toast('已重命名：' + r.old + ' → ' + r.new, 'ok'); renderProfilesPanel(body); }
        else toast('失败：' + (r.error || ''), 'err');
      } }) : null,
    ]));
    list.appendChild(row);
  }
  body.appendChild(list);
}

// ---- Curator 策展（复用内核 Hermes Curator：agent.curator + tools.skill_usage + agent.curator_backup） ----
export async function renderCuratorPanel(body) {
  const d = await getJSON('/api/features/curator').catch(() => ({ ok: false }));
  if (!d || !d.ok) { body.appendChild(el('div', { class: 'muted', text: '加载失败：' + ((d && d.error) || '') })); return; }
  if (!d.available) {
    body.appendChild(el('div', { class: 'section-title', text: '内容策展（Hermes 原生）' }));
    body.appendChild(el('div', { class: 'muted', text: '内核 Curator 模块不可用：' + (d.error || '') }));
    return;
  }
  body.appendChild(el('div', { class: 'section-title', text: '内容策展（Hermes 原生）' }));
  body.appendChild(el('div', { class: 'muted small', text: 'Curator 是 Hermes 对「Agent 创建的技能」的后台维护通道：按查看/使用/打补丁频率，把长期不用的技能从 活跃→陈旧→归档 流转；你可手动归档/恢复/固定、批量清理空闲技能，并可对技能树做快照随时回滚。' }));

  const tag = (text, cls) => el('span', { class: 'tag ' + (cls || ''), text });
  const rerender = () => { body.innerHTML = ''; renderCuratorPanel(body); };
  const act = async (url, payload, okMsg) => {
    const r = await postJSON(url, payload).catch(e => ({ ok: false, error: e.message }));
    if (r.ok) toast(okMsg || '已执行', 'ok'); else toast('失败：' + (r.error || ''), 'err');
    rerender();
  };

  // 状态概览
  const stBox = el('div', { class: 'card-row' }, [
    el('div', { class: 'cr-main' }, [
      el('div', { class: 'cr-title' }, [
        tag(d.enabled ? '已启用' : '未启用', d.enabled ? 'ok' : 'warn'),
        tag(d.paused ? '已暂停' : '运行中', d.paused ? 'warn' : 'ok'),
      ]),
      el('div', { class: 'cr-desc', text:
        `间隔 ${d.interval_hours}h · 陈旧阈值 ${d.stale_after_days}天 · 归档阈值 ${d.archive_after_days}天 · ` +
        `合并(LLM): ${d.consolidate ? '开' : '关'} · 清理内置: ${d.prune_builtins ? '开' : '关'} · ` +
        `上次运行: ${d.last_run_at ? relTime(d.last_run_at) : '从未'} · 运行次数: ${d.run_count || 0}` }),
    ]),
  ]);
  body.appendChild(stBox);

  // 启用/暂停 复选框
  const enabledCb = el('input', { type: 'checkbox' });
  enabledCb.checked = d.enabled && !d.paused;
  body.appendChild(el('div', { class: 'field-inline' }, [enabledCb, el('span', { text: '启用自动策展（取消勾选 = 暂停自动整理；使用记录仍照常追踪）' })]));
  body.appendChild(el('div', { class: 'actions-row' }, [el('button', { class: 'btn primary', text: '保存', onclick: async () => {
    await act('/api/features/curator/toggle', { enabled: enabledCb.checked }, '已保存');
  } })]));

  // 运行自动整理（确定性、无 LLM、不烧 token）
  body.appendChild(el('div', { class: 'actions-row' }, [el('button', { class: 'btn', text: '运行自动整理(active→stale→archived)', onclick: async () => {
    if (!confirm('将按阈值把长期不用的技能流转为 陈旧/归档（确定性、不烧 token），归档可在下方恢复。继续？')) return;
    const r = await postJSON('/api/features/curator/apply', { dry_run: false }).catch(e => ({ ok: false, error: e.message }));
    if (r.ok) toast('自动整理完成：' + JSON.stringify(r.counts || {}), 'ok'); else toast('失败：' + (r.error || ''), 'err');
    rerender();
  } })]));

  // agent 创建技能概览
  const bs = d.by_state || {};
  body.appendChild(el('div', { class: 'section-title', text: `Agent 创建的技能（${d.agent_created_total}）活跃 ${bs.active || 0} / 陈旧 ${bs.stale || 0} / 归档 ${bs.archived || 0}` }));
  if ((d.pinned || []).length) {
    body.appendChild(el('div', { class: 'muted small', text: '已固定(不参与自动流转)：' + (d.pinned || []).join('、') }));
  }

  // 使用遥测列表
  body.appendChild(el('div', { class: 'section-title', text: '技能使用遥测（全部技能）' }));
  const list = el('div', { class: 'card-list' });
  const usage = (d.usage || []).filter(r => r.provenance === 'agent');  // 重点展示 agent 创建
  const others = (d.usage || []).filter(r => r.provenance !== 'agent');
  const renderRow = (r) => {
    const isArchived = r.state === 'archived';
    const stateCls = r.state === 'active' ? 'ok' : (r.state === 'stale' ? 'warn' : 'err');
    const tags = [tag(r.state || 'active', stateCls)];
    if (r.pinned) tags.push(tag('固定', 'warn'));
    const title = el('div', { class: 'cr-title' }, [el('span', { text: r.name }), ...tags]);
    const desc = el('div', { class: 'cr-desc', text:
      `来源:${r.provenance} · 使用 ${r.use_count || 0} · 查看 ${r.view_count || 0} · 打补丁 ${r.patch_count || 0} · ` +
      `最近活动: ${r.last_activity_at ? relTime(r.last_activity_at) : '从未'}` });
    const actions = el('div', { class: 'actions-row' });
    if (isArchived) {
      actions.appendChild(el('button', { class: 'btn small', text: '恢复', onclick: async () => {
        await act('/api/features/curator/restore', { name: r.name }, '已恢复：' + r.name);
      } }));
    } else {
      actions.appendChild(el('button', { class: 'btn small', text: r.pinned ? '取消固定' : '固定', onclick: async () => {
        await act('/api/features/curator/pin', { name: r.name, pinned: !r.pinned }, r.pinned ? '已取消固定' : '已固定');
      } }));
      actions.appendChild(el('button', { class: 'btn small', text: '归档', onclick: async () => {
        if (!confirm('归档「' + r.name + '」（移到 .archive/，可在下方或归档列表恢复）？')) return;
        await act('/api/features/curator/archive', { name: r.name }, '已归档：' + r.name);
      } }));
    }
    return el('div', { class: 'card-row' }, [el('div', { class: 'cr-main' }, [title, desc]), actions]);
  };
  if (usage.length) usage.forEach(r => list.appendChild(renderRow(r)));
  else list.appendChild(el('div', { class: 'muted small', text: '暂无 agent 创建的技能。Agent 在对话中创建的技能会出现在这里，供策展管理。' }));
  body.appendChild(list);
  if (others.length) {
    body.appendChild(el('div', { class: 'muted small', style: 'margin-top:6px;', text: `另有 ${others.length} 个内置/Hub 技能（不在策展范围内，仅展示）。` }));
  }

  // 归档列表（可恢复）
  const archived = d.archived || [];
  body.appendChild(el('div', { class: 'section-title', text: `已归档（可恢复）· ${archived.length}` }));
  if (archived.length) {
    const al = el('div', { class: 'card-list' });
    archived.forEach(name => al.appendChild(el('div', { class: 'card-row' }, [
      el('div', { class: 'cr-main' }, [el('div', { class: 'cr-title' }, [el('span', { text: name }), tag('归档', 'err')])]),
      el('div', { class: 'actions-row' }, [el('button', { class: 'btn small', text: '恢复', onclick: async () => {
        await act('/api/features/curator/restore', { name }, '已恢复：' + name);
      } })]),
    ])));
    body.appendChild(al);
  } else {
    body.appendChild(el('div', { class: 'muted small', text: '无归档技能。' }));
  }

  // 批量清理空闲技能
  body.appendChild(el('div', { class: 'section-title', text: '批量清理空闲技能' }));
  const daysInp = el('input', { class: 'form-input', type: 'number', value: 90, min: 1, style: 'width:90px;' });
  body.appendChild(el('div', { class: 'field-inline' }, [el('label', { text: '空闲 ≥ ' }), daysInp, el('span', { text: ' 天（agent 创建、未固定、未归档）' })]));
  body.appendChild(el('div', { class: 'actions-row' }, [
    el('button', { class: 'btn small', text: '预览', onclick: async () => {
      const r = await postJSON('/api/features/curator/prune', { days: Number(daysInp.value) || 90, dry_run: true }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) toast('将归档 ' + (r.count || 0) + ' 个：' + (r.candidates || []).map(c => c.name).join('、'), 'ok');
      else toast('失败：' + (r.error || ''), 'err');
    } }),
    el('button', { class: 'btn small', text: '归档选中', onclick: async () => {
      if (!confirm('确认归档上述空闲技能？可在归档列表恢复。')) return;
      const r = await postJSON('/api/features/curator/prune', { days: Number(daysInp.value) || 90, dry_run: false }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) toast('已归档 ' + (r.archived || 0) + '/' + (r.total || 0), 'ok'); else toast('失败：' + (r.error || ''), 'err');
      rerender();
    } }),
  ]));

  // 技能树快照 / 回滚
  body.appendChild(el('div', { class: 'section-title', text: '技能树快照（回滚安全网）' }));
  body.appendChild(el('div', { class: 'actions-row' }, [
    el('button', { class: 'btn small', text: '创建快照', onclick: async () => {
      const r = await postJSON('/api/features/curator/backup', { reason: 'manual' }).catch(e => ({ ok: false, error: e.message }));
      if (r.ok) toast('已创建快照：' + (r.name || ''), 'ok'); else toast('失败：' + (r.error || ''), 'err');
    } }),
    el('button', { class: 'btn small', text: '列出快照', onclick: async () => {
      const r = await getJSON('/api/features/curator/backups').catch(e => ({ ok: false, error: e.message }));
      if (!r || !r.ok) { toast('失败：' + ((r && r.error) || ''), 'err'); return; }
      const rows = r.backups || [];
      if (!rows.length) { toast('暂无快照', 'ok'); return; }
      const bl = el('div', { class: 'card-list' });
      rows.forEach(b => bl.appendChild(el('div', { class: 'card-row' }, [
        el('div', { class: 'cr-main' }, [el('div', { class: 'cr-title', text: (b.name || b.id || '?') }),
          el('div', { class: 'cr-desc', text: `原因:${(b.reason || '?')} · 技能文件:${(b.skill_files != null ? b.skill_files : '?')} · 创建:${(b.created_at || '?')}` })]),
        el('div', { class: 'actions-row' }, [el('button', { class: 'btn small', text: '回滚', onclick: async () => {
          if (!confirm('回滚将用该快照替换当前技能树（回滚前会自动再拍一张安全快照）。继续？')) return;
          const rr = await postJSON('/api/features/curator/rollback', { backup_id: b.id || b.name, yes: true }).catch(e => ({ ok: false, error: e.message }));
          if (rr.ok) toast('已回滚：' + (rr.message || ''), 'ok'); else toast('失败：' + (rr.error || ''), 'err');
          rerender();
        } })]),
      ])));
      body.appendChild(el('div', { class: 'section-title', text: `快照列表（${rows.length}）` }));
      body.appendChild(bl);
    } }),
  ]));
}

// ---- Routing 提供者路由 ----
export async function renderRoutingPanel(body) {
  body.innerHTML = '';
  const d = await getJSON('/api/features/routing').catch(() => ({ ok: false }));
  if (!d) { body.appendChild(el('div', { class: 'muted', text: '加载失败' })); return; }
  if (d.available === false) {
    body.appendChild(el('div', { class: 'section-title', text: '提供者路由' }));
    body.appendChild(el('div', { class: 'muted small', text: d.error || 'Provider Routing 功能当前不可用（内核 config 模块缺失）。' }));
    return;
  }
  if (!d.ok) { body.appendChild(el('div', { class: 'muted', text: '加载失败：' + (d.error || '') })); return; }
  body.appendChild(el('div', { class: 'section-title', text: '提供者路由（Provider Routing）' }));
  body.appendChild(el('div', { class: 'muted small', text: 'OpenRouter 专属：控制请求如何在多个 provider 之间路由。其它 provider 下这些设置无作用。' }));
  if (!d.is_openrouter) {
    body.appendChild(el('div', { class: 'muted small warn', style: 'margin-top:6px;', text: '当前 provider 为「' + (d.provider || '未知') + '」而非 openrouter —— 下方设置当前不会生效。' }));
  }
  const sortSel = el('select', { class: 'form-input' });
  for (const s of ['price', 'throughput', 'latency']) sortSel.appendChild(el('option', { value: s, text: s, selected: d.sort === s }));
  body.appendChild(el('div', { class: 'field' }, [el('label', { text: '排序方式 (sort)' }), sortSel]));
  const onlyInp = el('input', { class: 'form-input', placeholder: '允许的 provider（逗号分隔，如 anthropic,google）', value: (d.only || []).join(', ') });
  body.appendChild(el('div', { class: 'field' }, [el('label', { text: '仅用 (only)' }), onlyInp]));
  const ignoreInp = el('input', { class: 'form-input', placeholder: '排除的 provider（逗号分隔）', value: (d.ignore || []).join(', ') });
  body.appendChild(el('div', { class: 'field' }, [el('label', { text: '排除 (ignore)' }), ignoreInp]));
  const orderInp = el('input', { class: 'form-input', placeholder: '优先级顺序（逗号分隔）', value: (d.order || []).join(', ') });
  body.appendChild(el('div', { class: 'field' }, [el('label', { text: '顺序 (order)' }), orderInp]));
  const reqCb = el('input', { type: 'checkbox', checked: !!d.require_parameters });
  body.appendChild(el('div', { class: 'field-inline' }, [reqCb, el('span', { text: '仅用支持全部请求参数的 provider (require_parameters)' })]));
  const dcSel = el('select', { class: 'form-input' });
  for (const [v, t] of [['', '（默认）'], ['allow', 'allow'], ['deny', 'deny']]) dcSel.appendChild(el('option', { value: v, text: t, selected: (d.data_collection || '') === v }));
  body.appendChild(el('div', { class: 'field' }, [el('label', { text: '数据收集 (data_collection)' }), dcSel]));
  const mcsInp = el('input', { class: 'form-input', type: 'number', min: '0', max: '1', step: '0.05', placeholder: '0.0–1.0（默认 0.65，仅 openrouter/pareto-code）', value: (d.min_coding_score == null ? '' : String(d.min_coding_score)) });
  body.appendChild(el('div', { class: 'field' }, [el('label', { text: 'Pareto Code 编码分 (min_coding_score)' }), mcsInp]));
  body.appendChild(el('div', { class: 'muted small', text: '快捷方式：模型名追加 :nitro（按吞吐）/ :floor（按价格）可快速切换 sort。' }));
  body.appendChild(el('div', { class: 'actions-row' }, [el('button', { class: 'btn primary', text: '保存', onclick: async () => {
    const r = await postJSON('/api/features/routing', {
      sort: sortSel.value,
      only: onlyInp.value.split(',').map(s => s.trim()).filter(Boolean),
      ignore: ignoreInp.value.split(',').map(s => s.trim()).filter(Boolean),
      order: orderInp.value.split(',').map(s => s.trim()).filter(Boolean),
      require_parameters: reqCb.checked,
      data_collection: dcSel.value || null,
      min_coding_score: mcsInp.value.trim() === '' ? null : mcsInp.value.trim(),
    }).catch(e => ({ ok: false, error: e.message }));
    if (r && r.ok) { toast('已保存', 'ok'); renderRoutingPanel(body); }
    else toast('保存失败：' + (r && r.error || ''), 'err');
  } })]));
}

