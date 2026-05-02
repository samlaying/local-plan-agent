'use client';

import { useWorkbench } from '@/features/planner/contexts/WorkbenchContext';
import { GoalInputCard, AgentTracePanel, PlanCompareGrid, PlanDetailPanel, ExecutionConfirmPanel, ExecutionDonePanel } from '@/components/planner';
import { ShareLinkCard, MemberList, CommentList, CommentComposer, VotePanel } from '@/components/collaboration';

export default function HomePage() {
  const { currentState, startPlanning } = useWorkbench();

  // 处理需求提交 — 通过 WebSocket 发起规划
  const handleIntentSubmit = async (intent: string) => {
    startPlanning(intent, {
      city: 'Shanghai',
      address: '徐家汇',
      lat: 31.2304,
      lng: 121.4737,
    });
  };

  // 根据当前状态渲染不同内容
  const renderContent = () => {
    switch (currentState) {
      case 'input':
        return <GoalInputCard onSubmit={handleIntentSubmit} />;

      case 'generating':
        return <AgentTracePanel />;

      case 'plan_select':
        return <PlanCompareGrid />;

      case 'plan_detail':
        return <PlanDetailPanel />;

      case 'sharing':
        return (
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-ink mb-2">群组分享 + 同行反馈</h2>
              <p className="text-muted">把路线分享给家人或朋友，一起完善这段半日时光</p>
            </div>

            <div className="space-y-6">
              <ShareLinkCard />
              <MemberList members={[
                { id: '1', name: '小明', status: 'joined' as const },
                { id: '2', name: '小红', status: 'joined' as const },
              ]} />
              <VotePanel />
              <CommentList comments={[
                { id: '1', author: '小明', content: '这个路线看起来不错', createdAt: new Date().toISOString() },
              ]} />
              <CommentComposer />
            </div>
          </div>
        );

      case 'execution_confirm':
        return <ExecutionConfirmPanel />;

      case 'execution_done':
        return <ExecutionDonePanel />;

      default:
        return null;
    }
  };

  return (
    <>{renderContent()}</>
  );
}
