# 17 · 调试纪律（Debug）

> 定位：**失败之后的处理闭环**。`07-quality-gates.md` 与 `09-integration-e2e.md` 回答「行为对不对」，Debug 回答「失败为什么发生、怎么修好」。
> 与静态关卡（`quality_check.py` 六段：py_compile / 技能结构 / 离线桥接 / 签名漂移 / 网页回归 / 文档链接）、
> 动态验证（离线桥接 / 回调触发 / 冒烟 / E2E / LLM Judge / 离线回放）互补：任何 Check 或 Test 失败后进入本节闭环。
> 排障知识沉淀库：`../docs/troubleshooting.md`（执行中问题 → 现象/本质/解决，优先沉淀于此）。

---

## 调试总纲：复现 → 定位 → 修复 → 回归 → 沉淀

任何失败按固定闭环处理，**绝不无测试修 bug、绝不「改了没验证」**：

1. **复现**：先写能稳定失败的复现（复现测试 / 最小用例 / 离线 mock），确认失败原因正确（不是凭证/网络/环境错）。
2. **定位**：用日志、`runtime_ready()` 自检、回调事件流、二分法缩小范围，找出根因。
3. **修复**：最小改动修复，不过度设计。
4. **回归**：重跑 `quality_check.py`（六段已含签名漂移与网页回归，不必单独再跑 `check_api_signature.py` / `smoke_test_web.py`），
   交付前再跑 `release_gate.py`，全绿才算无回归。
5. **沉淀**：将现象/本质/解法写入 `../docs/troubleshooting.md`，避免重复踩坑。

---

## Prove-It 模式（Bug 修复必做）

收到 bug → **先写复现测试（必失败）→ 实现修复 → 测试通过 → 跑全量防回归**。**绝不无测试修 bug。**

```
bug 报告
  ↓
写复现测试（应当 FAIL，如回调未触发 / 断言失败）
  ↓
测试 FAIL（确认 bug 存在）
  ↓
实现修复（最小改动）
  ↓
测试 PASS（证明修好）
  ↓
跑全量 release_gate.py（无回归）
```

> Hermes 特化：很多失败是「静默降级」——回调没被触发、事件没发出、工具没被调用但不报错。复现测试必须断言**行为证据**
> （`stream_callback` 被调 ≥1 次、`action` 与 `action_result` 配对出现、宿主领域行为触发），不能只断言「不崩溃」。
> 断言清单见 `09-integration-e2e.md` §4。

---

## Flaky 重复跑纪律

为让「全绿」结论可信，关键集成测试可加重复跑，用来排除偶发抖动：

- 安装 `pytest-rerunfailures`（提供 `@pytest.mark.flaky`）或 `pytest-repeat`（提供 `--count`）：
  加在**你自己工程**的 dev 依赖里；示例的 `Agent系统/` 是外部底座，改它的依赖声明会破坏底座零差异（`18` §7 `agent_zero_diff`）；
- 关键测试加 `@pytest.mark.flaky(reruns=3)`（网络 / LLM 调用 / 文件类易抖动项）；
- 重复跑**只能排除偶发的环境抖动**，不能掩盖真实失败；若某测试频繁 flaky，必须修根因（竞态 / 未隔离状态 / 网络超时 / 版本漂移）。
- 确定性测试优先走**离线 mock 回放**（`test_bridge` + mock，见 `09` §9），从源头消除网络 flaky。

---

## 改后干净复测回路（防「改了但没生效」假象）

> 典型踩坑：改了 `run_agent.py` 或示例，但重跑时命中了**旧进程 / 旧 `.pyc` / 已缓存的 hermes-agent 版本**，反复误判「修改无效」。

任何「改代码后复测」的流程，必须先确保**真的加载了新代码**：

1. `netstat -ano | findstr :8642`（或 `lsof -i:8642`）确认无旧网关在跑；有则按路线处理（进程内形态本就不该监听 8642）；
2. `find . -name __pycache__ -exec rm -rf {} +` 清字节码缓存；
3. 确认装的 `hermes-agent` 版本与 `runtime_ready()` 期望一致（漂移用 `check_api_signature.py` 看）；升级后先跑 `track_upstream.py`；
4. 复测前先跑 `runtime_ready()` 自检 + 最小对话，确认 `stream_callback` 真的被触发，再继续。

---

## 排障沉淀

- 任何「现象 → 根因 → 解法」一旦确认，立即追加到 `../docs/troubleshooting.md`，避免重复踩坑；
- 沉淀格式：现象（可复现症状）/ 本质（根因）/ 解决（最小修复 + 验证）；
- 涉及 API 签名/版本漂移的坑，同步更新 `api-baseline.json` 与 `07-quality-gates.md` §2。
