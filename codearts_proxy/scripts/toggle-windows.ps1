# Toggle codearts-proxy: if running -> stop; if not running -> start.
param(
  [int]$Port = 17129
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

if ($conn) {
  Write-Host "=======================================================" -ForegroundColor Yellow
  Write-Host "  CodeArts Proxy (端口 $Port) 正在运行，正在停止..." -ForegroundColor Yellow
  Write-Host "=======================================================" -ForegroundColor Yellow
  Write-Host ""
  & (Join-Path $ScriptDir "stop-windows.ps1") -Port $Port
} else {
  Write-Host "=======================================================" -ForegroundColor Cyan
  Write-Host "  CodeArts Proxy 未运行，正在启动后台服务..." -ForegroundColor Cyan
  Write-Host "=======================================================" -ForegroundColor Cyan
  Write-Host ""
  & (Join-Path $ScriptDir "start-windows.ps1") -Port $Port
}
