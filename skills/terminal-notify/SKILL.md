---
name: terminal-notify
description: 为 Claude Code 配置 Windows 终端通知 —— 当承载 Claude Code 的终端窗口不在前台（或所在标签页非当前活动标签）时，任务完成 / 需要确认会弹出 Windows 通知，点击可跳回对应标签页。适用于「配置终端通知」「Claude 完成时提醒我」「后台标签提醒」「装一下通知 hook」等需求，也用于排查通知不弹、跳转失效等问题。仅 Windows。
---

# Claude Code 终端通知

给 Claude Code 装两个 hook：终端不在前台时弹 Windows 通知，点击跳回对应标签页。

## 安装

先确认在 Windows 上（`$env:OS` 为 `Windows_NT`），然后直接跑安装脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<skill目录>/scripts/install.ps1"
```

脚本是幂等的，重复执行安全，会自动备份 `settings.json`。

常用参数：

| 参数 | 用途 |
|---|---|
| `-DryRun` | 只检查不改动，先看会做什么 |
| `-NoClickJump` | 不装点击跳转，只要通知 |
| `-Uninstall` | 卸载（移除 hooks、协议、脚本） |

装完告诉用户：**需要重启 Claude Code 才生效**（hooks 在会话启动时加载）。

## 装了什么

| Hook 事件 | 触发时机 | 行为 |
|---|---|---|
| `Notification` | 需要权限确认 / 等待输入 | 🔔 弹通知 |
| `Stop` | 一轮回答结束 | ✅ 弹通知（附回复结尾摘要） |
| `UserPromptSubmit` | 用户输入时 | 静默记录「当前活动标签」 |

文件落位：
- `<配置目录>/hooks/notify.ps1` —— 通知主脚本
- `<配置目录>/hooks/focus-tab.ps1` —— 点击跳转回调
- 注册表 `HKCU:\Software\Classes\claudecode` —— 自定义协议

## 静默规则

只有**同时满足**「终端窗口在前台」且「本会话是最后输入的标签」时才不打扰。
即：切到别的应用会提醒，切到隔壁标签页也会提醒。

临时关闭：设 `CLAUDE_NOTIFY_DISABLE=1`。

## 排障

**通知不弹**
1. 检查 Windows 通知开关：设置 → 系统 → 通知，确认「专注助手/免打扰」没开
2. 手动跑一次看报错（去掉 `-WindowStyle Hidden`）：
   ```powershell
   '{"session_id":"test","cwd":"C:\\tmp","message":"测试"}' | `
     powershell -NoProfile -File "$env:USERPROFILE\.claude\hooks\notify.ps1" -Event Notification
   ```
   注意：终端在前台时会被有意抑制，属正常。测试时先切到别的窗口。
3. 确认用的是 `powershell.exe`（5.1）而非 `pwsh`（见下方限制）

**通知弹了但点击不跳转**
- 非 Windows Terminal 终端不支持，属预期降级
- 检查协议：`Test-Path 'HKCU:\Software\Classes\claudecode'`
- 检查标签映射：`Get-Content "$env:TEMP\claude-tab-map.json"`，映射在用户输入时才写入，新会话需先输入一次

**脚本报大量语法错误** —— 八成是 UTF-8 BOM 丢了，重跑 `install.ps1` 会自动修复。

## 实现限制

这些是实测确认的边界，改动脚本时注意：

1. **必须用 `powershell.exe` 5.1 弹通知。** PowerShell 7（含 preview）加载不了 WinRT 类型，`.NET Core` 移除了内置投影。install.ps1 里硬编码了 5.1 路径，不要改成 `pwsh`。

2. **脚本文件必须带 UTF-8 BOM。** PS 5.1 在中文（GBK）环境下会把无 BOM 的 UTF-8 按 GBK 解码，导致整片语法错误。用 `[IO.File]::WriteAllBytes` 写入并显式加 `0xEF 0xBB 0xBF`。

3. **标签跳转靠索引，不是标签身份。** UI Automation 拿不到「标签 ↔ 进程」映射（RuntimeId / AutomationId 都不含进程信息）。若用户在收到通知后关闭或拖动重排标签，点击会跳错位置。索引在每次输入时刷新。

4. **无法真正判断「哪个标签是活动的」属于哪个会话。** WT 所有标签共用一个进程；hook 里也拿不到 tty（`/dev/tty` 不可用）。折衷方案是「最后输入的会话 = 你正在看的标签」，用 `$env:TEMP\claude-active-session.txt` 打戳比对。已知误报：开着某标签但长时间不输入时，该标签的通知仍会弹。

5. **`cwd` 会漂移，不能用作项目名。** shell 里的 `cd`（包括 Bash 工具切目录）会改变 payload 里的 `cwd`。notify.ps1 改从 transcript 首条记录读会话启动目录，`cwd` 仅作兜底。

6. **合并 `settings.json` 不能整体覆盖。** 里面通常还有 model / env / permissions / statusLine / enabledPlugins。install.ps1 只增删 `hooks` 下的三个键，并在写入前备份。注意 `ConvertFrom-Json -AsHashtable` 是 PS 7 专属参数，安装脚本为兼容 5.1 没有使用。
