'use client';

import React, { useState } from 'react';
import { useWorkbench } from '@/features/planner/contexts/WorkbenchContext';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';
import { ItineraryTimeline } from './ItineraryTimeline';
import { MockRouteMap } from '../map/MockRouteMap';

type RejectStep = 'idle' | 'input';

type TabType = 'overview' | 'map' | 'timeline' | 'reasons';

export const PlanDetailPanel: React.FC = () => {
  const { selectedPlan, transitionTo, activeTab, setActiveTab, rejectPlan } = useWorkbench();
  const [rejectStep, setRejectStep] = useState<RejectStep>('idle');
  const [rejectFeedback, setRejectFeedback] = useState('');

  if (!selectedPlan) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold text-ink mb-4">未选择方案</h2>
        <p className="text-muted">请先返回选择一个方案</p>
        <Button
          className="mt-4"
          onClick={() => transitionTo('plan_select')}
        >
          返回选择方案
        </Button>
      </div>
    );
  }

  const tabs = [
    { id: 'overview' as TabType, label: '总览' },
    { id: 'map' as TabType, label: '地图' },
    { id: 'timeline' as TabType, label: '时间线' },
    { id: 'reasons' as TabType, label: '推荐理由' },
  ];

  // 处理Tab切换
  const handleTabChange = (tabId: TabType) => {
    setActiveTab(tabId);
    console.log('Tab changed to:', tabId, 'Current activeTab:', activeTab);
  };

  // 模拟行程数据
  const mockStops = [
    {
      id: '1',
      name: '徐家汇公园',
      type: 'activity' as const,
      address: '徐家汇路168号',
      duration: '40分钟',
      description: '轻松的公园散步，适合亲子互动',
    },
    {
      id: '2',
      name: '街区咖啡',
      type: 'meal' as const,
      address: '天钥桥路133号',
      duration: '50分钟',
      description: '特色咖啡店，环境舒适',
    },
    {
      id: '3',
      name: '上海自然博物馆',
      type: 'activity' as const,
      address: '静安区北京西路510号',
      duration: '60分钟',
      description: '教育性的博物馆参观',
    },
  ];

  return (
    <div className="max-w-6xl mx-auto">
      {/* 返回按钮 */}
      <div className="mb-6">
        <button
          onClick={() => transitionTo('plan_select')}
          className="flex items-center gap-2 text-muted hover:text-ink transition-colors"
        >
          <span>←</span>
          <span>返回方案列表</span>
        </button>
      </div>

      {/* 方案标题 */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-ink mb-3">{selectedPlan.title}</h1>
        <div className="flex items-center gap-3 text-sm text-muted">
          <span className="chip selected">亲子友好</span>
          <span className="chip selected">室内+户外</span>
          <span className="chip selected">轻松舒适</span>
        </div>
      </div>

      {/* 方案摘要 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="card-paper p-4 text-center">
          <div className="text-2xl font-bold text-ink">
            {Math.floor(selectedPlan.totalDurationMinutes / 60)}h{selectedPlan.totalDurationMinutes % 60}m
          </div>
          <div className="text-xs text-muted">总时长</div>
        </div>
        <div className="card-paper p-4 text-center">
          <div className="text-2xl font-bold text-ink">3.2km</div>
          <div className="text-xs text-muted">总距离</div>
        </div>
        <div className="card-paper p-4 text-center">
          <div className="text-2xl font-bold text-ink">亲子</div>
          <div className="text-xs text-muted">适合人群</div>
        </div>
        <div className="card-paper p-4 text-center">
          <div className="text-2xl font-bold text-clay-orange">
            {selectedPlan.score}
          </div>
          <div className="text-xs text-muted">推荐度</div>
        </div>
      </div>

      {/* Tabs 导航 */}
      <div className="flex gap-2 mb-6 border-b border-line">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={cn(
              'px-4 py-2 font-medium transition-colors relative',
              activeTab === tab.id
                ? 'text-clay-orange'
                : 'text-muted hover:text-ink'
            )}
          >
            {tab.label}
            {activeTab === tab.id && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-clay-orange" />
            )}
          </button>
        ))}
      </div>

      {/* Tab 内容 */}
      <div className="mb-8">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* 路线概览 */}
            <div className="card-paper p-6">
              <h3 className="text-lg font-bold text-ink mb-4">路线概览</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <div className="text-sm text-muted mb-2">时长</div>
                  <div className="text-ink font-medium">
                    约{Math.floor(selectedPlan.totalDurationMinutes / 60)}小时
                    {selectedPlan.totalDurationMinutes % 60}分钟
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted mb-2">里程</div>
                  <div className="text-ink font-medium">3.2公里</div>
                </div>
                <div>
                  <div className="text-sm text-muted mb-2">出发点</div>
                  <div className="text-ink font-medium">徐家汇</div>
                </div>
                <div>
                  <div className="text-sm text-muted mb-2">适合人群</div>
                  <div className="text-ink font-medium">家庭、亲子、朋友</div>
                </div>
              </div>
            </div>

            {/* 地图预览 */}
            <div className="card-paper p-6">
              <h3 className="text-lg font-bold text-ink mb-4">路线地图</h3>
              <MockRouteMap stops={mockStops} />
            </div>
          </div>
        )}

        {activeTab === 'map' && (
          <div className="card-paper p-6">
            <h3 className="text-lg font-bold text-ink mb-4">详细地图</h3>
            <MockRouteMap stops={mockStops} mode="detail" />
          </div>
        )}

        {activeTab === 'timeline' && (
          <div className="card-paper p-6">
            <h3 className="text-lg font-bold text-ink mb-4">行程时间线</h3>
            <ItineraryTimeline plan={selectedPlan} />
          </div>
        )}

        {activeTab === 'reasons' && (
          <div className="space-y-6">
            <div className="card-paper p-6">
              <h3 className="text-lg font-bold text-ink mb-4">为什么推荐这条路线</h3>
              <div className="space-y-4">
                {selectedPlan.fitSummary.map((reason, index) => (
                  <div key={index} className="flex gap-3">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-clay-orange/10 flex items-center justify-center">
                      <span className="text-clay-orange text-xs">{index + 1}</span>
                    </div>
                    <div>
                      <h4 className="font-medium text-ink mb-1">{reason}</h4>
                      <p className="text-sm text-muted">
                        根据你的需求，这条路线特别适合{reason}的场景
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card-paper p-6">
              <h3 className="text-lg font-bold text-ink mb-4">需要权衡的地方</h3>
              <div className="space-y-3">
                {selectedPlan.tradeoffs.map((tradeoff, index) => (
                  <div key={index} className="flex items-start gap-2 text-sm text-muted">
                    <span>⚠️</span>
                    <span>{tradeoff}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 底部操作栏 */}
      <div className="card-paper p-6">
        {rejectStep === 'idle' ? (
          <div className="flex flex-wrap gap-3 justify-center">
            <Button
              variant="ghost"
              onClick={() => transitionTo('plan_select')}
            >
              重新选方案
            </Button>
            <Button
              variant="ghost"
              onClick={() => setRejectStep('input')}
            >
              不喜欢，重新规划
            </Button>
            <Button
              variant="secondary"
              onClick={() => transitionTo('plan_select')}
            >
              调整行程
            </Button>
            <Button
              variant="primary"
              onClick={() => transitionTo('sharing')}
            >
              分享同行
            </Button>
            <Button
              variant="secondary"
              onClick={() => transitionTo('execution_confirm')}
            >
              确认出发
            </Button>
          </div>
        ) : (
          <div>
            <h3 className="text-base font-bold text-ink mb-1">告诉我你想要什么方向（可选）</h3>
            <p className="text-sm text-muted mb-3">不填也可以直接提交，Agent 会重新规划</p>
            <textarea
              value={rejectFeedback}
              onChange={(e) => setRejectFeedback(e.target.value)}
              placeholder="例如：换个户外活动的、近一点的、预算再低一些…"
              rows={2}
              className="w-full bg-card-bg border border-line rounded-xl px-4 py-3 text-sm text-ink placeholder:text-muted resize-none focus:outline-none focus:border-clay-orange mb-3"
            />
            <div className="flex gap-3 justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setRejectStep('idle');
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
                  setRejectStep('idle');
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