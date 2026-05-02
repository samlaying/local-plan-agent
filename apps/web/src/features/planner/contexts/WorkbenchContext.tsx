'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react';
import type { ItineraryPlan, TripMapSnapshot, UserIntent } from '@/types/planning';

// 状态机类型定义
export type WorkbenchState =
  | 'input'
  | 'generating'
  | 'plan_select'
  | 'plan_detail'
  | 'sharing'
  | 'execution_confirm'
  | 'execution_done';

// 状态流转规则
const STATE_TRANSITIONS: Record<WorkbenchState, WorkbenchState[]> = {
  input: ['generating'],
  generating: ['plan_select', 'input'],
  plan_select: ['plan_detail', 'input'],
  plan_detail: ['sharing', 'plan_select'],
  sharing: ['execution_confirm', 'plan_detail'],
  execution_confirm: ['execution_done', 'sharing'],
  execution_done: ['input'],
};

// Context 数据结构
interface WorkbenchContextType {
  // 当前状态
  currentState: WorkbenchState;

  // 用户输入数据
  userIntent: string;
  setUserIntent: (intent: string) => void;

  // 计划数据
  plans: ItineraryPlan[];
  setPlans: (plans: ItineraryPlan[]) => void;
  selectedPlan: ItineraryPlan | null;
  setSelectedPlan: (plan: ItineraryPlan) => void;

  // 地图数据
  tripMap: TripMapSnapshot | null;
  setTripMap: (map: TripMapSnapshot) => void;

  // 协作数据
  shareToken: string | null;
  setShareToken: (token: string) => void;

  // Tab状态
  activeTab: string;
  setActiveTab: (tab: string) => void;

  // 状态控制方法
  transitionTo: (newState: WorkbenchState) => boolean;
  canTransitionTo: (newState: WorkbenchState) => boolean;
  reset: () => void;

  // UI 状态
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;
}

// 创建 Context
const WorkbenchContext = createContext<WorkbenchContextType | undefined>(undefined);

// Provider Props
interface WorkbenchProviderProps {
  children: ReactNode;
}

// Provider 组件
export const WorkbenchProvider: React.FC<WorkbenchProviderProps> = ({ children }) => {
  // 核心状态
  const [currentState, setCurrentState] = useState<WorkbenchState>('input');

  // 用户输入
  const [userIntent, setUserIntent] = useState<string>('');

  // 计划数据
  const [plans, setPlans] = useState<ItineraryPlan[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<ItineraryPlan | null>(null);

  // 地图数据
  const [tripMap, setTripMap] = useState<TripMapSnapshot | null>(null);

  // 协作数据
  const [shareToken, setShareToken] = useState<string | null>(null);

  // Tab状态
  const [activeTab, setActiveTab] = useState<string>('overview');

  // UI 状态
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // 状态转换方法
  const transitionTo = useCallback((newState: WorkbenchState): boolean => {
    // 检查是否可以转换到新状态
    if (!canTransitionTo(newState)) {
      console.warn(`Cannot transition from ${currentState} to ${newState}`);
      return false;
    }

    setCurrentState(newState);

    // 当进入 plan_detail 状态时，重置 tab 为 'overview'
    if (newState === 'plan_detail') {
      setActiveTab('overview');
    }

    return true;
  }, [currentState, setActiveTab]);

  // 检查状态转换是否合法
  const canTransitionTo = useCallback((newState: WorkbenchState): boolean => {
    return STATE_TRANSITIONS[currentState].includes(newState);
  }, [currentState]);

  // 重置状态
  const reset = useCallback(() => {
    setCurrentState('input');
    setUserIntent('');
    setPlans([]);
    setSelectedPlan(null);
    setTripMap(null);
    setShareToken(null);
    setIsLoading(false);
    setError(null);
  }, []);

  const value: WorkbenchContextType = {
    currentState,
    userIntent,
    setUserIntent,
    plans,
    setPlans,
    selectedPlan,
    setSelectedPlan,
    tripMap,
    setTripMap,
    shareToken,
    setShareToken,
    activeTab,
    setActiveTab,
    transitionTo,
    canTransitionTo,
    reset,
    isLoading,
    setIsLoading,
    error,
    setError,
  };

  return (
    <WorkbenchContext.Provider value={value}>
      {children}
    </WorkbenchContext.Provider>
  );
};

// Hook 来使用 Context
export const useWorkbench = (): WorkbenchContextType => {
  const context = useContext(WorkbenchContext);
  if (context === undefined) {
    throw new Error('useWorkbench must be used within a WorkbenchProvider');
  }
  return context;
};

// 辅助函数：获取状态显示信息
export const getStateInfo = (state: WorkbenchState) => {
  const stateInfoMap = {
    input: {
      title: '输入需求',
      description: '告诉我你的想法',
      stepNumber: 1,
    },
    generating: {
      title: '生成路线',
      description: 'Agent 正在理解你的偏好',
      stepNumber: 2,
    },
    plan_select: {
      title: '选择方案',
      description: '今日三条路',
      stepNumber: 3,
    },
    plan_detail: {
      title: '路书详情',
      description: '查看完整路线',
      stepNumber: 4,
    },
    sharing: {
      title: '分享同行',
      description: '邀请家人或朋友',
      stepNumber: 5,
    },
    execution_confirm: {
      title: '出发确认',
      description: '确认最终信息',
      stepNumber: 6,
    },
    execution_done: {
      title: '安排完成',
      description: '可以出发了',
      stepNumber: 7,
    },
  };

  return stateInfoMap[state];
};