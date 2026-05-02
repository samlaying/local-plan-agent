'use client';

import React from 'react';
import type { ItineraryPlan } from '@/types/planning';
import { Card } from '@/components/ui';
import { Button } from '@/components/ui';
import { StatusBadge } from '@/components/ui';
import { cn } from '@/lib/utils';

export type PlanCardState = 'default' | 'hover' | 'selected' | 'risk_high' | 'disabled';

interface PlanCardProps {
  plan: ItineraryPlan;
  state?: PlanCardState;
  onSelect?: () => void;
  onViewDetails?: () => void;
}

export const PlanCard: React.FC<PlanCardProps> = ({
  plan,
  state = 'default',
  onSelect,
  onViewDetails
}) => {
  const isSelected = state === 'selected';
  const isDisabled = state === 'disabled';

  return (
    <Card
      className={cn(
        'relative transition-all duration-200',
        isSelected && 'border-2 border-clay-orange',
        isDisabled && 'opacity-45 cursor-not-allowed',
        !isDisabled && 'hover:shadow-paper-hover hover:-translate-y-1'
      )}
      onClick={!isDisabled ? onViewDetails : undefined}
    >

      {/* 选中标记 */}
      {isSelected && (
        <div className="absolute top-4 right-4 w-6 h-6 rounded-full bg-clay-orange flex items-center justify-center">
          <span className="text-white text-xs">✓</span>
        </div>
      )}

      {/* 风险警告 */}
      {plan.riskLevel === 'high' && !isSelected && (
        <div className="absolute top-4 left-4">
          <span className="chip" style={{ backgroundColor: '#FEF3C7', color: '#D97706', border: 'none' }}>
            需注意排队
          </span>
        </div>
      )}

      {/* 方案编号 */}
      <div className="text-xs text-muted mb-2">方案 {plan.id.slice(-1)}</div>

      {/* 标题 */}
      <h3 className="text-lg font-bold text-ink mb-3">{plan.title}</h3>

      {/* 预览图片占位 */}
      <div className="w-full h-32 rounded-xl bg-gradient-to-br from-clay-orange/20 to-pine-green/20 mb-4 flex items-center justify-center">
        <span className="text-4xl">🗺️</span>
      </div>

      {/* 关键信息 */}
      <div className="space-y-2 mb-4 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-muted">时长</span>
          <span className="text-ink font-medium">
            {Math.floor(plan.totalDurationMinutes / 60)}小时{plan.totalDurationMinutes % 60}分钟
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted">预算</span>
          <span className="text-ink font-medium">
            ¥{plan.estimatedCost.min} - ¥{plan.estimatedCost.max}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted">风险</span>
          <StatusBadge
            status={plan.riskLevel === 'high' ? 'danger' : plan.riskLevel === 'medium' ? 'warning' : 'success'}
          >
            {plan.riskLevel === 'high' ? '高' : plan.riskLevel === 'medium' ? '中' : '低'}
          </StatusBadge>
        </div>
      </div>

      {/* 评分 */}
      <div className="flex items-center gap-1 mb-4">
        {[...Array(5)].map((_, i) => (
          <span
            key={i}
            className={cn(
              'text-lg',
              i < Math.floor(plan.score / 20) ? 'text-clay-orange' : 'text-gray-300'
            )}
          >
            ★
          </span>
        ))}
        <span className="text-sm text-muted ml-2">{plan.score}/100</span>
      </div>

      {/* 亮点标签 */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {plan.fitSummary.slice(0, 3).map((fit, index) => (
          <span key={index} className="text-xs bg-card-soft text-muted px-2 py-1 rounded-full">
            {fit}
          </span>
        ))}
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-2">
        {!isSelected ? (
          <>
            <Button
              variant="secondary"
              size="sm"
              className="flex-1"
              onClick={(e) => {
                e.stopPropagation();
                onViewDetails?.();
              }}
            >
              查看详情
            </Button>
            <Button
              variant="primary"
              size="sm"
              className="flex-1"
              onClick={(e) => {
                e.stopPropagation();
                onSelect?.();
              }}
            >
              选择此方案
            </Button>
          </>
        ) : (
          <Button
            variant="primary"
            size="sm"
            className="w-full"
            disabled
          >
            已选择此方案
          </Button>
        )}
      </div>

      {/* 不可用状态 */}
      {isDisabled && (
        <div className="absolute inset-0 bg-white/60 flex items-center justify-center rounded-3xl">
          <span className="text-sm text-muted">当前条件下不太适合</span>
        </div>
      )}
    </Card>
  );
};