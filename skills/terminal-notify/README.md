# Claude Code 终端通知

终端不在前台时弹 Windows 通知，点击跳回对应标签页。仅 Windows。

```
┌─────────────────────────────────────┐
│ Claude Code · my-project            │  ← 项目名
│ ✅ 任务完成                          │
│ …已通过全部测试，可以合并了。          │  ← 回复结尾摘要
└─────────────────────────────────────┘
```

## 安装

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install.ps1
```

重启 Claude Code 生效。

| 参数 | 用途 |
|---|---|
| `-DryRun` | 只检查不改动 |
| `-NoClickJump` | 只要通知，不装点击跳转 |
| `-Uninstall` | 卸载 |

在装了本 skill 的 Claude Code 里，直接说「帮我装终端通知」也可以。

## 静默规则

同时满足「窗口在前台」+「本会话是最后输入的标签」才不打扰。
切到别的应用会提醒，切到隔壁标签页也会提醒。

临时关闭：`$env:CLAUDE_NOTIFY_DISABLE = '1'`

## 手动安装

不想跑脚本的话：

1. 把 `scripts\notify.ps1`、`scripts\focus-tab.ps1` 拷到 `%USERPROFILE%\.claude\hooks\`
   —— **必须保留 UTF-8 BOM**，否则 PS 5.1 会按 GBK 解码报错

2. 在 `%USERPROFILE%\.claude\settings.json` 的 `hooks` 下加三项（**合并，别覆盖整个文件**）。
   注意 settings.json 里的 `%USERPROFILE%` **不会自动展开**，需替换成你的实际路径：

```json
{
  "hooks": {
    "Notification": [{ "hooks": [{ "type": "command", "timeout": 10,
      "command": "\"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe\" -NoProfile -ExecutionPolicy Bypass -File \"%USERPROFILE%\\.claude\\hooks\\notify.ps1\" -Event Notification" }] }],
    "Stop": [{ "hooks": [{ "type": "command", "timeout": 10,
      "command": "... -Event Stop" }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "timeout": 10,
      "command": "... -Event Active" }] }]
  }
}
```

3. 点击跳转需注册协议 `HKCU:\Software\Classes\claudecode`，指向 `focus-tab.ps1`（见 install.ps1 第 3 步）

## 已知限制

| 限制 | 说明 |
|---|---|
| 必须用 powershell.exe 5.1 | PS 7（含 preview）加载不了 WinRT，弹不出 toast |
| 脚本需带 UTF-8 BOM | 否则 PS 5.1 中文环境按 GBK 解码，语法整片报错 |
| 跳转靠标签索引 | 收到通知后关闭/重排标签会跳错位（索引在每次输入时刷新）|
| 仅 Windows Terminal 支持跳转 | 其他终端自动降级为只弹通知 |
| 长时间不输入的标签会误报 | 无法真正判断活动标签归属，折衷用「最后输入」近似 |

技术细节与排障见 `SKILL.md`。
