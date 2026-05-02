'use client';

import React, { useState } from 'react';
import { useWorkbench } from '@/features/planner/contexts/WorkbenchContext';
import { Button } from '@/components/ui';
import { CheckCircleIcon, ClockIcon, UsersIcon } from '../icons';
import { cn } from '@/lib/utils';

export const ExecutionConfirmPanel: React.FC = () => {
  const { selectedPlan, transitionTo } = useWorkbench();
  const [checkedItems, setCheckedItems] = useState<string[]>([]);
  const [confirmed, setConfirmed] = useState(false);

  // 确认清单项目
  const checklistItems = [
    {
      id: 'time',
      label: '出发时间',
      value: '今天 14:00 出发',
      status: 'ready',
    },
    {
      id: 'duration',
      label: '预计时长',
      value: '约3.5小时',
      status: 'ready',
    },
    {
      id: 'weather',
      label: '天气提醒',
      value: '23°C 晴',
      status: 'ready',
    },
    {
      id: 'participants',
      label: '同行人数',
      value: '4人',
      status: 'ready',
    },
    {
      id: 'items',
      label: '随身物品建议',
      value: '水、轻便背包、遮阳帽',
      status: 'ready',
    },
  ];

  // 处理确认
  const handleConfirm = async () => {
    try {
      // 前端本地模拟执行
      await new Promise(resolve => setTimeout(resolve, 1500));
      setConfirmed(true);

      // 延迟后转换到完成状态
      setTimeout(() => {
        transitionTo('execution_done');
      }, 1000);
    } catch (error) {
      console.error('Confirmation failed:', error);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* 返回按钮 */}
      <div className="mb-6">
        <button
          onClick={() => transitionTo('plan_detail')}
          className="flex items-center gap-2 text-muted hover:text-ink transition-colors"
        >
          <span>←</span>
          <span>返回上一步</span>
        </button>
      </div>

      {/* 方案摘要卡片 */}
      {selectedPlan && (
        <div className="card-paper p-6 mb-6">
          <div className="flex gap-6">
            <div className="w-32 h-32 rounded-xl bg-gradient-to-br from-clay-orange/20 to-pine-green/20 flex items-center justify-center flex-shrink-0">
              <span className="text-4xl">🗺️</span>
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-ink mb-2">{selectedPlan.title}</h2>
              <div className="flex flex-wrap gap-2 mb-3">
                <span className="chip selected">亲子</span>
                <span className="chip selected">半日</span>
                <span className="chip selected">≤10km</span>
              </div>
              <div className="flex gap-6 text-sm">
                <div>
                  <span className="text-muted">时长：</span>
                  <span className="text-ink font-medium">
                    {Math.floor(selectedPlan.totalDurationMinutes / 60)}h
                    {selectedPlan.totalDurationMinutes % 60}m
                  </span>
                </div>
                <div>
                  <span className="text-muted">距离：</span>
                  <span className="text-ink font-medium">3.2km</span>
                </div>
                <div>
                  <span className="text-muted">评分：</span>
                  <span className="text-ink font-medium">{selectedPlan.score}/100</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 执行确认 */}
      <div className="card-paper p-6 mb-6">
        <h3 className="text-xl font-bold text-ink mb-6 flex items-center gap-2">
          <ClockIcon className="w-5 h-5 text-clay-orange" />
          执行确认
        </h3>

        {/* 出发前确认清单 */}
        <div className="mb-6">
          <div className="text-sm text-muted mb-4">出发前确认清单</div>
          <div className="space-y-3">
            {checklistItems.map((item) => {
              const isChecked = checkedItems.includes(item.id);

              return (
                <div
                  key={item.id}
                  className={cn(
                    'flex items-center justify-between p-4 rounded-xl border transition-all duration-200',
                    isChecked
                      ? 'bg-pine-green/10 border-pine-green'
                      : 'bg-card-bg border-line'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        'w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors',
                        isChecked
                          ? 'bg-pine-green border-pine-green'
                          : 'border-gray-300'
                      )}
                    >
                      {isChecked && <CheckCircleIcon className="w-3 h-3 text-white" />}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-ink">{item.label}</div>
                      <div className="text-xs text-muted">{item.value}</div>
                    </div>
                  </div>
                  <div className="text-xs text-pine-green font-medium">
                    {isChecked ? '✅' : '待确认'}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 当前需要你确认 */}
        <div className="bg-card-soft rounded-xl p-4">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-clay-orange/10 flex items-center justify-center">
              <span className="text-clay-orange text-sm">!</span>
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-bold text-ink mb-2">出发确认（需要你操作）</h4>
              <p className="text-sm text-muted mb-3">
                确认以上信息无误后，点击下方按钮正式出发。
              </p>

              {/* 安全须知复选框 */}
              <label className="flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="mt-1"
                  onChange={(e) => {
                    if (e.target.checked) {
                      setCheckedItems([...checkedItems, 'safety']);
                    } else {
                      setCheckedItems(checkedItems.filter(id => id !== 'safety'));
                    }
                  }}
                />
                <span className="text-sm text-ink">
                  我已阅读并同意出行安全须知
                </span>
              </label>
            </div>
          </div>
        </div>

        {/* 确认按钮 */}
        <div className="flex justify-center mt-6">
          <Button
            variant="primary"
            size="lg"
            onClick={handleConfirm}
            disabled={checkedItems.length < checklistItems.length || confirmed}
            loading={confirmed}
          >
            {confirmed ? '确认中...' : '确认出发'}
          </Button>
        </div>
      </div>

      {/* 执行状态示例 */}
      <div className="card-paper p-6">
        <h3 className="text-sm font-bold text-ink mb-4">执行状态示例</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-3 bg-pine-green/10 border border-pine-green rounded-lg text-center">
            <div className="text-xs text-muted mb-1">成功</div>
            <div className="text-sm text-ink">路线规划完成</div>
          </div>
          <div className="p-3 bg-clay-orange/10 border border-clay-orange rounded-lg text-center">
            <div className="text-xs text-muted mb-1">需确认</div>
            <div className="text-sm text-ink">等待用户确认</div>
          </div>
          <div className="p-3 bg-gray-100 border border-gray-300 rounded-lg text-center">
            <div className="text-xs text-muted mb-1">待处理</div>
            <div className="text-sm text-ink">预约餐厅</div>
          </div>
        </div>
      </div>
    </div>
  );
};