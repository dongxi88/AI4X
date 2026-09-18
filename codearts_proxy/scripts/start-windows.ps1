# Start the codearts-proxy server as a hidden background process on Windows.

param(
  [string]$EntryFile = "src\index.ts",
  [string]$LogFile = "proxy.log",
  [int]$Port = 17129
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$EntryPath = Join-Path $ProjectRoot $EntryFile
$LogPath = Join-Path $ProjectRoot $LogFile

if (-not (Test-Path $EntryPath)) {
  Write-Error "Entry file not found at $EntryPath."
  exit 1
}

# Check if already running on the port
$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
  $procId = $existing.OwningProcess | Select-Object -First 1
  Write-Host "codearts-proxy is already running on port $Port (PID $procId)."
  try {
    $status = Invoke-RestMethod "http://127.0.0.1:$Port/health" -ErrorAction SilentlyContinue
    Write-Host "Status: $($status | ConvertTo-Json -Compress)"
  } catch {}
  exit 0
}

# Start hidden node process
$env:CODEARTS_PROXY_PORT = "$Port"
$proc = Start-Process -FilePath "node" `
  -ArgumentList "$EntryPath" `
  -WorkingDirectory $ProjectRoot `
  -WindowStyle Hidden `
  -RedirectStandardOutput $LogPath `
  -RedirectStandardError "$LogPath.err" `
  -PassThru

Start-Sleep -Seconds 2

# Verify it came up
$check = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($check) {
  Write-Host "codearts-proxy successfully started in background (PID $($proc.Id))."
  Write-Host "  URL:   http://127.0.0.1:$Port/v1"
  Write-Host "  Logs:  $LogPath (and $LogPath.err)"
  try {
    $status = Invoke-RestMethod "http://127.0.0.1:$Port/health" -ErrorAction SilentlyContinue
    Write-Host "  Health: $($status | ConvertTo-Json -Compress)"
  } catch {}
} else {
  Write-Error "Failed to start codearts-proxy. Check $LogPath.err for details."
  exit 1
}
