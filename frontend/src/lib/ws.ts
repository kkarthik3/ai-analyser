/**
 * WebSocket client for real-time market data streaming.
 *
 * Features:
 *  - Auto-reconnect with exponential backoff
 *  - Message type routing
 *  - Connection state management
 *  - Ping/pong keepalive
 */

type MessageHandler = (data: unknown) => void;

interface WSOptions {
  maxRetries?: number;
  baseDelay?: number;
  maxDelay?: number;
  pingInterval?: number;
}

export class MarketWebSocket {
  private ws: WebSocket | null = null;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private retryCount = 0;
  private isIntentionalClose = false;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private options: Required<WSOptions>;
  private url: string;

  constructor(options?: WSOptions) {
    this.options = {
      maxRetries: options?.maxRetries ?? 20,
      baseDelay: options?.baseDelay ?? 1000,
      maxDelay: options?.maxDelay ?? 30000,
      pingInterval: options?.pingInterval ?? 25000,
    };

    const wsBase =
      process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
    this.url = `${wsBase}/ws/market`;
  }

  /** Connect to the WebSocket server. */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.isIntentionalClose = false;

    try {
      this.ws = new WebSocket(this.url);
      this.ws.onopen = this.onOpen.bind(this);
      this.ws.onmessage = this.onMessage.bind(this);
      this.ws.onclose = this.onClose.bind(this);
      this.ws.onerror = this.onError.bind(this);
    } catch (err) {
      console.error("[WS] Connection error:", err);
      this.scheduleReconnect();
    }
  }

  /** Disconnect from the WebSocket server. */
  disconnect(): void {
    this.isIntentionalClose = true;
    this.stopPing();
    this.ws?.close();
    this.ws = null;
  }

  /** Subscribe to a specific message type. */
  on(type: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, []);
    }
    this.handlers.get(type)!.push(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.handlers.get(type);
      if (handlers) {
        const idx = handlers.indexOf(handler);
        if (idx !== -1) handlers.splice(idx, 1);
      }
    };
  }

  /** Send a message to the server. */
  send(data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  /** Get current connection state. */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  // ---- Internal handlers ----

  private onOpen(): void {
    console.log("[WS] Connected");
    this.retryCount = 0;
    this.startPing();
    this.emit("connection", { status: "connected" });
  }

  private onMessage(event: MessageEvent): void {
    try {
      const message = JSON.parse(event.data);
      const type = message.type || "unknown";

      // Route to type-specific handlers
      this.emit(type, message.data || message);

      // Also emit to wildcard handlers
      this.emit("*", message);
    } catch (err) {
      console.error("[WS] Parse error:", err);
    }
  }

  private onClose(event: CloseEvent): void {
    console.log(`[WS] Closed (code: ${event.code})`);
    this.stopPing();
    this.emit("connection", { status: "disconnected" });

    if (!this.isIntentionalClose) {
      this.scheduleReconnect();
    }
  }

  private onError(event: Event): void {
    console.error("[WS] Error:", event);
  }

  private emit(type: string, data: unknown): void {
    const handlers = this.handlers.get(type);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(data);
        } catch (err) {
          console.error(`[WS] Handler error for '${type}':`, err);
        }
      });
    }
  }

  private scheduleReconnect(): void {
    if (this.retryCount >= this.options.maxRetries) {
      console.error("[WS] Max retries reached, giving up.");
      return;
    }

    const delay = Math.min(
      this.options.baseDelay * Math.pow(2, this.retryCount),
      this.options.maxDelay
    );

    console.log(
      `[WS] Reconnecting in ${delay}ms (attempt ${this.retryCount + 1})`
    );

    this.retryCount++;
    setTimeout(() => this.connect(), delay);
  }

  private startPing(): void {
    this.pingTimer = setInterval(() => {
      this.send({ type: "ping" });
    }, this.options.pingInterval);
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }
}

// Singleton instance
let _instance: MarketWebSocket | null = null;

export function getMarketWebSocket(): MarketWebSocket {
  if (!_instance) {
    _instance = new MarketWebSocket();
  }
  return _instance;
}
