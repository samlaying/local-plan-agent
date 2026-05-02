'use client';

import React, { useState, useCallback } from 'react';
import { useWorkbench } from '@/features/planner/contexts/WorkbenchContext';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';

export type InputBoxState = 'empty' | 'typing' | 'submitting' | 'error';

interface GoalInputCardProps {
  onSubmit?: (intent: string) => Promise<void>;
}

export const GoalInputCard: React.FC<GoalInputCardProps> = ({ onSubmit }) => {
  const { userIntent, setUserIntent, transitionTo, setIsLoading, setError } = useWorkbench();
  const [localInput, setLocalInput] = useState('');
  const [inputState, setInputState] = useState<InputBoxState>('empty');

  // 示例想法
  const exampleIdeas = [
    '今天下午想和老婆孩子出去玩几个小时，别离家太远',
    '想找咖啡馆聊聊天，放松一下',
    '带爸妈逛逛，找个不太累的地方',
  ];

  // 处理输入变化
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    if (value.length <= 200) {
      setLocalInput(value);
      setInputState(value.length > 0 ? 'typing' : 'empty');
    }
  };

  // 处理提交
  const handleSubmit = async () => {
    if (localInput.trim().length < 5) {
      setInputState('error');
      setError('再多写一点点，我才能帮你安排得更合适。');
      return;
    }

    try {
      setInputState('submitting');
      setIsLoading(true);

      // 调用提交回调
      if (onSubmit) {
        await onSubmit(localInput);
      } else {
        // 默认行为：更新用户意图并转换状态
        setUserIntent(localInput);
        transitionTo('generating');
      }

      setInputState('typing');
    } catch (error) {
      setInputState('error');
      setError(error instanceof Error ? error.message : '提交失败，请重试。');
    } finally {
      setIsLoading(false);
    }
  };

  // 使用示例想法
  const handleUseExample = (example: string) => {
    setLocalInput(example);
    setInputState('typing');
    setUserIntent(example);
  };

  const isSubmitDisabled = localInput.trim().length < 5 || inputState === 'submitting';
  const charCount = localInput.length;

  return (
    <div className="card-paper p-8 max-w-3xl mx-auto">
      {/* 标题 */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-ink mb-2">告诉我你的想法</h2>
        <p className="text-muted text-sm">我会帮你生成一张完美的半日路书</p>
      </div>

      {/* 输入框 */}
      <div className="mb-4">
        <div
          className={cn(
            'relative bg-card-bg border-2 rounded-3xl p-4 transition-all duration-200',
            inputState === 'error' && 'border-danger',
            inputState !== 'error' && 'border-line',
            inputState === 'typing' && 'border-clay-orange',
            inputState === 'submitting' && 'opacity-60 pointer-events-none'
          )}
        >
          <textarea
            value={localInput}
            onChange={handleInputChange}
            placeholder="例如：今天下午想和老婆孩子出去玩几个小时，别离家太远"
            className={cn(
              'w-full min-h-[120px] bg-transparent text-ink placeholder:text-muted resize-none focus:outline-none',
              inputState === 'submitting' && 'cursor-not-allowed'
            )}
            disabled={inputState === 'submitting'}
          />

          {/* 底部工具栏 */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-line">
            {/* 字数统计 */}
            <div className="text-sm text-muted">
              字数：{charCount}/200
              {charCount > 0 && (
                <button
                  onClick={() => {
                    setLocalInput('');
                    setInputState('empty');
                  }}
                  className="ml-4 text-clay-orange hover:underline"
                >
                  清空
                </button>
              )}
            </div>

            {/* 发送按钮 */}
            <Button
              onClick={handleSubmit}
              disabled={isSubmitDisabled}
              loading={inputState === 'submitting'}
              size="md"
            >
              {inputState === 'submitting' ? '正在把你的想法写成路书...' : '发送需求'}
            </Button>
          </div>
        </div>

        {/* 错误提示 */}
        {inputState === 'error' && (
          <div className="mt-3 text-sm text-danger">
            再多写一点点，我才能帮你安排得更合适。
          </div>
        )}
      </div>

      {/* 辅助选项 */}
      <div className="mb-6">
        <p className="text-sm text-muted mb-3">试试添加这些信息，帮助 Agent 更懂你：</p>
        <div className="flex flex-wrap gap-2">
          <button className="chip">时间</button>
          <button className="chip">偏好</button>
          <button className="chip">约束</button>
          <button className="chip">添加说明 +</button>
        </div>
      </div>

      {/* 示例想法 */}
      <div>
        <p className="text-sm text-muted mb-3">示例想法：</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {exampleIdeas.map((idea, index) => (
            <button
              key={index}
              onClick={() => handleUseExample(idea)}
              className="card-paper p-4 text-left hover:shadow-paper-hover transition-all duration-200"
            >
              <p className="text-sm text-ink line-clamp-3">{idea}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};