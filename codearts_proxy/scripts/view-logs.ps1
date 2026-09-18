# Live interactive console log monitor for codearts-proxy
param(
  [string]$LogFile = "proxy.log",
  [int]$Port = 17129
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$LogPath = Join-Path $ProjectRoot $LogFile

$host.UI.RawUI.WindowTitle = "CodeArts Proxy - 实时交互日志监控"

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "      CodeArts Proxy - 实时控制台交互日志监控" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  日志文件: $LogPath" -ForegroundColor DarkGray
Write-Host "  Web 看板: http://127.0.0.1:$Port/dashboard" -ForegroundColor DarkGray
Write-Host "  提示: 客户端 (Cursor/Cline/Claude) 发送请求时，此处将实时滚屏输出。" -ForegroundColor Yellow
Write-Host "  按 Ctrl+C 可随时退出监控（不影响后台代理运行）" -ForegroundColor DarkGray
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $LogPath)) {
  New-Item -ItemType File -Path $LogPath -Force | Out-Null
}

Get-Content -Path $LogPath -Wait -Tail 40
