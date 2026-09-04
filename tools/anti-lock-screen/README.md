# Anti-Lock Screen (防锁屏工具)

通过模拟按键（Pause 键）防止 Windows 自动息屏/睡眠/锁屏，支持静默后台运行与日志记录。

## 一键启动方式

- **`start-silent.bat`**：双击即可在后台静默运行（无窗口、无弹窗干扰，日志输出在当前目录 `logs/`）。
- **`start.bat`**：启动菜单，支持选择后台运行、前台调试运行、以及一键停止后台进程。
- **`stop.bat`**：双击一键停止后台运行的防锁屏进程。

## 手动运行方式 (PowerShell)

在当前目录下打开 PowerShell：

1. **后台静默运行**：
   ```powershell
   Start-Process powershell -WindowStyle Hidden -ArgumentList "-ExecutionPolicy Bypass -File `"$PSScriptRoot\anti-lock-screen-v2.ps1`" -Silent"
   ```

2. **前台调试运行（带提示窗口与Toast通知）**：
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\anti-lock-screen-v2.ps1
   ```
