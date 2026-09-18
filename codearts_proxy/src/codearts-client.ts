/**
 * CodeArts Client: Communicates directly with agent-kernel HTTP endpoints.
 */

import crypto from "node:crypto";
import { KernelProbe } from "./kernel-probe.ts";
import { CODEARTS_HEADERS, DEFAULT_PROVIDER, UPSTREAM_IDLE_TIMEOUT_MS } from "./config.ts";
import { idleBudget } from "./idle-budget.ts";
import { kernelEvents, type KernelDelta } from "./kernel-events.ts";

export interface ChatMessageResult {
  text: string;
  reasoning?: string;
  tokens: {
    input?: number;
    output?: number;
    reasoning?: number;
  };
  finish: string;
}

export class CodeArtsClient {
  /**
   * Send a prompt message to an active session on the CodeArts kernel.
   * Subscribes to real-time kernel token events to keep watchdog alive
   * and optionally forward streaming deltas to callers.
   */
  static async sendMessage(
    sessionId: string,
    prompt: string,
    modelId: string,
    options: {
      providerId?: string;
      variant?: string;
      timeoutMs?: number;
      signal?: AbortSignal;
      onDelta?: (delta: KernelDelta) => void;
    } = {}
  ): Promise<ChatMessageResult> {
    const port = await KernelProbe.getPort();
    const providerId = options.providerId || DEFAULT_PROVIDER;
    const variant = options.variant || "low";
    const timeoutMs = options.timeoutMs || UPSTREAM_IDLE_TIMEOUT_MS;

    const url = `http://127.0.0.1:${port}/session/${sessionId}/message`;
    const headers: Record<string, string> = {
      ...CODEARTS_HEADERS,
      "x-snap-traceid": crypto.randomUUID(),
    };

    const payload = {
      model: {
        providerID: providerId,
        modelID: modelId,
      },
      variant,
      parts: [
        {
          type: "text",
          text: prompt,
        },
      ],
    };

    // Combine external signal with timeout budget
    const budget = idleBudget(timeoutMs);
    const combinedSignal = options.signal
      ? AbortSignal.any([options.signal, budget.signal])
      : budget.signal;

    // Hook into live kernel event stream to touch watchdog on every token
    const unsubscribe = kernelEvents.subscribe(sessionId, (delta) => {
      budget.touch();
      if (options.onDelta) {
        options.onDelta(delta);
      }
    });

    try {
      const resp = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
        signal: combinedSignal,
      });

      if (!resp.ok) {
        const errText = await resp.text().catch(() => "");
        throw new Error(`CodeArts kernel returned HTTP ${resp.status}: ${errText}`);
      }

      const data = (await resp.json()) as any;
      const parts = data.parts || [];
      const texts: string[] = [];
      const reasonings: string[] = [];

      for (const part of parts) {
        if (part.type === "text" && part.text) {
          texts.push(part.text);
        } else if (part.type === "reasoning" && part.text) {
          reasonings.push(part.text);
        }
      }

      const info = data.info || {};
      return {
        text: texts.join("\n"),
        reasoning: reasonings.join("\n"),
        tokens: {
          input: info.tokens?.input || 0,
          output: info.tokens?.output || 0,
          reasoning: info.tokens?.reasoning || 0,
        },
        finish: info.finish || "stop",
      };
    } finally {
      unsubscribe();
      budget.done();
    }
  }
}
