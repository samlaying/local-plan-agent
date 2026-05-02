/**
 * WebSocket client module — pure TypeScript, no React dependency.
 *
 * Manages connection lifecycle, typed message sending/receiving,
 * callback registration per server message type, and exponential-backoff
 * reconnection.
 *
 * Usage:
 *   import { wsClient } from '@/lib/ws-client';
 *   wsClient.connect();
 *   wsClient.on('onTrace', handler);
 *   wsClient.send({ type: 'start', payload: { ... } });
 */

import type {
  ClientMessage,
  ServerMessage,
  ServerMessageCallbacks,
  WsConnectionStatus,
} from '@/types/websocket';

// Default WebSocket URL — override via NEXT_PUBLIC_WS_URL
const DEFAULT_WS_URL = 'ws://localhost:8001/ws/planning';

// Reconnection config
const RECONNECT_BASE_DELAY_MS = 500;
const RECONNECT_MAX_DELAY_MS = 30_000;
const RECONNECT_MAX_ATTEMPTS = 8;

class PlanningWsClient {
  private url: string;
  private socket: WebSocket | null = null;
  private callbacks: ServerMessageCallbacks = {};
  private status: WsConnectionStatus = 'disconnected';
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  /** When true the caller explicitly disconnected — suppress auto-reconnect */
  private intentionalClose = false;

  constructor(url: string) {
    this.url = url;
  }

  // ----------------------------------------------------------
  // Public API
  // ----------------------------------------------------------

  /** Register callbacks for each server message type. */
  on(callbacks: ServerMessageCallbacks): void {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  /** Override a single callback by key. */
  onKey<K extends keyof ServerMessageCallbacks>(
    key: K,
    handler: ServerMessageCallbacks[K]
  ): void {
    this.callbacks[key] = handler;
  }

  /** Remove all callbacks. */
  off(): void {
    this.callbacks = {};
  }

  /** Open the WebSocket connection. Safe to call multiple times — no-ops if already open. */
  connect(): void {
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN ||
        this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    this.intentionalClose = false;
    this._createSocket();
  }

  /** Close the connection permanently (no automatic reconnect). */
  disconnect(): void {
    this.intentionalClose = true;
    this._cancelReconnect();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this._setStatus('disconnected');
  }

  /** Send a typed client message. Throws if not connected. */
  send(message: ClientMessage): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.warn('[WsClient] Cannot send — socket not open', message.type);
      return;
    }
    this.socket.send(JSON.stringify(message));
  }

  get connectionStatus(): WsConnectionStatus {
    return this.status;
  }

  // ----------------------------------------------------------
  // Private helpers
  // ----------------------------------------------------------

  private _createSocket(): void {
    this._setStatus('connecting');

    try {
      const ws = new WebSocket(this.url);
      this.socket = ws;

      ws.onopen = () => {
        this.reconnectAttempts = 0;
        this._setStatus('connected');
      };

      ws.onmessage = (event: MessageEvent) => {
        this._handleMessage(event.data);
      };

      ws.onerror = () => {
        // onerror is always followed by onclose — handle state there
        this._setStatus('error');
      };

      ws.onclose = () => {
        this.socket = null;
        if (!this.intentionalClose) {
          this._scheduleReconnect();
        } else {
          this._setStatus('disconnected');
        }
      };
    } catch (err) {
      console.error('[WsClient] Failed to create WebSocket', err);
      this._setStatus('error');
      this._scheduleReconnect();
    }
  }

  private _handleMessage(raw: string): void {
    let msg: ServerMessage;
    try {
      msg = JSON.parse(raw) as ServerMessage;
    } catch {
      console.error('[WsClient] Received non-JSON message', raw);
      return;
    }

    switch (msg.type) {
      case 'session_ready':
        this.callbacks.onSessionReady?.(msg.data);
        break;
      case 'trace':
        this.callbacks.onTrace?.(msg.data);
        break;
      case 'ask':
        this.callbacks.onAsk?.(msg.data);
        break;
      case 'plans_ready':
        this.callbacks.onPlansReady?.(msg.data);
        break;
      case 'execution_preview':
        this.callbacks.onExecutionPreview?.(msg.data);
        break;
      case 'execution_result':
        this.callbacks.onExecutionResult?.(msg.data);
        break;
      case 'done':
        this.callbacks.onDone?.();
        break;
      case 'error':
        this.callbacks.onError?.(msg.data);
        break;
      default:
        console.warn('[WsClient] Unknown message type', (msg as { type: string }).type);
    }
  }

  private _setStatus(status: WsConnectionStatus): void {
    if (this.status === status) return;
    this.status = status;
    this.callbacks.onConnectionStatusChange?.(status);
  }

  private _scheduleReconnect(): void {
    if (this.reconnectAttempts >= RECONNECT_MAX_ATTEMPTS) {
      console.error('[WsClient] Max reconnect attempts reached');
      this._setStatus('error');
      return;
    }

    const delay = Math.min(
      RECONNECT_BASE_DELAY_MS * Math.pow(2, this.reconnectAttempts),
      RECONNECT_MAX_DELAY_MS
    );

    this.reconnectAttempts += 1;
    console.info(`[WsClient] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    this._setStatus('connecting');
    this.reconnectTimer = setTimeout(() => {
      this._createSocket();
    }, delay);
  }

  private _cancelReconnect(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

// ============================================================
// Singleton — one shared connection for the whole app session
// ============================================================

const WS_URL =
  (typeof process !== 'undefined' &&
    process.env.NEXT_PUBLIC_WS_URL) ||
  DEFAULT_WS_URL;

export const wsClient = new PlanningWsClient(WS_URL);
