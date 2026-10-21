# Stop the codearts-proxy process on Windows.

param(
  [int]$Port = 17129
)

$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $conn) {
  Write-Host "No proxy listening on port $Port."
  exit 0
}

$procId = $conn.OwningProcess | Select-Object -First 1
Stop-Process -Id $procId -Force
Write-Host "Stopped codearts-proxy (PID $procId) on port $Port."
