# BUGS

## 已修复

以下条目均已合并到 master：

| 修复时间 | 描述 | commit |
|---|---|---|
| 2026-05-02 | Phase 1: WS 协议 data 包装缺失（trace/ask/plans_ready/execution_preview/execution_result/error 全部补 data wrapper） | e5b1692 |
| 2026-05-02 | Phase 1: error 消息缺 recoverable 字段 | e5b1692 |
| 2026-05-02 | Phase 1: user_reply 和 plan_confirmed 从 payload 而非顶层取字段 | e5b1692 |
| 2026-05-02 | mock 数据城市名不一致（"Shanghai" → "上海"） | e5b1692 |
| 2026-05-02 | 死代码 _build_mock_execution_results 已删除 | e5b1692 |
| 2026-05-06 | IntentParserNode 追问通过 trace 传递（隐式协议）→ 改为 pending_clarification 显式字段 | 本次 |
| 2026-05-06 | Orchestrator session._location_raw 非类型化 hack → location 写入 PlanningState.origin_location | 本次 |
| 2026-05-06 | RetrievalNode 同步 IO 改为 run_in_executor 实现真正并发 | 本次 |
| 2026-05-02 | Phase 1: TraceStatus 枚举（done/error）前后端已对齐 | 早期 |
| 2026-05-02 | Phase 1: onExecutionPreview 触发 execution_confirm 状态转换 | 早期 |
| 2026-05-02 | IntentParserNode: LLMError 未捕获 | 早期 |
| 2026-05-02 | IntentParserNode: _detect_scenario 阈值 >= 3 改为 >= 4 | 早期 |
| 2026-05-02 | IntentParserNode: _call_llm 改 run_in_executor 避免阻塞事件循环 | 早期 |
| 2026-05-02 | RetrievalNode: parents[4] 改 parents[3] | 早期 |
| 2026-05-02 | RetrievalResult: 增加 rejected_by_business_hours 字段 | 早期 |
| 2026-05-02 | PlanningNode: verifier_rejection_reason AttributeError（补 @property） | 早期 |
| 2026-05-02 | PlanningNode: None 时间窗口导致 prompt 出现 "None–None" | 早期 |
| 2026-05-02 | VerifierNode: 校验失败方案不从 candidate_plans 过滤 | 早期 |
| 2026-05-02 | PlanningState: 缺失 verifier_rejection_reasons 字段 | 早期 |

---

## 待处理


### [LOW] wsClient 在 SSR 环境下实例化 WebSocket

**位置**: `apps/web/src/lib/ws-client.ts`

**描述**: `wsClient` 是模块级单例，在 SSR 阶段 import 可能触发 `ReferenceError: WebSocket is not defined`。当前 connect() 只在 useEffect 里调用，暂时安全。

**建议**: 加 `typeof window !== 'undefined'` guard 或 lazy 初始化。

---



### [LOW] MAX_PLAN_REVISION 未定义在 types.py

**位置**: `services/agent/state/types.py`，`plan_revision_count` 字段；`orchestrator.py` 中定义为 `MAX_PLAN_REVISION = 2`

**描述**: 常量只在 orchestrator 里，若其他地方（节点、测试）也需要该值，存在重复定义风险。

**建议**: 迁移到 `state/types.py` 或单独 `constants.py`。

---

### [LOW] ExecutionResult 缺少 action_id / action_title

**位置**: `services/agent/nodes/execution_node.py`，`agent/state/types.py`

**描述**: `ExecutionResult` 只有 `action_type`、`success`、`detail`，缺少 `action_id`。前端 `execution_result` 消息无法将执行结果精确映射回具体动作，只能按 action_type 做模糊匹配。

**建议**: `ExecutionResult` 增加 `action_id: str | None` 可选字段，ExecutionNode 赋值。

---

### [LOW] VerifierNode 双阶段均 reject 时 plan_revision_count +2

**位置**: `services/agent/nodes/verifier_node.py`，`run()` 方法

**描述**: 同一轮 VerifierNode 运行中，若硬约束阶段和 LLM Critic 阶段各自都有方案被 reject，`plan_revision_count` 会被累加两次（各阶段各加 1）。Orchestrator 的回环判断基于 `plan_revision_count` 的增量，+2 会导致跳过一次重试机会（MAX_PLAN_REVISION=2 的情况下实际只重试 1 次而非 2 次）。

**发现时间**: 2026-05-07（PR review）

---

### [LOW] _filter_rejection_reason_for_strategy 与 verifier_rejection_reason 格式隐式耦合

**位置**: `services/agent/nodes/planning_node.py`，`_filter_rejection_reason_for_strategy()`

**描述**: 该方法通过字符串匹配 `plan_s{N}_` 前缀来过滤 rejection reason，依赖 `PlanningState.verifier_rejection_reason` property 的格式化输出（`方案 plan_sN_M（...）：...`）。如果 property 的文本格式发生变更，过滤会静默失效——不报错，只是所有策略都拿不到 rejection reason，重试 prompt 退化为无改进建议状态。

**建议**: 在 `_filter_rejection_reason_for_strategy` 加注释说明依赖格式；或将格式化改为结构化数据（每条 rejection 以 dict 形式传递，不依赖字符串解析）。

**发现时间**: 2026-05-07（PR review）

---

### [MEDIUM] PlanningNode 可能选咖啡厅/甜品店作为用餐地点

**位置**: `services/agent/nodes/planning_node.py`，`_SYSTEM_PROMPT` 用餐规则（第 8 条）；`services/tools/poi/amap_searcher.py`，`search_with_strategy()`

**描述**: 高德 `050000`（餐饮服务）包含所有餐饮场所——正餐、咖啡厅、甜品店、茶馆等。AMap 搜索将所有 `050000` 结果标记为 `category="restaurant"`，不区分正餐和非正餐。PlanningNode 提示只要求"需要用餐时包含 type=meal 步骤"，未指示 LLM 优先正餐（中餐、日料、火锅等）并避免咖啡厅/甜品店。导致 LLM 可能选中星巴克（subcategory=咖啡厅）作为用餐地点。

**复现**: 策略路径检索到星巴克后，LLM 生成的计划中出现"在星巴克享用咖啡简餐"作为 type=meal 步骤。

**建议**:
1. PlanningNode `_SYSTEM_PROMPT` 第 8 条用餐规则增加：type=meal 优先选中餐、日料、火锅等正餐 subcategory，避免咖啡厅、甜品店、冷饮店、茶馆
2. 或 `AmapSearcher.search_with_strategy()` 检索时过滤掉 subcategory 为咖啡厅/甜品店/冷饮店/茶艺馆的 POI

**发现时间**: 2026-05-10

---
### [LOW] ExecutionConfirmPanel 确认按钮 disabled 逻辑有歧义

**位置**: `apps/web/src/components/planner/ExecutionConfirmPanel.tsx`

**描述**: `allChecklistChecked` 要求 `checkedItems.length >= checklistItems.length && checkedItems.includes('safety')`，但 `safety` 不在 `checklistItems` 数组里，条件不够直观（实际等价于"5 项确认 + safety"共 6 个元素）。
