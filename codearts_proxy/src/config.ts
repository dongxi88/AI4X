/**
 * Configuration and constants for CodeArts Proxy
 */

export const PROXY_PORT = parseInt(process.env.CODEARTS_PROXY_PORT || "17129", 10);
export const PROXY_HOST = process.env.CODEARTS_PROXY_HOST || "127.0.0.1";

export const DEFAULT_MODEL = "deepseek-v4-pro-0813";
export const DEFAULT_PROVIDER = "inferhub-provider";

export const CODEARTS_HEADERS: Record<string, string> = {
  "Content-Type": "application/json",
  "pluginName": "codearts_space",
  "pluginVersion": "1.0.0",
  "ideName": "codearts_space",
  "ideVersion": "1.0.0",
  "maas_type": "benefit",
};

export const SESSION_TTL_MS = 30 * 60 * 1000; // 30 minutes inactivity expiry
export const UPSTREAM_IDLE_TIMEOUT_MS = 300 * 1000; // 300s (5 minutes) idle timeout
export const KERNEL_HEALTH_CHECK_INTERVAL_MS = 10 * 1000; // 10s health polling

export const MODEL_ALIASES: Record<string, string> = {
  // Direct native model names (fallback when availableModels query pending)
  "glm-5.3-flash": "glm-5.3-flash",
  "glm-5.3": "glm-5.3-flash",
  "glm-5.2": "GLM-5.2",
  "glm-5.1": "GLM-5.1",
  "deepseek-v4-pro-0813": "deepseek-v4-pro-0813",
  "deepseek-v4-flash-0731": "deepseek-v4-flash-0731",
  "deepseek-v4-pro": "deepseek-v4-pro-0813",
  "deepseek-v4-flash": "deepseek-v4-flash-0731",
  "openpangu-2.0-pro": "openpangu-2.0-pro",
  "openpangu-2.0-flash": "openpangu-2.0-flash",

  // Claude mappings
  "claude-3-7-sonnet": "deepseek-v4-pro-0813",
  "claude-3-5-sonnet": "deepseek-v4-pro-0813",
  "claude-3-sonnet": "deepseek-v4-pro-0813",
  "claude-3-opus": "deepseek-v4-pro-0813",
  "claude-3-5-haiku": "glm-5.3-flash",
  "claude-3-haiku": "glm-5.3-flash",
  "claude": "deepseek-v4-pro-0813",
  // OpenAI GPT mappings
  "gpt-4o": "deepseek-v4-pro-0813",
  "gpt-4-turbo": "deepseek-v4-pro-0813",
  "gpt-4": "deepseek-v4-pro-0813",
  "gpt-3.5-turbo": "glm-5.3-flash",
  "gpt-4o-mini": "glm-5.3-flash",
  "o1": "deepseek-v4-pro-0813",
  "o3-mini": "glm-5.3-flash",
  // Deepseek aliases
  "deepseek-chat": "deepseek-v4-pro-0813",
  "deepseek-coder": "deepseek-v4-pro-0813",
  "deepseek-reasoner": "deepseek-v4-pro-0813",
  // GLM / Pangu aliases
  "glm-4": "GLM-5.2",
  "glm-4-flash": "glm-5.3-flash",
  "pangu": "openpangu-2.0-pro",
};

export function resolveModel(requestedModel?: string, availableModels: string[] = []): string {
  if (!requestedModel) return DEFAULT_MODEL;
  
  // Exact match with available models
  if (availableModels.includes(requestedModel)) {
    return requestedModel;
  }

  // Case-insensitive match
  const lower = requestedModel.toLowerCase().trim();
  const exactCaseInsensitive = availableModels.find((m) => m.toLowerCase() === lower);
  if (exactCaseInsensitive) {
    return exactCaseInsensitive;
  }

  // Check aliases
  for (const [alias, target] of Object.entries(MODEL_ALIASES)) {
    if (lower === alias || lower.startsWith(alias) || lower.includes(alias)) {
      return target;
    }
  }

  // If already matches a known pattern or fallback
  return DEFAULT_MODEL;
}

