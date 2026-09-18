# CodeArts Proxy

将本地运行的 **CodeArts** 模型内核直接桥接转换为标准的 **OpenAI** 和 **Anthropic** API 格式。

让 **Cursor**、**Windsurf**、**Cline**、**Claude Code**、**Continue** 等主流 AI 辅助工具直接调用 CodeArts 内置的大模型（如 `deepseek-v4-pro-0813`、`glm-5.3-flash`、`openpangu-2.0-pro` 等）。

---

## 一、核心特性

- **双标准协议兼容**：
  - **OpenAI 规范接口**：`POST /v1/chat/completions`（支持非流式与 SSE 流式输出，透传思考链 `reasoning_content`）
  - **Anthropic 规范接口**：`POST /v1/messages`（支持 Claude Code CLI 直接调用与标准 SSE 事件流）
  - **模型发现接口**：`GET /v1/models`
  - **健康度检查接口**：`GET /health`
- **模型智能别名与路由**：
  - 自动将 `claude-3-7-sonnet`、`claude-3-5-sonnet`、`gpt-4o` 路由至 CodeArts 旗舰推理模型 `deepseek-v4-pro-0813`。
  - 自动将 `claude-3-5-haiku`、`gpt-4o-mini` 路由至极速多模态模型 `glm-5.3-flash`。
- **会话指纹映射 (`conversationKey`)**：
  - 借鉴 `opencode-deveco` 算法，基于首轮对话特征计算 SHA-256 唯一指纹，实现无状态客户端自动锁定有状态会话，多轮对话上下文完美保留。
- **动态端口自愈感知 (`kernel-probe`)**：
  - 自动通过系统 CIM 查询 `agent-kernel.exe` 动态端口，具备心跳探活与重连机制。
- **长推理看门狗 (`idleBudget`)**：
  - 智能流量活跃检测，避免深度思考（Reasoning）模型因固定超时被误杀。
- **零额外依赖**：
  - 基于 Node.js 18+ 原生能力开发，无需额外安装庞大复杂的第三方依赖项。

---

## 二、运行与运维控制

本工具支持 **双击运行** 与 **命令行控制** 两种方式：

### 1. Windows 双击运行脚本（最推荐）

无论在**项目根目录**还是在 **`codearts_proxy/`** 目录下，直接双击即可执行：

| 脚本文件 | 说明与用途 |
| :--- | :--- |
| **`打开Web日志看板.bat`**<br>(或 `codearts_proxy/dashboard.bat`) | **【实时图形化监控看板】**<br>双击在默认浏览器中打开 Web 动态看板 (`/dashboard`)，包含服务与内核指标、Token 消耗统计、请求列表、完整提示词与思考链展开 |
| **`查看实时终端日志.bat`**<br>(或 `codearts_proxy/logs.bat`) | **【实时终端滚屏监控】**<br>双击打开黑色终端窗口，像 `tail -f` 一样实时动态滚屏显示每一次收发请求的协议、模型、提示词与耗时 |
| **`一键切换CodeArts代理.bat`**<br>(或 `codearts_proxy/toggle.bat`) | **【智能单键开关】**<br>• 若服务**未运行**：双击自动启动服务并探活<br>• 若服务**正在运行**：双击自动停止服务并释放端口<br>无需关心当前运行状态，双击即可做翻转操作 |
| **`检查CodeArts代理状态.bat`**<br>(或 `codearts_proxy/status.bat`) | **【健康度与状态检查】**<br>双击即时检查代理运行状态（PID、监听端口）、CodeArts 内核端口连通性及当前已就绪的可用模型列表 |
| **`启动CodeArts代理.bat`**<br>(或 `codearts_proxy/start.bat`) | **【启动后台服务】**<br>以后台静默方式启动代理服务（关闭弹出的黑色窗口不会终止后台代理） |
| **`停止CodeArts代理.bat`**<br>(或 `codearts_proxy/stop.bat`) | **【停止后台服务】**<br>安全退出后台代理进程并释放 17129 端口 |

### 2. 命令行控制方式

**前台调试运行（控制台实时打印日志）：**
```powershell
node codearts_proxy/src/index.ts
```

**PowerShell 后台启停：**
```powershell
# 启动后台服务
powershell -ExecutionPolicy Bypass -File codearts_proxy/scripts/start-windows.ps1

# 停止后台服务
powershell -ExecutionPolicy Bypass -File codearts_proxy/scripts/stop-windows.ps1

# 查看健康状态
powershell -ExecutionPolicy Bypass -File codearts_proxy/scripts/status-windows.ps1

# 智能切换启停
powershell -ExecutionPolicy Bypass -File codearts_proxy/scripts/toggle-windows.ps1
```

---

## 三、客户端接入配置

服务默认运行在：`http://127.0.0.1:17129`

### 1. Cursor / Windsurf / Continue (OpenAI 兼容客户端)

在客户端的模型设置中，添加自定义 OpenAI 兼容提供商：
- **Base URL**: `http://127.0.0.1:17129/v1`
- **API Key**: `codearts-key`（任意填入非空字符即可）
- **Model ID**:
  - `deepseek-v4-pro-0813`（推荐：高阶编程与深度思考）
  - `glm-5.3-flash`（快速响应与多模态图文）
  - `openpangu-2.0-pro`（OpenPangu 盘古模型）
  - `claude-3-7-sonnet`（自动路由至 deepseek-v4-pro-0813）

### 2. Cline (VS Code 扩展)

- **API Provider**: `OpenAI Compatible`
- **Base URL**: `http://127.0.0.1:17129/v1`
- **API Key**: 任意非空字符（如 `dummy`）
- **Model ID**: `deepseek-v4-pro-0813`

### 3. Claude Code CLI (Anthropic 兼容)

通过环境变量将 Claude Code 指向本地代理端点即可：
```powershell
# Windows PowerShell
$env:ANTHROPIC_BASE_URL="http://127.0.0.1:17129"
$env:ANTHROPIC_API_KEY="dummy"
claude
```

---

## 四、接口诊断与健康检查

### 1. 健康状态探活
```bash
curl http://127.0.0.1:17129/health
```

### 2. 查询已挂载模型列表
```bash
curl http://127.0.0.1:17129/v1/models
```

### 3. 测试标准 OpenAI 对话
```bash
curl http://127.0.0.1:17129/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v4-pro-0813",
    "messages": [{"role": "user", "content": "你好，请做个自我介绍"}]
  }'
```

### 4. 测试标准 Anthropic 对话
```bash
curl http://127.0.0.1:17129/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-7-sonnet",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "你好！"}]
  }'
```
