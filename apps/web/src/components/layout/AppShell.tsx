'use client';

import React, { ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import { useWorkbench } from '@/features/planner/contexts/WorkbenchContext';
import { AppHeader } from './AppHeader';
import { SideNav } from './SideNav';
import { RightContextPanel } from './RightContextPanel';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';

interface AppShellProps {
  children: ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const { currentState } = useWorkbench();
  const pathname = usePathname();
  const showRightPanel = pathname === '/';

  return (
    <div className="min-h-screen bg-paper-bg">
      {/* 顶部导航栏 */}
      <AppHeader currentState={currentState} />

      {/* 主内容区 - 三栏布局 */}
      <div className="flex pt-[72px]">
        {/* 左侧导航 - 220px (桌面端显示，移动端隐藏) */}
        <div className="hidden md:block">
          <SideNav currentState={currentState} />
        </div>

        {/* 中间主任务区 - flex-1 */}
        <main className={cn(
          'flex-1 px-4 md:px-8 py-6 overflow-y-auto md:pl-[252px]',
          showRightPanel ? 'lg:pr-[332px]' : 'lg:pr-8'
        )}>
          {children}
        </main>

        {/* 右侧上下文区 - 300px (桌面端显示，移动端隐藏) */}
        {showRightPanel && <div className="hidden lg:block">
          <RightContextPanel currentState={currentState} />
        </div>}
      </div>

      {/* 移动端底部操作栏 */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 bg-card-bg border-t border-line p-4 z-40">
        <div className="flex items-center justify-between text-sm">
          <div className="text-muted">
            {currentState === 'input' && '输入需求'}
            {currentState === 'generating' && '生成中...'}
            {currentState === 'plan_select' && '选择方案'}
            {currentState === 'plan_detail' && '查看详情'}
            {currentState === 'sharing' && '分享同行'}
            {currentState === 'execution_confirm' && '确认出发'}
            {currentState === 'execution_done' && '已完成'}
          </div>
          <Button size="sm">
            操作
          </Button>
        </div>
      </div>
    </div>
  );
};
