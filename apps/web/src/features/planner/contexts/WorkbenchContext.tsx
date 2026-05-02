'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode, useEffect, useRef } from 'react';
import type { ItineraryPlan, TripMapSnapshot, ExecutableAction } from '@/types/planning';
import type { WsConnectionStatus, WsTraceData, WsAskData } from '@/types/websocket';
import { wsClient } from '@/lib/ws-client';

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

  // ---- WebSocket 新增状态 ----
  sessionId: string | null;
  wsStatus: WsConnectionStatus;
  traceEvents: WsTraceData[];
  askQuestion: WsAskData | null;
  executionActions: ExecutableAction[];

  // ---- WebSocket 操作方法 ----
  startPlanning: (query: string, location: { city: string; address: string; lat: number; lng: number }) => void;
  sendUserReply: (text: string) => void;
  confirmPlan: (planId: string) => void;
  rejectPlan: (feedback: string) => void;
  confirmExecution: (planId: string) => void;
  cancelPlanning: () => void;
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

  // ---- WebSocket 新增状态 ----
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<WsConnectionStatus>('disconnected');
  const [traceEvents, setTraceEvents] = useState<WsTraceData[]>([]);
  const [askQuestion, setAskQuestion] = useState<WsAskData | null>(null);
  const [executionActions, setExecutionActions] = useState<ExecutableAction[]>([]);

  // Ref to hold latest currentState for use inside stable WS callbacks
  const currentStateRef = useRef<WorkbenchState>(currentState);
  useEffect(() => {
    currentStateRef.current = currentState;
  }, [currentState]);

  // ----------------------------------------------------------
  // 状态转换方法（必须在 WebSocket effect 之前定义）
  // ----------------------------------------------------------

  const canTransitionTo = useCallback((newState: WorkbenchState): boolean => {
    return STATE_TRANSITIONS[currentStateRef.current].includes(newState);
  }, []);

  const transitionTo = useCallback((newState: WorkbenchState): boolean => {
    if (!STATE_TRANSITIONS[currentStateRef.current].includes(newState)) {
      console.warn(`Cannot transition from ${currentStateRef.current} to ${newState}`);
      return false;
    }
    setCurrentState(newState);
    if (newState === 'plan_detail') {
      setActiveTab('overview');
    }
    return true;
  }, []);

  // ----------------------------------------------------------
  // 重置
  // ----------------------------------------------------------

  const reset = useCallback(() => {
    setCurrentState('input');
    setUserIntent('');
    setPlans([]);
    setSelectedPlan(null);
    setTripMap(null);
    setShareToken(null);
    setIsLoading(false);
    setError(null);
    setSessionId(null);
    setTraceEvents([]);
    setAskQuestion(null);
    setExecutionActions([]);
  }, []);

  // ----------------------------------------------------------
  // WebSocket 初始化 & 回调注册
  // ----------------------------------------------------------

  useEffect(() => {
    wsClient.on({
      onConnectionStatusChange: (status) => {
        setWsStatus(status);
      },

      onSessionReady: ({ session_id }) => {
        setSessionId(session_id);
      },

      onTrace: (data) => {
        setTraceEvents((prev) => [...prev, data]);
      },

      onAsk: (data) => {
        setAskQuestion(data);
      },

      onPlansReady: ({ plans: incoming }) => {
        setPlans(incoming);
        // Transition to plan_select — ref-based check avoids stale closure
        if (STATE_TRANSITIONS[currentStateRef.current].includes('plan_select')) {
          setCurrentState('plan_select');
        }
        setIsLoading(false);
      },

      onExecutionPreview: ({ actions }) => {
        setExecutionActions(actions);
      },

      onExecutionResult: ({ results }) => {
        setExecutionActions(results);
        if (STATE_TRANSITIONS[currentStateRef.current].includes('execution_done')) {
          setCurrentState('execution_done');
        }
      },

      onDone: () => {
        setIsLoading(false);
      },

      onError: ({ message: msg, recoverable }) => {
        setError(msg);
        setIsLoading(false);
        if (!recoverable) {
          // Fall back to input so user can retry
          setCurrentState('input');
        }
      },
    });

    wsClient.connect();

    return () => {
      // On unmount: disconnect and clear callbacks
      wsClient.disconnect();
      wsClient.off();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps — intentionally runs once

  // ----------------------------------------------------------
  // WebSocket 操作方法
  // ----------------------------------------------------------

  const startPlanning = useCallback(
    (
      query: string,
      location: { city: string; address: string; lat: number; lng: number }
    ) => {
      setUserIntent(query);
      setError(null);
      setTraceEvents([]);
      setAskQuestion(null);
      setPlans([]);
      setIsLoading(true);

      if (STATE_TRANSITIONS[currentStateRef.current].includes('generating')) {
        setCurrentState('generating');
      }

      wsClient.send({ type: 'start', payload: { query, location } });
    },
    []
  );

  const sendUserReply = useCallback((text: string) => {
    setAskQuestion(null);
    wsClient.send({ type: 'user_reply', payload: { text } });
  }, []);

  const confirmPlan = useCallback((planId: string) => {
    wsClient.send({ type: 'plan_confirmed', payload: { plan_id: planId } });
  }, []);

  const rejectPlan = useCallback((feedback: string) => {
    wsClient.send({ type: 'plan_rejected', payload: { feedback } });
  }, []);

  const confirmExecution = useCallback((planId: string) => {
    setIsLoading(true);
    wsClient.send({ type: 'execution_confirmed', payload: { plan_id: planId } });
  }, []);

  const cancelPlanning = useCallback(() => {
    wsClient.send({ type: 'cancel' });
    setIsLoading(false);
    setCurrentState('input');
  }, []);

  // ----------------------------------------------------------
  // Context value
  // ----------------------------------------------------------

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
    // WebSocket
    sessionId,
    wsStatus,
    traceEvents,
    askQuestion,
    executionActions,
    startPlanning,
    sendUserReply,
    confirmPlan,
    rejectPlan,
    confirmExecution,
    cancelPlanning,
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
