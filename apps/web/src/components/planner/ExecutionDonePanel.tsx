'use client';

import React from 'react';
import { useWorkbench } from '@/features/planner/contexts/WorkbenchContext';
import { Button } from '@/components/ui';
import { CheckCircleIcon } from '../icons';

export const ExecutionDonePanel: React.FC = () => {
  const { selectedPlan, reset, tripMap } = useWorkbench();

  const handleOpenMemory = () => {
    if (tripMap?.id) {
      window.location.href = `/memory/${tripMap.id}`;
    }
  };

  return (
    <div className="max-w-4xl mx-auto text-center">
      {/* 成功图标 */}
      <div className="mb-8">
        <div className="w-20 h-20 rounded-full bg-pine-green/10 flex items-center justify-center mx-auto">
          <CheckCircleIcon className="w-10 h-10 text-pine-green" />
        </div>
      </div>

      {/* 成功标题 */}
      <h1 className="text-3xl font-bold text-ink mb-4">安排好了</h1>

      {/* 完成清单 */}
      <div className="space-y-4 mb-8 max-w-lg mx-auto">
        <div className="flex items-center gap-3 text-left">
          <CheckCircleIcon className="w-5 h-5 text-pine-green flex-shrink-0" />
          <span className="text-ink">半日路线已确认</span>
        </div>
        <div className="flex items-center gap-3 text-left">
          <CheckCircleIcon className="w-5 h-5 text-pine-green flex-shrink-0" />
          <span className="text-ink">地图已生成</span>
        </div>
        <div className="flex items-center gap-3 text-left">
          <CheckCircleIcon className="w-5 h-5 text-pine-green flex-shrink-0" />
          <span className="text-ink">同行信息已记录</span>
        </div>
        <div className="flex items-center gap-3 text-left">
          <CheckCircleIcon className="w-5 h-5 text-pine-green flex-shrink-0" />
          <span className="text-ink">可以开始记录今日足迹</span>
        </div>
      </div>

      {/* 路线摘要 */}
      <div className="card-paper p-6 mb-8 text-left">
        <h3 className="text-lg font-bold text-ink mb-4">今日路线摘要</h3>
        <div className="text-muted leading-relaxed">
          14:00 出发 → 14:40 公园 → 15:30 咖啡 → 16:40 返回
        </div>
      </div>

      {/* 可发送消息 */}
      <div className="card-paper p-6 mb-8">
        <h3 className="text-sm font-bold text-ink mb-3">可发送消息：</h3>
        <div className="bg-card-soft rounded-xl p-4 text-sm text-ink italic">
          "路线定好了，今天下午 2 点出发，先去公园散步，然后到街区咖啡休息，最后参观自然博物馆。全程约 3.5 小时，轻松舒适。"
        </div>
        <Button
          variant="secondary"
          className="mt-3"
          onClick={() => {
            navigator.clipboard.writeText('路线定好了，今天下午 2 点出发，先去公园散步，然后到街区咖啡休息，最后参观自然博物馆。全程约 3.5 小时，轻松舒适。');
          }}
        >
          复制消息
        </Button>
      </div>

      {/* 操作按钮 */}
      <div className="flex flex-wrap gap-3 justify-center">
        <Button
          variant="secondary"
          onClick={() => window.location.reload()}
        >
          再来一条新路线
        </Button>
        <Button
          variant="primary"
          onClick={handleOpenMemory}
        >
          打开今日足迹
        </Button>
      </div>

      {/* 底部文案 */}
      <div className="mt-12 text-sm text-muted">
        <p>城市很大，半日刚好。我们帮你记下这一段刚刚好的时光。</p>
      </div>
    </div>
  );
};