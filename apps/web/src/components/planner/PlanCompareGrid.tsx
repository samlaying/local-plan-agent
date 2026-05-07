'use client';

import React, { useState } from 'react';
import { useWorkbench } from '@/features/planner/contexts/WorkbenchContext';
import { PlanCard } from './PlanCard';
import { Button } from '@/components/ui';

export const PlanCompareGrid: React.FC = () => {
  const { plans, selectedPlan, setSelectedPlan, transitionTo, rejectPlan } = useWorkbench();
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [rejectFeedback, setRejectFeedback] = useState('');

  // 模拟方案数据（实际应从 API 获取）
  const mockPlans = [
    {
      id: 'plan-1',
      title: '公园慢走线',
      summary: '轻松的公园散步路线，适合亲子互动',
      scenario: 'family_weight_loss_child5' as const,
      totalDurationMinutes: 210,
      estimatedCost: { min: 50, max: 100, currency: 'CNY' as const },
      score: 85,
      riskLevel: 'low' as const,
      steps: [],
      pois: [],
      actions: [],
      fitSummary: ['亲子友好', '户外活动', '轻松散步'],
      tradeoffs: ['可能会遇到人流高峰'],
    },
    {
      id: 'plan-2',
      title: '街区咖啡线',
      summary: '城市街区的咖啡文化探索',
      scenario: 'friends_4_mixed_gender' as const,
      totalDurationMinutes: 200,
      estimatedCost: { min: 80, max: 150, currency: 'CNY' as const },
      score: 78,
      riskLevel: 'medium' as const,
      steps: [],
      pois: [],
      actions: [],
      fitSummary: ['适合聊天', '轻社交', '有点新鲜感'],
      tradeoffs: ['咖啡店可能需要排队'],
    },
    {
      id: 'plan-3',
      title: '博物馆亲子线',
      summary: '教育性的博物馆参观路线',
      scenario: 'family_weight_loss_child5' as const,
      totalDurationMinutes: 220,
      estimatedCost: { min: 100, max: 200, currency: 'CNY' as const },
      score: 92,
      riskLevel: 'low' as const,
      steps: [],
      pois: [],
      actions: [],
      fitSummary: ['室内+户外', '轻松舒适', '教育意义'],
      tradeoffs: ['博物馆可能需要预约'],
    },
  ];

  const displayPlans = plans.length > 0 ? plans : mockPlans;

  // 处理方案选择
  const handleSelectPlan = (plan: typeof displayPlans[0]) => {
    setSelectedPlan(plan as any);
    // 这里应该调用 API 创建协作地图
    transitionTo('plan_detail');
  };

  // 处理查看详情
  const handleViewDetails = (plan: typeof displayPlans[0]) => {
    setSelectedPlan(plan as any);
    transitionTo('plan_detail');
  };

  // 推荐理由
  const recommendReasons = [
    {
      title: '亲子友好',
      description: '所有方案都考虑了孩子的需求，选择了安全、有趣的活动地点',
    },
    {
      title: '时间适中',
      description: '每个方案都控制在 3-4 小时，不会太累，适合半日游',
    },
    {
      title: '距离合理',
      description: '路线规划合理，避免长途奔波，让你有更多时间享受活动',
    },
  ];

  return (
    <div className="max-w-6xl mx-auto">
      {/* 页面标题 */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-ink mb-2">今日三条路</h2>
        <p className="text-muted">根据你的想法，我为你准备了三套不同风格的半日路线</p>

        {/* 标签 */}
        <div className="flex justify-center gap-2 mt-4">
          <span className="chip selected">亲子</span>
          <span className="chip selected">半日</span>
          <span className="chip selected">≤10km</span>
          <span className="chip selected">轻松散步</span>
        </div>
      </div>

      {/* 方案卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {displayPlans.map((plan) => (
          <PlanCard
            key={plan.id}
            plan={plan}
            state={selectedPlan?.id === plan.id ? 'selected' : 'default'}
            onSelect={() => handleSelectPlan(plan)}
            onViewDetails={() => handleViewDetails(plan)}
          />
        ))}
      </div>

      {/* 推荐理由 */}
      <div className="card-paper p-6">
        <h3 className="text-xl font-bold text-ink mb-4">为什么推荐这三条路</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {recommendReasons.map((reason, index) => (
            <div key={index} className="flex gap-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-clay-orange/10 flex items-center justify-center">
                <span className="text-clay-orange font-bold">{index + 1}</span>
              </div>
              <div>
                <h4 className="font-bold text-ink mb-1">{reason.title}</h4>
                <p className="text-sm text-muted">{reason.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 不满意 / 重新规划 */}
      <div className="mt-8">
        {!showRejectInput ? (
          <div className="flex justify-center gap-4">
            <Button
              variant="ghost"
              onClick={() => transitionTo('input')}
            >
              重新输入需求
            </Button>
            <Button
              variant="secondary"
              onClick={() => setShowRejectInput(true)}
            >
              不喜欢，重新规划
            </Button>
          </div>
        ) : (
          <div className="card-paper p-6 max-w-2xl mx-auto border-2 border-line">
            <h3 className="text-base font-bold text-ink mb-1">告诉我你想要什么方向（可选）</h3>
            <p className="text-sm text-muted mb-4">不填也可以直接提交，Agent 会重新规划</p>
            <textarea
              value={rejectFeedback}
              onChange={(e) => setRejectFeedback(e.target.value)}
              placeholder="例如：换个户外活动的、近一点的、预算再低一些…"
              rows={2}
              className="w-full bg-card-bg border border-line rounded-xl px-4 py-3 text-sm text-ink placeholder:text-muted resize-none focus:outline-none focus:border-clay-orange mb-4"
            />
            <div className="flex gap-3 justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowRejectInput(false);
                  setRejectFeedback('');
                }}
              >
                取消
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  rejectPlan(rejectFeedback.trim());
                  setShowRejectInput(false);
                  setRejectFeedback('');
                }}
              >
                重新规划
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};