# BUGS

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

## [2026-05-02] ExecutionConfirmPanel 确认按钮 disabled 逻辑有歧义

**位置**: `apps/web/src/components/planner/ExecutionConfirmPanel.tsx`

**描述**: `allChecklistChecked` 要求 `checkedItems.length >= checklistItems.length && checkedItems.includes('safety')`。但 `safety` 不在 `checklistItems` 数组里，所以实际需要 `checkedItems.length >= 5`（checklist 项）且包含 `'safety'`，即至少 6 个元素。这与界面逻辑隐含的"5项确认 + 1项安全须知"一致，但条件写得不够直观。
