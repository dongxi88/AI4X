/**
 * Kernel Events: Manages real-time SSE connection to CodeArts agent-kernel /event endpoint.
 * Dispatches per-session token deltas (reasoning and text) to active callers.
 */

import http from "node:http";
import { KernelProbe } from "./kernel-probe.ts";

export interface KernelDelta {
  field: "reasoning" | "text";
  text: string;
}

export type DeltaListener = (delta: KernelDelta) => void;
export type RawEventListener = (event: any) => void;

interface SessionSubscribers {
  deltaListeners: Set<DeltaListener>;
  rawListeners: Set<RawEventListener>;
}

export class KernelEventsManager {
  private static instance: KernelEventsManager | null = null;

  private subscribers = new Map<string, SessionSubscribers>();
  private activeReq: http.ClientRequest | null = null;
  private isConnecting = false;
  private isRunning = false;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private buffer = "";

  static getInstance(): KernelEventsManager {
    if (!this.instance) {
      this.instance = new KernelEventsManager();
    }
    return this.instance;
  }

  /**
   * Start listening to the kernel /event SSE stream.
   */
  async start(): Promise<void> {
    this.isRunning = true;
    await this.connect();
  }

  /**
   * Stop the event listener.
   */
  stop(): void {
    this.isRunning = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.activeReq) {
      this.activeReq.destroy();
      this.activeReq = null;
    }
    this.subscribers.clear();
  }

  /**
   * Subscribe to token deltas and raw events for a specific session ID.
   * Returns an unsubscribe function.
   */
  subscribe(
    sessionId: string,
    onDelta?: DeltaListener,
    onRawEvent?: RawEventListener
  ): () => void {
    let subs = this.subscribers.get(sessionId);
    if (!subs) {
      subs = {
        deltaListeners: new Set(),
        rawListeners: new Set(),
      };
      this.subscribers.set(sessionId, subs);
    }

    if (onDelta) subs.deltaListeners.add(onDelta);
    if (onRawEvent) subs.rawListeners.add(onRawEvent);

    // Ensure connection is active
    if (!this.activeReq && this.isRunning) {
      this.connect().catch(() => {});
    }

    return () => {
      if (onDelta) subs?.deltaListeners.delete(onDelta);
      if (onRawEvent) subs?.rawListeners.delete(onRawEvent);
      if (subs && subs.deltaListeners.size === 0 && subs.rawListeners.size === 0) {
        this.subscribers.delete(sessionId);
      }
    };
  }

  private async connect(): Promise<void> {
    if (this.isConnecting || !this.isRunning) return;
    this.isConnecting = true;

    try {
      const port = await KernelProbe.getPort();
      if (!port) {
        this.scheduleReconnect(2000);
        return;
      }

      const req = http.get(
        `http://127.0.0.1:${port}/event`,
        {
          headers: {
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
          },
        },
        (res) => {
          if (res.statusCode !== 200) {
            req.destroy();
            this.scheduleReconnect(2000);
            return;
          }

          this.activeReq = req;
          this.isConnecting = false;
          this.buffer = "";

          res.setEncoding("utf8");
          res.on("data", (chunk: string) => this.handleChunk(chunk));
          res.on("end", () => {
            this.activeReq = null;
            this.scheduleReconnect(1000);
          });
          res.on("error", () => {
            this.activeReq = null;
            this.scheduleReconnect(2000);
          });
        }
      );

      req.on("error", () => {
        this.activeReq = null;
        this.isConnecting = false;
        this.scheduleReconnect(2000);
      });
    } catch {
      this.isConnecting = false;
      this.scheduleReconnect(2000);
    }
  }

  private handleChunk(chunk: string): void {
    this.buffer += chunk;
    const lines = this.buffer.split("\n");
    // Keep trailing partial line in buffer
    this.buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;

      const jsonStr = trimmed.slice(5).trim();
      if (!jsonStr) continue;

      try {
        const event = JSON.parse(jsonStr);
        this.dispatchEvent(event);
      } catch {
        // Ignore unparseable SSE frame
      }
    }
  }

  private dispatchEvent(event: any): void {
    const sessionId = event?.properties?.sessionID;
    if (!sessionId) return;

    const subs = this.subscribers.get(sessionId);
    if (!subs) return;

    // Dispatch raw event
    for (const rawListener of subs.rawListeners) {
      try {
        rawListener(event);
      } catch (err) {
        console.error("[KernelEvents] rawListener error:", err);
      }
    }

    // Dispatch token delta
    if (event.type === "message.part.delta") {
      const field = event.properties?.field;
      const delta = event.properties?.delta;
      if ((field === "reasoning" || field === "text") && typeof delta === "string") {
        const deltaObj: KernelDelta = { field, text: delta };
        for (const deltaListener of subs.deltaListeners) {
          try {
            deltaListener(deltaObj);
          } catch (err) {
            console.error("[KernelEvents] deltaListener error:", err);
          }
        }
      }
    }
  }

  private scheduleReconnect(delayMs: number): void {
    if (!this.isRunning || this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect().catch(() => {});
    }, delayMs);
  }
}

export const kernelEvents = KernelEventsManager.getInstance();
