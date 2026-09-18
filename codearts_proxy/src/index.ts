/**
 * CodeArts Proxy Entry Point
 */

import { CodeArtsProxyServer } from "./server.ts";
import { PROXY_PORT, PROXY_HOST } from "./config.ts";
import { KernelProbe } from "./kernel-probe.ts";

async function main() {
  console.log("=".repeat(65));
  console.log("  CodeArts Proxy - AI Model Reverse Proxy & Protocol Adapter");
  console.log("=".repeat(65));

  // 1. Probe CodeArts kernel
  try {
    const port = await KernelProbe.getPort();
    console.log(`[+] 成功检测到正在运行的 CodeArts agent-kernel (端口: ${port})`);
    const models = await KernelProbe.listModels();
    console.log(`[+] 已加载可用模型 (${models.length} 个):`);
    for (const m of models) {
      console.log(`    - ${m.id}`);
    }
  } catch (err: any) {
    console.warn(`[!] 警告: ${err.message}`);
    console.warn("    代理将继续启动，待 CodeArts 启动后将自动完成连接。");
  }

  // 2. Start HTTP proxy server
  const server = new CodeArtsProxyServer(PROXY_PORT, PROXY_HOST);
  await server.start();

  console.log("\n" + "-".repeat(65));
  console.log(`[✓] 代理服务就绪！`);
  console.log(`    - OpenAI 接口:    http://${PROXY_HOST}:${PROXY_PORT}/v1`);
  console.log(`    - 检查状态:       http://${PROXY_HOST}:${PROXY_PORT}/health`);
  console.log(`    - 查看模型列表:   http://${PROXY_HOST}:${PROXY_PORT}/v1/models`);
  console.log("-".repeat(65));
  console.log("\n【客户端配置指引】:");
  console.log(`  1. Cursor / Windsurf / Cline / Continue (OpenAI 兼容):`);
  console.log(`     Base URL: http://${PROXY_HOST}:${PROXY_PORT}/v1`);
  console.log(`     API Key:  codearts-proxy-key (任意字符)`);
  console.log(`     Model:    deepseek-v4-pro-0813 或 glm-5.3-flash`);
  console.log(`\n  2. Claude Code (Anthropic 兼容):`);
  console.log(`     ANTHROPIC_BASE_URL=http://${PROXY_HOST}:${PROXY_PORT}`);
  console.log("-".repeat(65));
  console.log("按 Ctrl+C 停止服务\n");

  const shutdown = async () => {
    console.log("\n[*] 正在优雅退出代理服务...");
    await server.stop();
    process.exit(0);
  };

  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);

  process.on("uncaughtException", (err) => {
    console.error("[codearts-proxy] Uncaught exception:", err);
  });
  process.on("unhandledRejection", (reason) => {
    console.error("[codearts-proxy] Unhandled rejection:", reason);
  });
}

main().catch((err) => {
  console.error("Fatal startup error:", err);
  process.exit(1);
});

