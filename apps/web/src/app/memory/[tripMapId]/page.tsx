'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { Button } from '@/components/ui';
import { MockRouteMap } from '@/components/map';
import { getCollaborationMap } from '@/lib/api';

export default function MemoryPage() {
  const params = useParams();
  const tripMapId = params.tripMapId as string;

  // 模拟今日足迹数据
  const todayMemory = {
    title: '徐汇文博半日游',
    subtitle: '文化与咖啡香的一段小确幸',
    date: '2025年5月2日',
    stats: {
      duration: '3.5小时',
      distance: '3.2公里',
      stops: 3,
      photos: 16,
    },
  };

  const mockStops = [
    {
      id: '1',
      name: '徐家汇公园',
      type: 'activity' as const,
      address: '徐家汇路168号',
      duration: '40分钟',
      description: '轻松的公园散步，享受午后的阳光',
    },
    {
      id: '2',
      name: '街区咖啡',
      type: 'meal' as const,
      address: '天钥桥路133号',
      duration: '50分钟',
      description: '特色咖啡店，环境舒适，适合聊天休息',
    },
    {
      id: '3',
      name: '上海自然博物馆',
      type: 'activity' as const,
      address: '静安区北京西路510号',
      duration: '60分钟',
      description: '教育性的博物馆参观，学习新知识',
    },
  ];

  const mockTimeline = [
    { time: '14:00', action: '出发', description: '从徐家汇出发' },
    { time: '14:15', action: '徐家汇公园', description: '轻松散步 40分钟' },
    { time: '15:00', action: '街区咖啡', description: '休息用餐 50分钟' },
    { time: '16:00', action: '上海自然博物馆', description: '参观学习 60分钟' },
    { time: '17:00', action: '返回', description: '活动结束' },
  ];

  // 模拟照片数据
  const mockPhotos = [
    { id: '1', url: '🌳', title: '公园风景' },
    { id: '2', url: '☕', title: '咖啡时光' },
    { id: '3', url: '🏛️', title: '博物馆一角' },
    { id: '4', url: '👨‍👩‍👧‍👦', title: '亲子时光' },
  ];

  return (
    <div className="min-h-screen bg-paper-bg">
      {/* 顶部导航 */}
      <header className="bg-card-bg border-b border-line p-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold text-ink">今日足迹</h1>
          <div className="text-sm text-muted">{todayMemory.date}</div>
        </div>
      </header>

      {/* 主要内容 */}
      <div className="max-w-6xl mx-auto p-6">
        {/* 标题 */}
        <div className="text-center mb-8">
          <div className="text-sm text-muted mb-2">行程已完成</div>
          <h2 className="text-3xl font-bold text-ink mb-2">{todayMemory.title}</h2>
          <p className="text-muted">{todayMemory.subtitle}</p>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="card-paper p-4 text-center">
            <div className="text-2xl font-bold text-ink">{todayMemory.stats.duration}</div>
            <div className="text-xs text-muted">总时长</div>
          </div>
          <div className="card-paper p-4 text-center">
            <div className="text-2xl font-bold text-ink">{todayMemory.stats.distance}</div>
            <div className="text-xs text-muted">总距离</div>
          </div>
          <div className="card-paper p-4 text-center">
            <div className="text-2xl font-bold text-ink">{todayMemory.stats.stops}</div>
            <div className="text-xs text-muted">打卡地点</div>
          </div>
          <div className="card-paper p-4 text-center">
            <div className="text-2xl font-bold text-ink">{todayMemory.stats.photos}</div>
            <div className="text-xs text-muted">照片</div>
          </div>
        </div>

        {/* 足迹地图回顾 + 行程时间轴 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* 足迹地图回顾 */}
          <div className="card-paper p-6">
            <h3 className="text-lg font-bold text-ink mb-4">足迹地图回顾</h3>
            <MockRouteMap stops={mockStops} mode="memory" />
          </div>

          {/* 行程时间轴 */}
          <div className="card-paper p-6">
            <h3 className="text-lg font-bold text-ink mb-4">行程时间轴</h3>
            <div className="space-y-4">
              {mockTimeline.map((item, index) => (
                <div key={index} className="flex gap-3">
                  <div className="flex-shrink-0 w-14 text-right text-sm text-muted">
                    {item.time}
                  </div>
                  <div className="flex-shrink-0 w-2 h-2 rounded-full bg-clay-orange mt-1.5"></div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-ink">{item.action}</div>
                    <div className="text-xs text-muted">{item.description}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 路打卡记录 */}
        <div className="card-paper p-6 mb-8">
          <h3 className="text-lg font-bold text-ink mb-4">打卡记录</h3>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {mockPhotos.map((photo) => (
              <div
                key={photo.id}
                className="flex-shrink-0 w-24 h-24 rounded-xl bg-gradient-to-br from-clay-orange/20 to-pine-green/20 flex items-center justify-center text-3xl cursor-pointer hover:shadow-paper-hover transition-all"
              >
                {photo.url}
              </div>
            ))}
          </div>
        </div>

        {/* Agent 小结 */}
        <div className="card-paper p-6 mb-8">
          <h3 className="text-lg font-bold text-ink mb-4">Agent 小结</h3>
          <div className="text-muted leading-relaxed">
            <p className="mb-2">
              这是一次很棒的半日探索！路线安排合理，既有户外的轻松散步，也有室内的文化体验。
              咖啡店的休息时间恰到好处，让整个行程节奏舒适自然。
            </p>
            <p>
              博物馆参观不仅增加了知识性，也为亲子时光增添了教育意义。3.5小时的时长安排适中，
              不会太累，让每个人都能享受这段周末时光。
            </p>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex flex-wrap gap-3 justify-center mb-8">
          <Button variant="secondary">
            保存游笺
          </Button>
          <Button variant="secondary">
            分享回顾
          </Button>
          <Button
            variant="primary"
            onClick={() => window.location.href = '/'}
          >
            再来一条新路线
          </Button>
        </div>

        {/* 底部文案 */}
        <footer className="text-center text-sm text-muted pb-8">
          <p>把周末的空白，写成一张可以出发的城市路书。</p>
          <p className="mt-2">城市很大，半日刚好。</p>
        </footer>
      </div>
    </div>
  );
}