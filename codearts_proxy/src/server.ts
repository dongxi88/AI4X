/**
 * Server: HTTP Server exposing OpenAI and Anthropic compatible APIs.
 */

import http from "node:http";
import crypto from "node:crypto";
import { PROXY_PORT, PROXY_HOST, DEFAULT_MODEL, resolveModel } from "./config.ts";
import { KernelProbe } from "./kernel-probe.ts";
import { SessionStore, conversationKey } from "./session-store.ts";
import { CodeArtsClient } from "./codearts-client.ts";
import { kernelEvents } from "./kernel-events.ts";
import {
  anthropicToOpenaiChat,
  openaiChatToAnthropic,
  openaiChatStreamToAnthropic,
  type AnthropicRequest,
} from "./anthropic-transform.ts";
import { renderDashboardHtml } from "./dashboard.ts";
import { interactionLogger } from "./logger.ts";

export class CodeArtsProxyServer {
  private server: http.Server | null = null;
  private readonly port: number;
  private readonly host: string;

  constructor(port = PROXY_PORT, host = PROXY_HOST) {
    this.port = port;
    this.host = host;
  }

  async start(): Promise<void> {
    this.server = http.createServer((req, res) => this.handleRequest(req, res));

    await new Promise<void>((resolve, reject) => {
      this.server!.on("error", reject);
      this.server!.listen(this.port, this.host, () => resolve());
    });

    kernelEvents.start().catch((err) => {
      console.warn("[CodeArts Proxy] Failed to connect kernel events stream:", err.message);
    });

    console.log(`[CodeArts Proxy] Server listening on http://${this.host}:${this.port}`);
  }

  async stop(): Promise<void> {
    kernelEvents.stop();
    if (!this.server) return;
    await new Promise<void>((resolve) => this.server!.close(() => resolve()));
    this.server = null;
  }

  private async handleRequest(req: http.IncomingMessage, res: http.ServerResponse): Promise<void> {
    // Enable CORS for web apps and browser plugins
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE");
    res.setHeader("Access-Control-Allow-Headers", "*");

    if (req.method === "OPTIONS") {
      res.writeHead(204);
      return void res.end();
    }

    const host = req.headers.host || `${this.host}:${this.port}`;
    const url = new URL(req.url || "/", `http://${host}`);
    const pathname = url.pathname;

    try {
      // 0. Live Dashboard UI
      if (pathname === "/" || pathname === "/dashboard") {
        res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        return void res.end(renderDashboardHtml());
      }

      // API: Get recorded interactions
      if (pathname === "/api/interactions" && req.method === "GET") {
        res.writeHead(200, { "Content-Type": "application/json" });
        return void res.end(JSON.stringify({ records: interactionLogger.getRecords() }));
      }

      // API: Clear recorded interactions
      if (pathname === "/api/interactions/clear" && req.method === "POST") {
        interactionLogger.clear();
        res.writeHead(200, { "Content-Type": "application/json" });
        return void res.end(JSON.stringify({ status: "ok" }));
      }

      // API: Live SSE log stream
      if (pathname === "/api/stream" && req.method === "GET") {
        res.writeHead(200, {
          "Content-Type": "text/event-stream; charset=utf-8",
          "Cache-Control": "no-cache",
          "Connection": "keep-alive",
        });
        const unsubscribe = interactionLogger.addListener((record) => {
          if (!res.writableEnded) {
            res.write(`data: ${JSON.stringify(record)}\n\n`);
          }
        });
        req.on("close", () => unsubscribe());
        return;
      }

      // 1. Health & status
      if (pathname === "/health" || pathname === "/v0/status") {
        return this.handleStatus(res);
      }

      // 2. OpenAI Model List: GET /v1/models
      if (pathname === "/v1/models" && req.method === "GET") {
        return this.handleListModels(res);
      }

      // 3. OpenAI Chat Completions: POST /v1/chat/completions
      if (pathname === "/v1/chat/completions" && req.method === "POST") {
        return this.handleChatCompletions(req, res);
      }

      // 4. Anthropic Messages: POST /v1/messages
      if (pathname === "/v1/messages" && req.method === "POST") {
        return this.handleAnthropicMessages(req, res);
      }

      // 404
      res.writeHead(404, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: `Route not found: ${pathname}` }));
    } catch (err: any) {
      console.error("[Proxy Error]:", err);
      if (!res.headersSent) {
        res.writeHead(500, { "Content-Type": "application/json" });
      }
      res.end(JSON.stringify({ error: { message: err.message || String(err) } }));
    }
  }

  private async handleStatus(res: http.ServerResponse): Promise<void> {
    try {
      const port = await KernelProbe.getPort();
      const models = await KernelProbe.listModels();
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          status: "ok",
          kernel: {
            port,
            connected: true,
            models: models.map((m) => m.id),
          },
        })
      );
    } catch (err: any) {
      res.writeHead(503, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          status: "degraded",
          error: err.message,
        })
      );
    }
  }

  private async handleListModels(res: http.ServerResponse): Promise<void> {
    try {
      const models = await KernelProbe.listModels();
      const openAiModels = models.map((m) => ({
        id: m.id,
        object: "model",
        created: 1700000000,
        owned_by: "codearts",
        permission: [],
        root: m.id,
      }));

      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          object: "list",
          data: openAiModels,
        })
      );
    } catch (err: any) {
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: { message: err.message } }));
    }
  }

  private async handleChatCompletions(
    req: http.IncomingMessage,
    res: http.ServerResponse
  ): Promise<void> {
    const startTime = Date.now();
    let requestedModel = DEFAULT_MODEL;
    let model = DEFAULT_MODEL;
    let stream = false;
    let prompt = "";
    let convKey = "";

    try {
      const rawBody = await this.readRequestBody(req);
      const body = JSON.parse(rawBody || "{}");

      const messages = body.messages || [];
      requestedModel = body.model || DEFAULT_MODEL;
      model = resolveModel(requestedModel, KernelProbe.models.map((m) => m.id));
      stream = body.stream === true;
      const variant = body.reasoning_effort || body.variant || "low";

      convKey = conversationKey(messages);
      const { sessionId, isNew } = await SessionStore.getOrCreateSession(convKey);

      // Build user prompt from messages (only latest message for existing sessions)
      prompt = this.formatMessagesToPrompt(messages, isNew);

      // Cancel on client disconnect
      const abortController = new AbortController();
      req.on("close", () => {
        if (!res.writableEnded) {
          abortController.abort();
          SessionStore.abortSession(sessionId);
        }
      });

      const completionId = `chatcmpl-${crypto.randomUUID()}`;
      const createdTime = Math.floor(Date.now() / 1000);

      if (!stream) {
        // Non-streaming response
        const result = await CodeArtsClient.sendMessage(sessionId, prompt, model, {
          variant,
          signal: abortController.signal,
        });

        const responsePayload = {
          id: completionId,
          object: "chat.completion",
          created: createdTime,
          model: requestedModel,
          choices: [
            {
              index: 0,
              message: {
                role: "assistant",
                content: result.text,
                ...(result.reasoning ? { reasoning_content: result.reasoning } : {}),
              },
              finish_reason: result.finish || "stop",
            },
          ],
          usage: {
            prompt_tokens: result.tokens.input || 0,
            completion_tokens: result.tokens.output || 0,
            total_tokens: (result.tokens.input || 0) + (result.tokens.output || 0),
          },
        };

        interactionLogger.logInteraction({
          id: completionId,
          time: new Date().toLocaleTimeString(),
          timestamp: startTime,
          protocol: "OpenAI",
          method: "POST",
          path: "/v1/chat/completions",
          clientModel: requestedModel,
          resolvedModel: model,
          stream: false,
          prompt,
          response: result.text,
          reasoning: result.reasoning,
          durationMs: Date.now() - startTime,
          tokens: {
            input: result.tokens.input || 0,
            output: result.tokens.output || 0,
            total: (result.tokens.input || 0) + (result.tokens.output || 0),
          },
          status: 200,
        });

        res.writeHead(200, { "Content-Type": "application/json" });
        return void res.end(JSON.stringify(responsePayload));
      }

      // True Real-Time Streaming: Send SSE headers immediately
      res.writeHead(200, {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      });

      let fullText = "";
      let fullReasoning = "";

      const result = await CodeArtsClient.sendMessage(sessionId, prompt, model, {
        variant,
        signal: abortController.signal,
        onDelta: (delta) => {
          if (res.writableEnded) return;
          if (delta.field === "reasoning") {
            fullReasoning += delta.text;
            const chunk = {
              id: completionId,
              object: "chat.completion.chunk",
              created: createdTime,
              model: requestedModel,
              choices: [
                {
                  index: 0,
                  delta: {
                    role: "assistant",
                    reasoning_content: delta.text,
                  },
                  finish_reason: null,
                },
              ],
            };
            res.write(`data: ${JSON.stringify(chunk)}\n\n`);
          } else if (delta.field === "text") {
            fullText += delta.text;
            const chunk = {
              id: completionId,
              object: "chat.completion.chunk",
              created: createdTime,
              model: requestedModel,
              choices: [
                {
                  index: 0,
                  delta: {
                    content: delta.text,
                  },
                  finish_reason: null,
                },
              ],
            };
            res.write(`data: ${JSON.stringify(chunk)}\n\n`);
          }
        },
      });

      // Fallback if no SSE delta chunks were caught
      if (!fullText && result.text) {
        if (result.reasoning) {
          const rChunk = {
            id: completionId,
            object: "chat.completion.chunk",
            created: createdTime,
            model: requestedModel,
            choices: [
              {
                index: 0,
                delta: {
                  role: "assistant",
                  reasoning_content: result.reasoning,
                },
                finish_reason: null,
              },
            ],
          };
          res.write(`data: ${JSON.stringify(rChunk)}\n\n`);
        }
        const tChunk = {
          id: completionId,
          object: "chat.completion.chunk",
          created: createdTime,
          model: requestedModel,
          choices: [
            {
              index: 0,
              delta: {
                content: result.text,
              },
              finish_reason: null,
            },
          ],
        };
        res.write(`data: ${JSON.stringify(tChunk)}\n\n`);
      }

      // Final stop chunk
      const finalChunk = {
        id: completionId,
        object: "chat.completion.chunk",
        created: createdTime,
        model: requestedModel,
        choices: [
          {
            index: 0,
            delta: {},
            finish_reason: result.finish || "stop",
          },
        ],
      };
      res.write(`data: ${JSON.stringify(finalChunk)}\n\n`);
      res.write("data: [DONE]\n\n");
      res.end();

      const loggedText = fullText || result.text || "";
      const loggedReasoning = fullReasoning || result.reasoning || "";

      interactionLogger.logInteraction({
        id: completionId,
        time: new Date().toLocaleTimeString(),
        timestamp: startTime,
        protocol: "OpenAI",
        method: "POST",
        path: "/v1/chat/completions",
        clientModel: requestedModel,
        resolvedModel: model,
        stream: true,
        prompt,
        response: loggedText,
        reasoning: loggedReasoning,
        durationMs: Date.now() - startTime,
        tokens: {
          input: result.tokens.input || 0,
          output: result.tokens.output || 0,
          total: (result.tokens.input || 0) + (result.tokens.output || 0),
        },
        status: 200,
      });
    } catch (err: any) {
      if (convKey) {
        SessionStore.deleteSession(convKey);
      }

      interactionLogger.logInteraction({
        id: `chatcmpl-${crypto.randomUUID()}`,
        time: new Date().toLocaleTimeString(),
        timestamp: startTime,
        protocol: "OpenAI",
        method: "POST",
        path: "/v1/chat/completions",
        clientModel: requestedModel,
        resolvedModel: model,
        stream,
        prompt,
        response: "",
        error: err.message,
        durationMs: Date.now() - startTime,
        tokens: { input: 0, output: 0, total: 0 },
        status: 500,
      });

      if (!res.headersSent) {
        res.writeHead(500, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            error: {
              message: err.message || "Internal server error",
              type: "upstream_error",
              code: 500,
            },
          })
        );
      } else if (!res.writableEnded) {
        res.write(
          `data: ${JSON.stringify({
            error: {
              message: err.message || "Internal server error",
              type: "upstream_error",
              code: 500,
            },
          })}\n\n`
        );
        res.end();
      }
    }
  }

  private async handleAnthropicMessages(
    req: http.IncomingMessage,
    res: http.ServerResponse
  ): Promise<void> {
    const startTime = Date.now();
    let requestedModel = DEFAULT_MODEL;
    let targetModel = DEFAULT_MODEL;
    let isStream = false;
    let prompt = "";
    let convKey = "";

    try {
      const rawBody = await this.readRequestBody(req);
      const anthropicReq = JSON.parse(rawBody || "{}") as AnthropicRequest;

      // Convert Anthropic request to OpenAI format
      const openAiReq = anthropicToOpenaiChat(anthropicReq);
      requestedModel = anthropicReq.model || DEFAULT_MODEL;
      targetModel = resolveModel(openAiReq.model || requestedModel, KernelProbe.models.map((m) => m.id));

      convKey = conversationKey(openAiReq.messages);
      const { sessionId, isNew } = await SessionStore.getOrCreateSession(convKey);

      prompt = this.formatMessagesToPrompt(openAiReq.messages, isNew);

      const abortController = new AbortController();
      req.on("close", () => {
        if (!res.writableEnded) {
          abortController.abort();
          SessionStore.abortSession(sessionId);
        }
      });

      isStream = anthropicReq.stream === true;

      if (!isStream) {
        const result = await CodeArtsClient.sendMessage(sessionId, prompt, targetModel, {
          variant: openAiReq.reasoning_effort || "low",
          signal: abortController.signal,
        });

        const openAiResp = {
          id: `chatcmpl-${crypto.randomUUID()}`,
          model: requestedModel,
          choices: [
            {
              message: {
                role: "assistant",
                content: result.text,
                ...(result.reasoning ? { reasoning_content: result.reasoning } : {}),
              },
              finish_reason: result.finish || "stop",
            },
          ],
          usage: {
            prompt_tokens: result.tokens.input || 0,
            completion_tokens: result.tokens.output || 0,
            total_tokens: (result.tokens.input || 0) + (result.tokens.output || 0),
          },
        };

        const anthropicResp = openaiChatToAnthropic(openAiResp, requestedModel);

        interactionLogger.logInteraction({
          id: anthropicResp.id,
          time: new Date().toLocaleTimeString(),
          timestamp: startTime,
          protocol: "Anthropic",
          method: "POST",
          path: "/v1/messages",
          clientModel: requestedModel,
          resolvedModel: targetModel,
          stream: false,
          prompt,
          response: result.text,
          reasoning: result.reasoning,
          durationMs: Date.now() - startTime,
          tokens: {
            input: result.tokens.input || 0,
            output: result.tokens.output || 0,
            total: (result.tokens.input || 0) + (result.tokens.output || 0),
          },
          status: 200,
        });

        res.writeHead(200, { "Content-Type": "application/json" });
        return void res.end(JSON.stringify(anthropicResp));
      }

      // True Real-Time Anthropic SSE Stream
      res.writeHead(200, {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      });

      const msgId = `msg_${crypto.randomUUID().replace(/-/g, "")}`;
      res.write(`event: message_start\ndata: ${JSON.stringify({
        type: "message_start",
        message: {
          id: msgId,
          type: "message",
          role: "assistant",
          content: [],
          model: requestedModel,
          stop_reason: null,
          stop_sequence: null,
          usage: { input_tokens: 0, output_tokens: 0 },
        },
      })}\n\n`);

      let hasStartedThinking = false;
      let hasStartedText = false;
      let contentIndex = 0;
      let fullText = "";
      let fullReasoning = "";

      const result = await CodeArtsClient.sendMessage(sessionId, prompt, targetModel, {
        variant: openAiReq.reasoning_effort || "low",
        signal: abortController.signal,
        onDelta: (delta) => {
          if (res.writableEnded) return;
          if (delta.field === "reasoning") {
            fullReasoning += delta.text;
            if (!hasStartedThinking) {
              hasStartedThinking = true;
              res.write(`event: content_block_start\ndata: ${JSON.stringify({
                type: "content_block_start",
                index: contentIndex,
                content_block: { type: "thinking", thinking: "" },
              })}\n\n`);
            }
            res.write(`event: content_block_delta\ndata: ${JSON.stringify({
              type: "content_block_delta",
              index: contentIndex,
              delta: { type: "thinking_delta", thinking: delta.text },
            })}\n\n`);
          } else if (delta.field === "text") {
            fullText += delta.text;
            if (hasStartedThinking) {
              // Close thinking block
              res.write(`event: content_block_stop\ndata: ${JSON.stringify({
                type: "content_block_stop",
                index: contentIndex,
              })}\n\n`);
              hasStartedThinking = false;
              contentIndex++;
            }
            if (!hasStartedText) {
              hasStartedText = true;
              res.write(`event: content_block_start\ndata: ${JSON.stringify({
                type: "content_block_start",
                index: contentIndex,
                content_block: { type: "text", text: "" },
              })}\n\n`);
            }
            res.write(`event: content_block_delta\ndata: ${JSON.stringify({
              type: "content_block_delta",
              index: contentIndex,
              delta: { type: "text_delta", text: delta.text },
            })}\n\n`);
          }
        },
      });

      if (hasStartedThinking) {
        res.write(`event: content_block_stop\ndata: ${JSON.stringify({
          type: "content_block_stop",
          index: contentIndex,
        })}\n\n`);
        contentIndex++;
      }
      if (hasStartedText) {
        res.write(`event: content_block_stop\ndata: ${JSON.stringify({
          type: "content_block_stop",
          index: contentIndex,
        })}\n\n`);
      } else if (!fullText && result.text) {
        // Fallback if no deltas arrived
        res.write(`event: content_block_start\ndata: ${JSON.stringify({
          type: "content_block_start",
          index: contentIndex,
          content_block: { type: "text", text: "" },
        })}\n\n`);
        res.write(`event: content_block_delta\ndata: ${JSON.stringify({
          type: "content_block_delta",
          index: contentIndex,
          delta: { type: "text_delta", text: result.text },
        })}\n\n`);
        res.write(`event: content_block_stop\ndata: ${JSON.stringify({
          type: "content_block_stop",
          index: contentIndex,
        })}\n\n`);
      }

      res.write(`event: message_delta\ndata: ${JSON.stringify({
        type: "message_delta",
        delta: { stop_reason: "end_turn", stop_sequence: null },
        usage: { output_tokens: result.tokens.output || 0 },
      })}\n\n`);

      res.write(`event: message_stop\ndata: {"type":"message_stop"}\n\n`);
      res.end();

      const loggedText = fullText || result.text || "";
      const loggedReasoning = fullReasoning || result.reasoning || "";

      interactionLogger.logInteraction({
        id: msgId,
        time: new Date().toLocaleTimeString(),
        timestamp: startTime,
        protocol: "Anthropic",
        method: "POST",
        path: "/v1/messages",
        clientModel: requestedModel,
        resolvedModel: targetModel,
        stream: true,
        prompt,
        response: loggedText,
        reasoning: loggedReasoning,
        durationMs: Date.now() - startTime,
        tokens: {
          input: result.tokens.input || 0,
          output: result.tokens.output || 0,
          total: (result.tokens.input || 0) + (result.tokens.output || 0),
        },
        status: 200,
      });
    } catch (err: any) {
      if (convKey) {
        SessionStore.deleteSession(convKey);
      }
      interactionLogger.logInteraction({
        id: `msg_${crypto.randomUUID().replace(/-/g, "")}`,
        time: new Date().toLocaleTimeString(),
        timestamp: startTime,
        protocol: "Anthropic",
        method: "POST",
        path: "/v1/messages",
        clientModel: requestedModel,
        resolvedModel: targetModel,
        stream: isStream,
        prompt,
        response: "",
        error: err.message,
        durationMs: Date.now() - startTime,
        tokens: { input: 0, output: 0, total: 0 },
        status: 500,
      });

      if (!res.headersSent) {
        res.writeHead(500, { "Content-Type": "application/json" });
        res.end(JSON.stringify({
          type: "error",
          error: {
            type: "api_error",
            message: err.message || "Internal server error",
          },
        }));
      } else if (!res.writableEnded) {
        res.write(`event: error\ndata: ${JSON.stringify({
          type: "error",
          error: { type: "api_error", message: err.message },
        })}\n\n`);
        res.end();
      }
    }
  }

  private formatMessagesToPrompt(messages: any[], isNewSession = true): string {
    if (!messages || messages.length === 0) return "";

    const systemDirectives =
      "【响应规范】：如果需要绘制插画、图表、流程图或海报，请务必直接在回答中使用 ```svg 代码块输出完整的标准 SVG 矢量图形代码（或 ```mermaid），前端界面将直接渲染该图像呈现；严禁调用本地文件写入或系统工具。";

    // If existing session, the kernel already preserves conversation history!
    // We only need to send the latest message to avoid duplicate history bloating.
    if (!isNewSession && messages.length > 1) {
      const lastMsg = messages[messages.length - 1];
      const content =
        typeof lastMsg.content === "string"
          ? lastMsg.content
          : JSON.stringify(lastMsg.content);
      return content;
    }

    // If only one message, return text directly
    if (messages.length === 1) {
      const content = typeof messages[0].content === "string"
        ? messages[0].content
        : JSON.stringify(messages[0].content);
      return `${systemDirectives}\n\n${content}`;
    }

    // If new session, format multi-turn cleanly:
    const lines: string[] = [`[System Directive]:\n${systemDirectives}\n`];
    for (const msg of messages) {
      const role = msg.role || "user";
      const content =
        typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content);
      if (role === "system") {
        lines.push(`[System Instruction]:\n${content}\n`);
      } else if (role === "assistant") {
        lines.push(`[Assistant]:\n${content}\n`);
      } else {
        lines.push(`[User]:\n${content}\n`);
      }
    }
    return lines.join("\n").trim();
  }

  private readRequestBody(req: http.IncomingMessage): Promise<string> {
    return new Promise((resolve, reject) => {
      const chunks: Buffer[] = [];
      req.on("data", (c) => chunks.push(c));
      req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
      req.on("error", reject);
    });
  }
}
