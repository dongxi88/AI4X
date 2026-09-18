/**
 * Interaction Logger & Live Event Broadcaster
 */

export interface InteractionRecord {
  id: string;
  time: string;
  timestamp: number;
  protocol: "OpenAI" | "Anthropic";
  method: string;
  path: string;
  clientModel: string;
  resolvedModel: string;
  stream: boolean;
  prompt: string;
  response: string;
  reasoning?: string;
  durationMs: number;
  tokens: { input?: number; output?: number; total?: number };
  status: number;
  error?: string;
}

class InteractionLogger {
  private records: InteractionRecord[] = [];
  private maxRecords = 300;
  private listeners: ((record: InteractionRecord) => void)[] = [];

  logInteraction(record: InteractionRecord): void {
    this.records.unshift(record);
    if (this.records.length > this.maxRecords) {
      this.records.pop();
    }

    // Format human-friendly console output
    const statusTag = record.status >= 200 && record.status < 300 ? "200 OK" : `${record.status} ERR`;
    const streamTag = record.stream ? "STREAM" : "BLOCK";
    const durationSec = (record.durationMs / 1000).toFixed(2);

    console.log(`\n[${record.time}] [${record.protocol}] ${record.method} ${record.path} [${streamTag}] -> ${statusTag} (${durationSec}s)`);
    console.log(`  模型: ${record.clientModel} -> ${record.resolvedModel} | Token: 输入=${record.tokens.input ?? 0}, 输出=${record.tokens.output ?? 0}`);

    const promptPreview = record.prompt.replace(/\s+/g, " ").trim();
    console.log(`  提示词: ${promptPreview.slice(0, 100)}${promptPreview.length > 100 ? "..." : ""}`);

    if (record.reasoning) {
      const reasonPreview = record.reasoning.replace(/\s+/g, " ").trim();
      console.log(`  思考链: ${reasonPreview.slice(0, 100)}${reasonPreview.length > 100 ? "..." : ""}`);
    }

    const respPreview = (record.response || record.error || "").replace(/\s+/g, " ").trim();
    console.log(`  模型回复: ${respPreview.slice(0, 120)}${respPreview.length > 120 ? "..." : ""}`);
    console.log("-".repeat(70));

    // Notify listeners
    for (const listener of this.listeners) {
      try {
        listener(record);
      } catch {}
    }
  }

  getRecords(): InteractionRecord[] {
    return this.records;
  }

  clear(): void {
    this.records = [];
  }

  addListener(listener: (record: InteractionRecord) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }
}

export const interactionLogger = new InteractionLogger();
