'use client';

import React from 'react';
import type { ItineraryPlan } from '@/types/planning';
import { ClockIcon, MapPinIcon, UtensilsIcon, ActivityIcon } from '../icons';
import { cn } from '@/lib/utils';

interface ItineraryTimelineProps {
  plan: ItineraryPlan;
}

export const ItineraryTimeline: React.FC<ItineraryTimelineProps> = ({ plan }) => {
  // 模拟时间线数据
  const mockTimeline = [
    {
      time: '14:00',
      action: '出发',
      icon: MapPinIcon,
      description: '从徐家汇出发',
      type: 'origin',
    },
    {
      time: '14:15',
      action: '徐家汇公园',
      icon: ActivityIcon,
      description: '轻松散步 40分钟',
      type: 'activity',
    },
    {
      time: '15:00',
      action: '街区咖啡',
      icon: UtensilsIcon,
      description: '休息用餐 50分钟',
      type: 'meal',
    },
    {
      time: '16:00',
      action: '上海自然博物馆',
      icon: ActivityIcon,
      description: '参观学习 60分钟',
      type: 'activity',
    },
    {
      time: '17:00',
      action: '返回',
      icon: MapPinIcon,
      description: '活动结束',
      type: 'destination',
    },
  ];

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'origin':
        return 'bg-pine-green';
      case 'destination':
        return 'bg-pine-green';
      case 'meal':
        return 'bg-clay-orange';
      case 'activity':
        return 'bg-blue-500';
      default:
        return 'bg-muted';
    }
  };

  return (
    <div className="space-y-4">
      {mockTimeline.map((item, index) => {
        const Icon = item.icon;

        return (
          <div key={index} className="flex gap-4">
            {/* 时间 */}
            <div className="flex-shrink-0 w-16 text-right">
              <div className="text-sm font-medium text-ink">{item.time}</div>
            </div>

            {/* 图标 */}
            <div className="flex-shrink-0 relative">
              <div
                className={cn(
                  'w-10 h-10 rounded-full flex items-center justify-center text-white',
                  getTypeColor(item.type)
                )}
              >
                <Icon className="w-5 h-5" />
              </div>
              {/* 连接线 */}
              {index < mockTimeline.length - 1 && (
                <div className="absolute top-10 left-1/2 w-0.5 h-full bg-line -translate-x-1/2"></div>
              )}
            </div>

            {/* 内容 */}
            <div className="flex-1 pb-8">
              <div className="font-medium text-ink mb-1">{item.action}</div>
              <div className="text-sm text-muted">{item.description}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
};