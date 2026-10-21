# Open CodeArts Proxy Web Dashboard in default browser
param(
  [int]$Port = 17129
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

if (-not $conn) {
  Write-Host "[*] 检测到代理服务未运行，正在自动启动后台服务..." -ForegroundColor Cyan
  & (Join-Path $ScriptDir "start-windows.ps1") -Port $Port
}

$url = "http://127.0.0.1:$Port/dashboard"
Write-Host "[✓] 正在打开实时日志与监控看板: $url" -ForegroundColor Green
Start-Process $url
