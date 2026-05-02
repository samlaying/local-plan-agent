'use client';

import React from 'react';
import { WorkbenchState } from '@/features/planner/contexts/WorkbenchContext';
import { CalendarIcon, UsersIcon, BellIcon } from '../icons';
import { cn } from '@/lib/utils';

interface AppHeaderProps {
  currentState: WorkbenchState;
}

export const AppHeader: React.FC<AppHeaderProps> = ({ currentState }) => {
  // 流程进度定义
  const progressSteps = [
    { state: 'input' as WorkbenchState, label: '输入需求' },
    { state: 'generating' as WorkbenchState, label: '生成路线' },
    { state: 'plan_select' as WorkbenchState, label: '选择方案' },
    { state: 'plan_detail' as WorkbenchState, label: '路书详情' },
    { state: 'sharing' as WorkbenchState, label: '分享同行' },
    { state: 'execution_confirm' as WorkbenchState, label: '出发确认' },
    { state: 'execution_done' as WorkbenchState, label: '完成' },
  ];

  const getCurrentStepIndex = () => {
    return progressSteps.findIndex(step => step.state === currentState);
  };

  const currentStepIndex = getCurrentStepIndex();

  return (
    <header className="fixed top-0 left-0 right-0 h-[72px] bg-card-bg border-b border-line z-50">
      <div className="h-full px-6 flex items-center justify-between">
        {/* 左侧：城市和天气 */}
        <div className="flex items-center gap-6">
          <h1 className="text-xl font-bold text-ink">半日游笺</h1>
          <div className="flex items-center gap-2 text-muted text-sm">
            <CalendarIcon className="w-4 h-4" />
            <span>上海 · 徐汇区</span>
            <span className="text-line">|</span>
            <span>23°C 晴</span>
          </div>
        </div>

        {/* 中间：流程进度 */}
        <div className="hidden md:flex items-center gap-2">
          {progressSteps.map((step, index) => {
            const isCompleted = index < currentStepIndex;
            const isCurrent = index === currentStepIndex;
            const isPending = index > currentStepIndex;

            return (
              <React.Fragment key={step.state}>
                {/* 步骤点 */}
                <div className="flex items-center gap-2">
                  <div
                    className={cn(
                      'w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-all duration-300',
                      isCurrent && 'bg-clay-orange text-white scale-110',
                      isCompleted && 'bg-pine-green text-white',
                      isPending && 'bg-gray-100 text-muted border-2 border-line'
                    )}
                  >
                    {isCompleted ? '✓' : index + 1}
                  </div>
                  <span
                    className={cn(
                      'text-xs font-medium transition-all duration-300',
                      isCurrent && 'text-clay-orange',
                      isCompleted && 'text-pine-green',
                      isPending && 'text-muted'
                    )}
                  >
                    {step.label}
                  </span>
                </div>

                {/* 连接线（除了最后一个步骤） */}
                {index < progressSteps.length - 1 && (
                  <div
                    className={cn(
                      'w-8 h-0.5 transition-all duration-300',
                      isCompleted ? 'bg-pine-green' : 'bg-line'
                    )}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* 移动端简化进度指示 */}
        <div className="md:hidden text-sm text-muted">
          {currentStepIndex + 1}/7
        </div>

        {/* 右侧：通知和用户头像 */}
        <div className="flex items-center gap-2 md:gap-4">
          <button className="relative p-2 text-muted hover:text-ink transition-colors">
            <BellIcon className="w-5 h-5" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-clay-orange rounded-full"></span>
          </button>
          <div className="hidden md:flex items-center gap-3">
            <div className="text-right">
              <div className="text-sm font-medium text-ink">用户</div>
              <div className="text-xs text-muted">今天也好心情</div>
            </div>
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-clay-orange to-clay-orange-dark flex items-center justify-center text-white font-bold">
              U
            </div>
          </div>
          {/* 移动端头像 */}
          <div className="md:hidden w-8 h-8 rounded-full bg-gradient-to-br from-clay-orange to-clay-orange-dark flex items-center justify-center text-white text-sm font-bold">
            U
          </div>
        </div>
      </div>
    </header>
  );
};