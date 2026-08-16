## Batch Processing 批量处理 — 示例落地清单（from examples/01-hermes-desktop，实际改动）

> 本文件从 `references/08-capability-integration.md#batch` 抽出：该旗舰示例对 Batch Processing 的实际落地（后端薄封装 `hermes_features.py` / 路由 `routes/features.py` / 前端 `renderBatchPanel`）。属示例耦合内容，不进入技能核心骨干（通用内核范式与反模式红线见 `references/08-capability-integration.md#batch`）。

---

## §2 桌面集成（薄封装，与全家桶同源范式）

### 2.1 后端 `hermes_features.py`

```python
_BATCH_RUNS: dict = {}          # 内存 run 注册表（桌面单进程）
_BATCH_LOCK = threading.Lock()

def _batch_runner_mod():        # 惰性导入内核，失败 → None
    try: import batch_runner as m; return m
    except Exception: return None

def batch_list_distributions() -> dict:       # GET /api/features/batch/distributions
    mod = _batch_runner_mod()
    if mod is None: return {"ok":True,"available":False,"items":[],"error":"batch_runner 模块不可用"}
    try:
        dists = mod.list_distributions()
        items = [{"key":k,"description":(v.get("description") if isinstance(v,dict) else ""),
                  "toolsets":(list(v.get("toolsets",{}).keys()) if isinstance(v,dict) else [])}
                 for k,v in dists.items()]
        return {"ok":True,"available":True,"items":items}
    except Exception as e:
        return {"ok":True,"available":False,"items":[],"error":f"{type(e).__name__}: {e}"}

def batch_run(rows: list, opts: dict | None = None) -> dict:   # POST /api/features/batch/run
    # rows 归一化为 [{"prompt":...}]；opts: run_name/model/base_url/api_key/max_iterations/
    #   distribution/reasoning_effort/max_tokens/verbose/providers_* ...
    # 默认 model=inclusionai/ling-3.0-flash:free（遵循项目 OpenRouter 铁律）、distribution=safe
    # 启动 daemon 线程跑 _batch_run_worker，立即返回 run_id

def batch_status(run_id: str) -> dict:          # GET /api/features/batch/status/{run_id}
    # 轮询：run_name/status(running|done|error)/total/processed/results[]/statistics/output_dir/error
```

`_batch_run_worker`（后台线程，串行）：

- 对每条 `entry` 调 `mod._process_single_prompt(idx, entry, 0, config)`（**真实内核执行器**）。
- 成功且含推理 → 归一化 `tool_stats`/`tool_error_counts`（复用内核 `_normalize_tool_stats`/`_normalize_tool_error_counts`）→ 写 `batch_0.jsonl` + `trajectories.jsonl` → 累积统计。
- 无推理 → `discarded`；失败 → `failed`；均不写轨迹（`has_any_reasoning` 过滤忠实于内核质量过滤）。
- 结束写 `checkpoint.json` + `statistics.json`，置 `status="done"`。
- 整体 try/except → `status="error"` + `error`（**绝不静默崩溃**）。

### 2.2 路由 `routes/features.py`

```python
@app.get('/api/features/batch/distributions')
def api_batch_distributions(): return hf.batch_list_distributions()

@app.post('/api/features/batch/run')
async def api_batch_run(req):
    b = await req.json(); return hf.batch_run(b.get('rows', []), b.get('opts') or {})

@app.get('/api/features/batch/status/{run_id}')
def api_batch_status(run_id: str): return hf.batch_status(run_id)
```

非阻塞：`POST /run` 立即返回 `run_id`；前端 `GET /status/{run_id}` 每 1s 轮询进度。

### 2.3 前端 `other.js` `renderBatchPanel`

- **诚实说明**：标题「批量处理（Hermes Batch Runner）」，副文案明确「生成 ShareGPT 训练/评测轨迹，桌面端单进程串行、每条真实调模型」。
- **可用性检查** → `available:false` 降级（`tag warn`，不渲染表单）。
- **输入模式**：
  - `JSONL 数据集`：每行 `{"prompt": "..."}`。
  - `模板 + 多输入`：`{input}` 模板 + N 条输入 → **展开为数据集**（诚实映射，把「模板+N输入」说明成「便捷构造 prompt 的方式」，底层单位仍是真实 `{prompt}`）。
- **配置**：`run_name` / `distribution`（下拉，默认 `safe`）/ `model`（默认 OpenRouter 免费）/ `base_url`（默认 OpenRouter）/ `max_iterations`（默认 10）/ `reasoning_effort`。
- **运行 + 轮询**：提交 → 拿到 `run_id` → 轮询渲染「进度 processed/total + 终态分项（状态徽章 / 输出文本 / api_calls / tool_stats / error）+ 统计（总数/失败/无推理丢弃/耗时）+ 轨迹目录」。
- 复用既有 `el`/`toast`/`getJSON`/`postJSON`（来自 `dom.js`/`api.js`）。新增 CSS 工具类 `.grid-2`/`.small`/`.batch-prog`。
