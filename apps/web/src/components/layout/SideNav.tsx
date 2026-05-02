'use client';

import React, { useState } from 'react';
import { useWorkbench } from '@/features/planner/contexts/WorkbenchContext';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { MapPinIcon, CalendarIcon, UsersIcon, CheckCircleIcon } from '../icons';

interface SideNavProps {
  currentState: string;
}

type NavSection = 'today' | 'my-plans' | 'favorites' | 'city-guide' | 'companions';

export const SideNav: React.FC<SideNavProps> = ({ currentState }) => {
  const { transitionTo } = useWorkbench();
  const router = useRouter();
  const [activeSection, setActiveSection] = useState<NavSection>('today');

  const menuItems = [
    { id: 'today' as NavSection, label: '今日规划', icon: MapPinIcon, route: '/' },
    { id: 'my-plans' as NavSection, label: '我的游笺', icon: CalendarIcon, route: '/my-plans' },
    { id: 'favorites' as NavSection, label: '收藏灵感', icon: CheckCircleIcon, route: '/favorites' },
    { id: 'city-guide' as NavSection, label: '城市志', icon: MapPinIcon, route: '/city-guide' },
    { id: 'companions' as NavSection, label: '同行记录', icon: UsersIcon, route: '/companions' },
  ];

  const handleNavClick = (item: typeof menuItems[0]) => {
    setActiveSection(item.id);

    // 如果是今日规划，使用工作台状态切换
    if (item.id === 'today') {
      transitionTo('input');
    } else {
      // 其他菜单项暂时显示"开发中"提示
      alert(`${item.label}功能正在开发中，敬请期待！`);
    }
  };

  return (
    <nav className="fixed left-0 top-[72px] bottom-0 w-[220px] bg-card-bg border-r border-line p-6 hidden md:block">
      {/* 导航菜单 */}
      <div className="space-y-2">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeSection === item.id;

          return (
            <button
              key={item.id}
              onClick={() => handleNavClick(item)}
              className={cn(
                'w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-200',
                isActive
                  ? 'bg-card-soft text-clay-orange font-medium'
                  : 'text-muted hover:text-ink hover:bg-card-soft'
              )}
            >
              <Icon className="w-5 h-5" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* 底部设置和帮助 */}
      <div className="absolute bottom-6 left-6 right-6 space-y-2">
        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-muted hover:text-ink hover:bg-card-soft transition-all duration-200">
          <span className="w-5 h-5 flex items-center justify-center text-sm">⚙</span>
          <span>设置</span>
        </button>
        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-muted hover:text-ink hover:bg-card-soft transition-all duration-200">
          <span className="w-5 h-5 flex items-center justify-center text-sm">?</span>
          <span>帮助与反馈</span>
        </button>
      </div>

      {/* 装饰元素 - 植物插画效果 */}
      <div className="absolute top-1/4 right-2 w-16 h-16 opacity-10 pointer-events-none">
        <div className="w-full h-full rounded-full bg-pine-green blur-2xl"></div>
      </div>
    </nav>
  );
};