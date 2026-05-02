import type { ExecutableAction, ItineraryPlan } from './planning';

// ============================================================
// Client → Server message types
// ============================================================

export interface WsStartPayload {
  query: string;
  location: {
    city: string;
    address: string;
    lat: number;
    lng: number;
  };
}

export interface WsUserReplyPayload {
  text: string;
}

export interface WsPlanConfirmedPayload {
  plan_id: string;
}

export interface WsPlanRejectedPayload {
  feedback: string;
}

export interface WsExecutionConfirmedPayload {
  plan_id: string;
}

// cancel has no extra payload

export type ClientMessage =
  | { type: 'start'; payload: WsStartPayload }
  | { type: 'user_reply'; payload: WsUserReplyPayload }
  | { type: 'plan_confirmed'; payload: WsPlanConfirmedPayload }
  | { type: 'plan_rejected'; payload: WsPlanRejectedPayload }
  | { type: 'execution_confirmed'; payload: WsExecutionConfirmedPayload }
  | { type: 'cancel' };

// ============================================================
// Server → Client message types
// ============================================================

export interface WsSessionReadyData {
  session_id: string;
}

export type TraceStatus = 'running' | 'completed' | 'failed';

export interface WsTraceData {
  agent: string;
  status: TraceStatus;
  message: string;
}

export interface WsAskData {
  question: string;
  round: number;
}

export interface WsPlansReadyData {
  plans: ItineraryPlan[];
}

export interface WsExecutionPreviewData {
  actions: ExecutableAction[];
}

export interface WsExecutionResultData {
  results: ExecutableAction[];
  all_success: boolean;
}

export interface WsErrorData {
  message: string;
  recoverable: boolean;
}

export type ServerMessage =
  | { type: 'session_ready'; data: WsSessionReadyData }
  | { type: 'trace'; data: WsTraceData }
  | { type: 'ask'; data: WsAskData }
  | { type: 'plans_ready'; data: WsPlansReadyData }
  | { type: 'execution_preview'; data: WsExecutionPreviewData }
  | { type: 'execution_result'; data: WsExecutionResultData }
  | { type: 'done' }
  | { type: 'error'; data: WsErrorData };

// ============================================================
// Connection state
// ============================================================

export type WsConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

// ============================================================
// Callback registry type (for the WS client)
// ============================================================

export type ServerMessageCallbacks = {
  onSessionReady?: (data: WsSessionReadyData) => void;
  onTrace?: (data: WsTraceData) => void;
  onAsk?: (data: WsAskData) => void;
  onPlansReady?: (data: WsPlansReadyData) => void;
  onExecutionPreview?: (data: WsExecutionPreviewData) => void;
  onExecutionResult?: (data: WsExecutionResultData) => void;
  onDone?: () => void;
  onError?: (data: WsErrorData) => void;
  onConnectionStatusChange?: (status: WsConnectionStatus) => void;
};
