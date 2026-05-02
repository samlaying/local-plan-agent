'use client';

import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { MapPinIcon } from '../icons';

interface MapStop {
  id: string;
  name: string;
  type: 'origin' | 'activity' | 'meal' | 'rest' | 'destination';
  address: string;
  duration: string;
  description: string;
}

interface MockRouteMapProps {
  stops: MapStop[];
  selectedStopId?: string;
  onSelectStop?: (stopId: string) => void;
  mode?: 'preview' | 'detail' | 'memory';
}

export const MockRouteMap: React.FC<MockRouteMapProps> = ({
  stops,
  selectedStopId,
  onSelectStop,
  mode = 'preview'
}) => {
  const [hoveredStopId, setHoveredStopId] = useState<string | null>(null);

  // 模拟地图坐标 (相对位置 0-100)
  const mapCoordinates = stops.map((stop, index) => ({
    ...stop,
    x: 20 + (index * 25), // 横向分布
    y: 30 + (index % 2) * 30, // 纵向交错
  }));

  // 获取标记样式
  const getMarkerStyle = (stop: MapStop, index: number) => {
    const isSelected = selectedStopId === stop.id;
    const isHovered = hoveredStopId === stop.id;

    let bgColor = 'bg-clay-orange';
    let scale = isSelected || isHovered ? 'scale-110' : 'scale-100';

    switch (stop.type) {
      case 'origin':
        bgColor = 'bg-pine-green';
        break;
      case 'destination':
        bgColor = 'bg-pine-green';
        break;
      case 'meal':
        bgColor = 'bg-clay-orange';
        break;
      case 'activity':
        bgColor = 'bg-clay-orange';
        break;
      default:
        bgColor = 'bg-muted';
    }

    return { bgColor, scale };
  };

  return (
    <div className="relative w-full h-80 bg-gradient-to-br from-[#FFFDF8] to-[#F8F1E7] rounded-2xl overflow-hidden border border-line">
      {/* 纸质地图背景 */}
      <div className="absolute inset-0 opacity-20">
        {/* 网格线 */}
        <svg className="w-full h-full">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#E8DCCB" strokeWidth="0.5"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>

        {/* 装饰性元素 */}
        <div className="absolute top-4 right-4 w-16 h-16 rounded-full bg-pine-green/10 blur-2xl"></div>
        <div className="absolute bottom-4 left-4 w-20 h-20 rounded-full bg-clay-orange/10 blur-2xl"></div>
      </div>

      {/* 路线连接线 */}
      <svg className="absolute inset-0 w-full h-full">
        {mapCoordinates.slice(0, -1).map((stop, index) => {
          const nextStop = mapCoordinates[index + 1];
          return (
            <line
              key={`route-${index}`}
              x1={`${stop.x}%`}
              y1={`${stop.y}%`}
              x2={`${nextStop.x}%`}
              y2={`${nextStop.y}%`}
              stroke="#D97745"
              strokeWidth="3"
              strokeDasharray="8,8"
              strokeLinecap="round"
              opacity="0.6"
            />
          );
        })}
      </svg>

      {/* 地图标记 */}
      {mapCoordinates.map((stop, index) => {
        const { bgColor, scale } = getMarkerStyle(stop, index);
        const isSelected = selectedStopId === stop.id;
        const isHovered = hoveredStopId === stop.id;

        return (
          <div
            key={stop.id}
            className="absolute cursor-pointer transition-transform duration-200"
            style={{
              left: `${stop.x}%`,
              top: `${stop.y}%`,
              transform: `translate(-50%, -50%) ${scale === 'scale-110' ? 'scale(1.1)' : ''}`,
            }}
            onMouseEnter={() => setHoveredStopId(stop.id)}
            onMouseLeave={() => setHoveredStopId(null)}
            onClick={() => onSelectStop?.(stop.id)}
          >
            {/* 标记圆圈 */}
            <div
              className={cn(
                'w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-lg transition-all duration-200',
                bgColor,
                (isSelected || isHovered) && 'shadow-xl ring-4 ring-white/50'
              )}
            >
              {index + 1}
            </div>

            {/* 悬浮提示 */}
            {(isHovered || isSelected) && (
              <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 bg-white rounded-lg shadow-paper p-3 min-w-[150px] z-10">
                <div className="font-bold text-ink text-sm mb-1">{stop.name}</div>
                <div className="text-xs text-muted">{stop.description}</div>
                {stop.duration && (
                  <div className="text-xs text-clay-orange mt-1">⏱️ {stop.duration}</div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* 图例 */}
      <div className="absolute bottom-4 right-4 bg-white/90 rounded-lg shadow-paper p-3">
        <div className="text-xs font-medium text-ink mb-2">图例</div>
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs">
            <div className="w-3 h-3 rounded-full bg-pine-green"></div>
            <span className="text-muted">起点/终点</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <div className="w-3 h-3 rounded-full bg-clay-orange"></div>
            <span className="text-muted">活动/餐饮</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <div className="w-8 h-0.5 bg-clay-orange" style={{ borderStyle: 'dashed' }}></div>
            <span className="text-muted">路线</span>
          </div>
        </div>
      </div>

      {/* 装饰性罗盘 */}
      <div className="absolute top-4 left-4 w-12 h-12 rounded-full bg-white/80 shadow-paper flex items-center justify-center">
        <div className="text-xs">
          <div className="text-center">N</div>
          <div className="text-muted">↑</div>
        </div>
      </div>

      {/* 总距离和时长 */}
      <div className="absolute bottom-4 left-4 bg-white/90 rounded-lg shadow-paper px-3 py-2">
        <div className="text-xs text-muted">总距离 3.2km · 预计 3.5小时</div>
      </div>
    </div>
  );
};