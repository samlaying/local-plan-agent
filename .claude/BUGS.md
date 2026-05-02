# BUGS

## [2026-05-02] IntentParserNode 追问通过 trace 传递，Orchestrator 需要解析 trace 才能提取追问文本

**位置**: `services/agent/nodes/intent_parser.py`，`services/agent/state/types.py`

**描述**: `IntentParserNode` 在需要追问时将追问文本以 `[clarification] <text>` 格式写入 `state.trace`（TraceEvent.message 字段），而不是写入 `PlanningState` 的专用字段。Orchestrator 若要读取追问文本，必须扫描 trace 列表寻找前缀为 `[clarification]` 的条目——这是一个隐式协议，容易在重构时被意外破坏。

**建议**: 在 `PlanningState` 上增加 `pending_clarification: str | None = None` 字段，由 IntentParserNode 直接写入，Orchestrator 读取后清空。

**影响**: 低。当前 Orchestrator 未实现，暂无实际影响，但会成为 Phase 2 的隐患。

---

## [2026-05-02] WorkbenchContext canTransitionTo 是非稳定闭包

**位置**: `apps/web/src/features/planner/contexts/WorkbenchContext.tsx`

**描述**: 原始代码中 `canTransitionTo` 依赖 `currentState` 并在 `transitionTo` 的 `useCallback` 依赖数组里引用，但 `transitionTo` 的依赖数组只有 `[currentState, setActiveTab]`，导致每次状态变化都重新生成新函数引用，可能造成子组件不必要的重渲染。

新版改用 `currentStateRef` 规避了这个问题，但 `canTransitionTo` 暴露给消费者的实现依然是基于 ref，调用时是即时准确的，不过作为 context value 它不会触发消费方重渲染（因为函数引用不变）。如果消费方需要响应式地知道"当前能否转换到 X"，这个函数不会自动触发 re-render。

**影响**: 低。当前消费方都是在事件处理函数里调用，无响应式依赖需求。

---

## [2026-05-02] wsClient 在 SSR 环境下实例化 WebSocket

**位置**: `apps/web/src/lib/ws-client.ts`

**描述**: `wsClient` 是模块级单例，在 Next.js 的服务端渲染（SSR）或静态生成阶段被 import 时，`new WebSocket(...)` 在 Node.js 环境下不存在，会抛出 `ReferenceError: WebSocket is not defined`。

目前 `connect()` 只在 `WorkbenchProvider` 的 `useEffect` 里被调用（客户端），实例化本身不调用 `new WebSocket`，所以暂时安全。但如果未来有服务端 import 此模块的路径，就会出问题。

**建议**: 将 `wsClient` 用 lazy 初始化封装，或加 `typeof window !== 'undefined'` guard。

---

## [2026-05-02] Orchestrator Phase 1: location 数据通过非类型化属性传递

**位置**: `services/agent/workflow/orchestrator.py`，`_phase_start` 和 `_phase_generate_plans`

**描述**: `_phase_start` 将客户端传来的 location dict 挂在 `session._location_raw` 上（`type: ignore[attr-defined]`），Session 类没有这个字段，属于 Phase 1 骨架为了快速实现而做的 hack。Phase 2 应当将 location 存入 `PlanningState` 的正式字段（如 `state.retrieval` 的 route_info，或在 `PlanningState` 上新增 `origin_location` 字段）。

**影响**: 中。类型系统无法捕获此属性，重构 Session 时容易漏掉。

---

---

## [2026-05-02] Phase 1 Review: 前后端消息协议不对齐 — payload 包装层缺失 (blocking)

**位置**: `services/agent/workflow/orchestrator.py` + `apps/web/src/features/planner/contexts/WorkbenchContext.tsx`

**描述**: 前端发送消息格式为 `{ type, payload: { ... } }`（由 `ClientMessage` 类型约束），但后端 Orchestrator 直接读取顶层字段。

具体冲突：
- `start` 消息：前端发 `{ type: 'start', payload: { query, location } }`，后端读 `msg.get("query")` / `msg.get("location")`，永远取到空值。
- `plan_confirmed`：前端发 `{ type: 'plan_confirmed', payload: { plan_id } }`，后端读 `msg.get("plan_id")`，永远为 `None`，导致 `confirmed = plans[0]`（无论用户选哪个方案都取第一个）。
- `plan_rejected`、`execution_confirmed` 同理。

后端 `_phase_start` 取到的 `query` 永远是 `""`，`location` 永远是 `{}`，规划流程实际运行在空输入上。

**影响**: blocking。当前端与后端对接时，start 消息的 query/location 全部丢失，规划无法正确启动。

---

## [2026-05-02] Phase 1 Review: TraceStatus 枚举值前后端不一致 (blocking)

**位置**: `services/agent/state/types.py` vs `apps/web/src/types/websocket.ts`

**描述**:
- 后端 `TraceStatus = Literal["running", "done", "error"]`
- 前端 `TraceStatus = 'running' | 'completed' | 'failed'`

后端发送 `"done"` 时，前端类型期待的是 `"completed"`；后端发送 `"error"` 时，前端期待 `"failed"`。前端渲染 trace 状态时会收到不在联合类型中的值，TypeScript 的类型守卫失效，UI 状态显示异常。

**影响**: blocking。所有 trace 事件的 done/error 状态在前端会被当成未知值处理。

---

## [2026-05-02] Phase 1 Review: error 消息缺少 recoverable 字段 (blocking)

**位置**: `services/agent/workflow/orchestrator.py:97` vs `apps/web/src/types/websocket.ts:WsErrorData`

**描述**: 后端发送错误消息 `{"type": "error", "message": str(exc)}`，缺少 `recoverable` 字段。前端 `onError` 回调解构时读取 `recoverable`，得到 `undefined`，`!recoverable` 判断为 `true`，每次后端抛错都会将前端状态强制跳回 `input`，即使是本可重试的瞬时错误。

**影响**: blocking。任何后端异常都会导致前端 session 被强制重置。

---

## [2026-05-02] Phase 1 Review: onExecutionPreview 未触发状态转换到 execution_confirm (warning)

**位置**: `apps/web/src/features/planner/contexts/WorkbenchContext.tsx:199-201`

**描述**: `onExecutionPreview` 回调仅调用 `setExecutionActions(actions)`，没有将 WorkbenchState 切换到 `'execution_confirm'`。当后端推送 `execution_preview` 消息时，前端状态还停在 `plan_detail` 或其他状态，`ExecutionConfirmPanel` 不会渲染。

**影响**: warning。执行确认 UI 永远不会自动展现，用户无法看到确认面板。

---

## [2026-05-02] Phase 1 Review: OpenAIClient 超时异常可能漏捕获 (warning)

**位置**: `services/llm/providers/openai_client.py:100`

**描述**: 捕获的是内置 `TimeoutError`。但 `urllib.request.urlopen` 在超时时实际抛出 `socket.timeout`（继承自 `OSError`，不继承自内置 `TimeoutError`，Python 3.11 之前两者不等价）。Python 3.11+ `socket.timeout` 已成为 `TimeoutError` 的别名，3.11 以下版本超时会被 `except OSError` 捕获而非 `except TimeoutError`，导致错误消息为"网络连接异常"而非"请求超时"，且不包含超时时间信息。

**影响**: warning。不影响功能，但错误信息在 Python < 3.11 环境下不准确，重试逻辑仍然正常工作（OSError 会被上层 `except LLMError` 捕获后重试）。

---

## [2026-05-02] VerifierNode 依赖 verifier_rejection_reasons 字段，主干 PlanningState 缺失

**位置**: `services/agent/nodes/verifier_node.py`，`services/agent/state/types.py`

**描述**: VerifierNode 写入 `state.verifier_rejection_reasons`，但主干 `services/agent/state/types.py`（master 分支）中 `PlanningState` 没有这个字段，只有 `plan_revision_count`。worktree `agent-aaef7f23` 的 `state/types.py` 已添加该字段，但若其他 worktree 或主干的 Orchestrator 使用未更新的 `PlanningState`，运行时会触发 `AttributeError: 'PlanningState' object has no attribute 'verifier_rejection_reasons'`。

**影响**: medium。当 VerifierNode 首次接入主干 Orchestrator 时必须同步更新 `PlanningState`，否则运行时崩溃。

---

## [2026-05-02] ExecutionConfirmPanel 确认按钮 disabled 逻辑有歧义

**位置**: `apps/web/src/components/planner/ExecutionConfirmPanel.tsx`

**描述**: `allChecklistChecked` 要求 `checkedItems.length >= checklistItems.length && checkedItems.includes('safety')`。但 `safety` 不在 `checklistItems` 数组里，所以实际需要 `checkedItems.length >= 5`（checklist 项）且包含 `'safety'`，即至少 6 个元素。这与界面逻辑隐含的"5项确认 + 1项安全须知"一致，但条件写得不够直观。
