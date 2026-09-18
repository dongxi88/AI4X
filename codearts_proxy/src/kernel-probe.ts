/**
 * Kernel Probe: Discovers and monitors the local CodeArts agent-kernel process.
 */

import { execSync } from "node:child_process";

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  reasoning?: boolean;
}

export class KernelProbe {
  private static cachedPort: number | null = null;
  private static lastProbeTime = 0;
  private static cachedModels: ModelInfo[] = [];

  static get models(): ModelInfo[] {
    return this.cachedModels;
  }

  /**
   * Get the current active port of agent-kernel.exe.
   * If cached port is still healthy, returns it immediately.
   */
  static async getPort(): Promise<number> {
    if (this.cachedPort && (await this.isHealthy(this.cachedPort))) {
      return this.cachedPort;
    }

    const port = this.scanProcessPort();
    if (!port) {
      throw new Error(
        "CodeArts agent-kernel.exe is not running. Please launch CodeArts first."
      );
    }

    if (!(await this.isHealthy(port))) {
      throw new Error(
        `agent-kernel.exe found on port ${port} but health check failed.`
      );
    }

    this.cachedPort = port;
    this.lastProbeTime = Date.now();
    return port;
  }

  /**
   * Check if kernel responds on /global/health.
   */
  static async isHealthy(port: number): Promise<boolean> {
    try {
      const resp = await fetch(`http://127.0.0.1:${port}/global/health`, {
        signal: AbortSignal.timeout(3000),
      });
      if (!resp.ok) return false;
      const data = (await resp.json()) as { healthy?: boolean };
      return data.healthy === true;
    } catch {
      return false;
    }
  }

  /**
   * Scan process table for agent-kernel.exe commandline argument --port.
   */
  private static scanProcessPort(): number | null {
    try {
      const cmd =
        'powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \\"Name = \'agent-kernel.exe\'\\").CommandLine"';
      const output = execSync(cmd, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], timeout: 5000 });
      const match = output.match(/--port=(\d+)/);
      if (match) {
        return parseInt(match[1], 10);
      }
    } catch {
      // Fallback or process not found
    }
    return null;
  }

  /**
   * Query available models from the kernel provider endpoint.
   */
  static async listModels(): Promise<ModelInfo[]> {
    const port = await this.getPort();
    const resp = await fetch(`http://127.0.0.1:${port}/provider`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!resp.ok) {
      throw new Error(`Failed to list models from kernel: HTTP ${resp.status}`);
    }

    const data = (await resp.json()) as {
      all?: Array<{
        id: string;
        models?: Record<string, { name?: string; reasoning?: boolean }>;
      }>;
    };

    const models: ModelInfo[] = [];
    for (const provider of data.all || []) {
      const providerId = provider.id;
      for (const [modelId, info] of Object.entries(provider.models || {})) {
        models.push({
          id: modelId,
          name: info.name || modelId,
          provider: providerId,
          reasoning: info.reasoning,
        });
      }
    }
    this.cachedModels = models;
    return models;
  }
}
