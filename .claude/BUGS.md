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


### [LOW] WorkbenchContext canTransitionTo 非响应式

**位置**: `apps/web/src/features/planner/contexts/WorkbenchContext.tsx`

**描述**: `canTransitionTo` 用 ref 实现，不会触发 consumer re-render。当前消费方均在事件处理函数里调用，无影响。若未来有响应式需求会出问题。

---

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

### [WARNING] OpenAIClient 超时异常在 Python < 3.11 漏捕获

**位置**: `services/llm/providers/openai_client.py`

**描述**: 捕获内置 `TimeoutError`，但 Python < 3.11 `socket.timeout` 不继承自内置 `TimeoutError`（只继承自 `OSError`）。超时会被 `except OSError` 捕获，错误信息为"网络连接异常"而非"请求超时"。功能不受影响（重试逻辑仍正常），仅错误日志不准确。

---

### [LOW] ExecutionResult 缺少 action_id / action_title

**位置**: `services/agent/nodes/execution_node.py`，`agent/state/types.py`

**描述**: `ExecutionResult` 只有 `action_type`、`success`、`detail`，缺少 `action_id`。前端 `execution_result` 消息无法将执行结果精确映射回具体动作，只能按 action_type 做模糊匹配。

**建议**: `ExecutionResult` 增加 `action_id: str | None` 可选字段，ExecutionNode 赋值。

---

### [LOW] ExecutionConfirmPanel 确认按钮 disabled 逻辑有歧义

**位置**: `apps/web/src/components/planner/ExecutionConfirmPanel.tsx`

**描述**: `allChecklistChecked` 要求 `checkedItems.length >= checklistItems.length && checkedItems.includes('safety')`，但 `safety` 不在 `checklistItems` 数组里，条件不够直观（实际等价于"5 项确认 + safety"共 6 个元素）。
