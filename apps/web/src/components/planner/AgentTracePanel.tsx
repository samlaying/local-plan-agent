'use client';

import React, { useEffect, useState } from 'react';
import { useWorkbench } from '@/features/planner/contexts/WorkbenchContext';
import { CheckCircleIcon, ClockIcon } from '../icons';
import { cn } from '@/lib/utils';

// Agent 处理步骤
interface AgentStep {
  id: string;
  label: string;
  status: 'pending' | 'processing' | 'completed';
  duration?: number;
}

const AGENT_STEPS: AgentStep[] = [
  { id: 'parse_intent', label: '理解你的出行需求', status: 'pending' },
  { id: 'search_candidates', label: '搜索附近合适地点', status: 'pending' },
  { id: 'check_constraints', label: '检查距离、营业和适合度', status: 'pending' },
  { id: 'generate_plans', label: '生成半日路线方案', status: 'pending' },
  { id: 'critique_plans', label: '检查排队和路线风险', status: 'pending' },
  { id: 'generate_actions', label: '准备可执行操作', status: 'pending' },
  { id: 'present_result', label: '整理成今日三条路', status: 'pending' },
];

export const AgentTracePanel: React.FC = () => {
  const { userIntent } = useWorkbench();
  const [steps, setSteps] = useState<AgentStep[]>(AGENT_STEPS);

  // 模拟 Agent 处理过程
  useEffect(() => {
    let currentStep = 0;

    const processSteps = setInterval(() => {
      if (currentStep >= steps.length) {
        clearInterval(processSteps);
        return;
      }

      setSteps(prevSteps =>
        prevSteps.map((step, index) =>
          index === currentStep
            ? { ...step, status: 'processing' }
            : index < currentStep
            ? { ...step, status: 'completed' }
            : step
        )
      );

      // 完成当前步骤
      setTimeout(() => {
        setSteps(prevSteps =>
          prevSteps.map((step, index) =>
            index === currentStep ? { ...step, status: 'completed' } : step
          )
        );
        currentStep++;
      }, 1500);
    }, 2000);

    return () => clearInterval(processSteps);
  }, []);

  // 提取的偏好关键词（示例）
  const preferenceTags = [
    { label: '亲子', checked: true },
    { label: '半日', checked: true },
    { label: '离家近', checked: true },
    { label: '轻松散步', checked: true },
    { label: '可拍照', checked: true },
    { label: '不太累', checked: true },
  ];

  return (
    <div className="max-w-4xl mx-auto">
      {/* 用户输入摘要 */}
      <div className="card-paper p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-ink">你的需求</h3>
          <button className="text-sm text-clay-orange hover:underline">
            修改
          </button>
        </div>
        <p className="text-ink mb-4">{userIntent || '今天下午想和老婆孩子出去玩几个小时，别离家太远'}</p>
        <div className="flex flex-wrap gap-2">
          <span className="chip selected">周末下午</span>
          <span className="chip selected">轻松散步</span>
          <span className="chip selected">可拍照</span>
          <span className="chip selected">不太累</span>
        </div>
      </div>

      {/* Agent 理解中 */}
      <div className="card-paper p-6 mb-6">
        <h3 className="text-lg font-bold text-ink mb-2">Agent 理解中</h3>
        <p className="text-muted mb-4">正在理解你的偏好，马上为你生成路线</p>

        {/* 提取的偏好关键词 */}
        <div className="mb-6">
          <p className="text-sm text-muted mb-3">提取的偏好关键词：</p>
          <div className="flex flex-wrap gap-2">
            {preferenceTags.map((tag, index) => (
              <div
                key={index}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200',
                  tag.checked
                    ? 'bg-pine-green-soft text-pine-green border border-pine-green'
                    : 'bg-card-soft text-muted border border-line'
                )}
              >
                {tag.checked && <CheckCircleIcon className="w-3 h-3" />}
                {tag.label}
              </div>
            ))}
          </div>
        </div>

        {/* 处理步骤 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {steps.map((step, index) => {
            const Icon = step.status === 'completed' ? CheckCircleIcon : ClockIcon;

            return (
              <div
                key={step.id}
                className={cn(
                  'card-paper p-4 transition-all duration-200',
                  step.status === 'processing' && 'border-clay-orange shadow-clay',
                  step.status === 'completed' && 'border-pine-green'
                )}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon
                    className={cn(
                      'w-4 h-4',
                      step.status === 'processing' && 'text-clay-orange animate-pulse',
                      step.status === 'completed' && 'text-pine-green',
                      step.status === 'pending' && 'text-muted'
                    )}
                  />
                  <span className="text-sm font-medium text-ink">{step.label}</span>
                </div>

                {/* 状态指示 */}
                {step.status === 'processing' && (
                  <div className="flex items-center gap-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-clay-orange animate-pulse"></div>
                    <div className="w-1.5 h-1.5 rounded-full bg-clay-orange animate-pulse" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-1.5 h-1.5 rounded-full bg-clay-orange animate-pulse" style={{ animationDelay: '300ms' }}></div>
                  </div>
                )}

                {step.status === 'completed' && (
                  <div className="text-xs text-pine-green">完成</div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Skeleton 加载状态 */}
      <div className="space-y-4">
        {/* 路线地图预览 */}
        <div className="card-paper p-6">
          <h4 className="text-sm font-bold text-ink mb-3">路线地图预览（生成中）</h4>
          <div className="skeleton h-48 rounded-xl bg-card-soft"></div>
        </div>

        {/* 行程时间预览 */}
        <div className="card-paper p-6">
          <h4 className="text-sm font-bold text-ink mb-3">行程时间预览（生成中）</h4>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-12 rounded-lg bg-card-soft"></div>
            ))}
          </div>
        </div>

        {/* 路线方案预览 */}
        <div className="card-paper p-6">
          <h4 className="text-sm font-bold text-ink mb-3">路线方案预览（生成中）</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-32 rounded-xl bg-card-soft"></div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};