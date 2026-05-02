'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';

interface VoteOption {
  id: string;
  label: string;
  count: number;
  percentage: number;
}

interface VotePanelProps {
  options?: VoteOption[];
  onVote?: (optionId: string) => Promise<void>;
  selectedVote?: string;
}

const DEFAULT_OPTIONS: VoteOption[] = [
  { id: 'plan_a', label: '方案1：公园慢走线', count: 2, percentage: 40 },
  { id: 'plan_b', label: '方案2：街区咖啡线', count: 1, percentage: 20 },
  { id: 'plan_c', label: '方案3：博物馆亲子线', count: 2, percentage: 40 },
];

export const VotePanel: React.FC<VotePanelProps> = ({
  options = DEFAULT_OPTIONS,
  onVote,
  selectedVote
}) => {
  const [voting, setVoting] = useState<string | null>(null);

  const handleVote = async (optionId: string) => {
    if (voting) return;

    try {
      setVoting(optionId);
      if (onVote) {
        await onVote(optionId);
      }
    } catch (error) {
      console.error('Failed to vote:', error);
    } finally {
      setVoting(null);
    }
  };

  return (
    <div className="card-paper p-6">
      <h3 className="text-sm font-bold text-ink mb-4">你觉得这条路线怎么样？</h3>

      <div className="space-y-3 mb-4">
        {options.map((option) => {
          const isSelected = selectedVote === option.id;
          const isVoting = voting === option.id;

          return (
            <div
              key={option.id}
              className={cn(
                'relative',
                isSelected && 'ring-2 ring-clay-orange rounded-xl'
              )}
            >
              {/* 选项标签 */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-ink">{option.label}</span>
                <span className="text-xs text-muted">{option.count} 票 ({option.percentage}%)</span>
              </div>

              {/* 进度条 */}
              <div className="h-2 bg-card-soft rounded-full overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-500',
                    isSelected ? 'bg-clay-orange' : 'bg-pine-green'
                  )}
                  style={{ width: `${option.percentage}%` }}
                />
              </div>

              {/* 投票按钮 */}
              {!selectedVote && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full mt-2"
                  onClick={() => handleVote(option.id)}
                  disabled={!!voting}
                  loading={isVoting}
                >
                  {isVoting ? '投票中...' : '投一票'}
                </Button>
              )}

              {/* 已投票标记 */}
              {isSelected && (
                <div className="absolute top-2 right-2">
                  <span className="chip selected">已投</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 总票数 */}
      <div className="text-xs text-muted text-center">
        总共 {options.reduce((sum, opt) => sum + opt.count, 0)} 人参与投票
      </div>
    </div>
  );
};