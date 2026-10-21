/**
 * Session Store: Maps stateless client conversations to stateful CodeArts Sessions
 * using the conversationKey algorithm inspired by opencode-deveco.
 */

import crypto from "node:crypto";
import { KernelProbe } from "./kernel-probe.ts";
import { SESSION_TTL_MS } from "./config.ts";

interface SessionEntry {
  sessionId: string;
  convKey: string;
  createdAt: number;
  lastActiveAt: number;
}

/**
 * Generate a deterministic hash key for a conversation based on its initial turn.
 * As a conversation grows, its system prompt and first message remain unchanged,
 * allowing stateless clients (Cursor, Cline) to automatically lock into the same session.
 */
export function conversationKey(messages: any[]): string {
  try {
    const head = JSON.stringify([messages[0] ?? "", messages[1] ?? ""]);
    return crypto.createHash("sha256").update(head).digest("hex").slice(0, 24);
  } catch {
    return crypto.randomUUID().replace(/-/g, "").slice(0, 24);
  }
}

export class SessionStore {
  private static sessions = new Map<string, SessionEntry>();
  private static reapTimer: NodeJS.Timeout | null = null;

  static {
    // Start background reaper for inactive sessions
    this.reapTimer = setInterval(() => this.reapExpiredSessions(), 60 * 1000);
    this.reapTimer.unref();
  }

  /**
   * Retrieve existing CodeArts session ID for the given conversation key,
   * or create a new session on the kernel.
   */
  static async getOrCreateSession(convKey: string): Promise<{ sessionId: string; isNew: boolean }> {
    const existing = this.sessions.get(convKey);
    if (existing) {
      existing.lastActiveAt = Date.now();
      return { sessionId: existing.sessionId, isNew: false };
    }

    const port = await KernelProbe.getPort();
    const resp = await fetch(`http://127.0.0.1:${port}/session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: `cpa_${convKey.slice(0, 8)}`,
      }),
      signal: AbortSignal.timeout(10000),
    });

    if (!resp.ok) {
      throw new Error(`Failed to create CodeArts session: HTTP ${resp.status}`);
    }

    const data = (await resp.json()) as { id: string };
    const sessionId = data.id;

    // Store in LRU / Cache
    if (this.sessions.size >= 500) {
      const oldestKey = this.sessions.keys().next().value;
      if (oldestKey) this.deleteSession(oldestKey);
    }

    this.sessions.set(convKey, {
      sessionId,
      convKey,
      createdAt: Date.now(),
      lastActiveAt: Date.now(),
    });

    return { sessionId, isNew: true };
  }

  /**
   * Abort an ongoing generation on a session (e.g. client disconnect).
   */
  static async abortSession(sessionId: string): Promise<void> {
    try {
      const port = await KernelProbe.getPort();
      await fetch(`http://127.0.0.1:${port}/session/${sessionId}/abort`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
        signal: AbortSignal.timeout(3000),
      });
    } catch {
      // Best-effort
    }
  }

  /**
   * Delete a session from kernel and local store.
   */
  static async deleteSession(convKey: string): Promise<void> {
    const entry = this.sessions.get(convKey);
    if (!entry) return;

    this.sessions.delete(convKey);
    try {
      const port = await KernelProbe.getPort();
      await fetch(`http://127.0.0.1:${port}/session/${entry.sessionId}`, {
        method: "DELETE",
        signal: AbortSignal.timeout(3000),
      });
    } catch {
      // Best-effort
    }
  }

  /**
   * Clean up sessions inactive for longer than SESSION_TTL_MS.
   */
  private static async reapExpiredSessions(): Promise<void> {
    const now = Date.now();
    for (const [key, entry] of this.sessions.entries()) {
      if (now - entry.lastActiveAt > SESSION_TTL_MS) {
        await this.deleteSession(key);
      }
    }
  }
}
