'use client';

import React from 'react';
import { WorkbenchState, getStateInfo } from '@/features/planner/contexts/WorkbenchContext';
import { useWorkbench } from '@/features/planner/contexts/WorkbenchContext';
import { cn } from '@/lib/utils';

interface RightContextPanelProps {
  currentState: WorkbenchState;
}

export const RightContextPanel: React.FC<RightContextPanelProps> = ({ currentState }) => {
  const { userIntent, selectedPlan, tripMap } = useWorkbench();

  // 根据当前状态显示不同的上下文内容
  const renderContextContent = () => {
    switch (currentState) {
      case 'input':
        return (
          <div className="space-y-6">
            {/* 当前你可以做 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">当前你可以做</h3>
              <ul className="space-y-2 text-sm text-muted">
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  输入你的想法
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  补充更多信息
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  导入收藏灵感
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  查看输入帮助
                </li>
              </ul>
            </div>

            {/* Agent 正在做 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">Agent 正在做</h3>
              <div className="text-sm text-muted">
                <p className="mb-2">等待你的输入</p>
                <p className="text-xs leading-relaxed">
                  我在这里等你告诉我想法～等你提交后，我会为你生成合适的半日路线建议！
                </p>
              </div>
            </div>
          </div>
        );

      case 'generating':
        return (
          <div className="space-y-6">
            {/* 当前步骤 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">当前步骤</h3>
              <div className="text-sm">
                <div className="text-clay-orange font-medium mb-1">2/6 生成路线</div>
                <div className="text-muted">Agent 正在理解你的偏好</div>
              </div>
            </div>

            {/* Agent 正在做 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">Agent 正在做</h3>
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-pine-green"></div>
                  <span className="text-muted">理解你的偏好</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-clay-orange animate-pulse"></div>
                  <span className="text-ink font-medium">匹配附近地点</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-gray-300"></div>
                  <span className="text-muted">估算路线时间</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-gray-300"></div>
                  <span className="text-muted">生成路线方案</span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'plan_select':
        return (
          <div className="space-y-6">
            {/* 你可以做什么 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">你可以做什么</h3>
              <ul className="space-y-2 text-sm text-muted">
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  查看三个方案
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  选择喜欢的方案
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  查看方案详情
                </li>
              </ul>
            </div>

            {/* 方案状态 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">方案状态</h3>
              <div className="text-sm text-muted">
                已生成 3 个方案，请选择你最喜欢的路线。
              </div>
            </div>
          </div>
        );

      case 'plan_detail':
        return (
          <div className="space-y-6">
            {/* 当前计划状态 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">当前计划状态</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted">出发时间</span>
                  <span className="text-ink">14:00</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">出发地点</span>
                  <span className="text-ink">徐家汇</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">同行小札</span>
                  <span className="text-ink">2 人</span>
                </div>
              </div>
            </div>

            {/* Agent 贴心提醒 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">Agent 贴心提醒</h3>
              <div className="text-sm text-muted leading-relaxed">
                这条路线以室内博物馆为主，适合亲子互动与学习。建议预留充足时间给孩子探索和休息。
              </div>
            </div>

            {/* 出行小贴士 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">出行小贴士</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted">今日天气</span>
                  <span className="text-ink">23°C 晴</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">步行强度</span>
                  <span className="text-ink">轻度</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">亲子友好</span>
                  <span className="text-pine-green">★★★★★</span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'sharing':
        return (
          <div className="space-y-6">
            {/* 你可以做 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">你可以做</h3>
              <ul className="space-y-2 text-sm text-muted">
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  复制链接
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  邀请同行
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  处理反馈
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  继续确认
                </li>
              </ul>
            </div>

            {/* Agent 正在做 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">Agent 正在做</h3>
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-pine-green"></div>
                  <span className="text-muted">同步反馈</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-gray-300"></div>
                  <span className="text-muted">调整计划建议</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-gray-300"></div>
                  <span className="text-muted">检查冲突</span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'execution_confirm':
        return (
          <div className="space-y-6">
            {/* 你可以做 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">你可以做</h3>
              <ul className="space-y-2 text-sm text-muted">
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  确认出发
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  调整出发时间
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  邀请同行好友
                </li>
              </ul>
            </div>

            {/* Agent 正在做 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">Agent 正在做</h3>
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-pine-green"></div>
                  <span className="text-muted">检查路线信息</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-pine-green"></div>
                  <span className="text-muted">检查天气情况</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-clay-orange animate-pulse"></div>
                  <span className="text-ink font-medium">准备行程记录</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-gray-300"></div>
                  <span className="text-muted">待出发确认</span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'execution_done':
        return (
          <div className="space-y-6">
            {/* 本次行程完成 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">本次行程完成</h3>
              <div className="text-sm text-muted leading-relaxed">
                半日路线已确认，可以开始记录今日足迹。
              </div>
            </div>

            {/* 可操作项 */}
            <div className="card-paper p-4">
              <h3 className="text-sm font-bold text-ink mb-3">可操作项</h3>
              <ul className="space-y-2 text-sm text-muted">
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  打开今日足迹
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  保存游笺
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-clay-orange"></span>
                  分享回顾
                </li>
              </ul>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <aside className="fixed right-0 top-[72px] bottom-0 w-[300px] bg-card-bg border-l border-line p-6 overflow-y-auto">
      {renderContextContent()}
    </aside>
  );
};