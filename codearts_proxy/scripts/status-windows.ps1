# Health & status checker for CodeArts Proxy
param(
  [int]$Port = 17129
)

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "        CodeArts AI 代理服务状态与健康度检查" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

if (-not $conn) {
  Write-Host "[!] 代理服务状态: 未运行 (端口 $Port 空闲)" -ForegroundColor Red
  Write-Host ""
  Write-Host "提示: 可双击运行【启动CodeArts代理.bat】启动服务。" -ForegroundColor Yellow
  return
}

$procId = $conn.OwningProcess | Select-Object -First 1
Write-Host "[+] 代理服务进程: 运行中 (PID: $procId, 监听端口: $Port)" -ForegroundColor Green
Write-Host "    OpenAI API 地址:    http://127.0.0.1:$Port/v1"
Write-Host "    Anthropic API 地址: http://127.0.0.1:$Port"
Write-Host ""

try {
  $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 5 -ErrorAction Stop
  Write-Host "---【CodeArts 内核通信状态】---" -ForegroundColor Cyan
  if ($health.kernel.connected) {
    Write-Host "  内核连接状态:  正常通信" -ForegroundColor Green
    Write-Host "  内核动态端口:  $($health.kernel.port)" -ForegroundColor Green
    $models = $health.kernel.models
    Write-Host "  可用模型总数:  $($models.Count) 个" -ForegroundColor Green
    Write-Host ""
    Write-Host "---【当前已就绪模型】---" -ForegroundColor Cyan
    foreach ($m in $models) {
      if ($m -eq "deepseek-v4-pro-0813") {
        Write-Host "  * $m (主力推荐: 深度推理/复杂代码编程)" -ForegroundColor Yellow
      } elseif ($m -eq "glm-5.3-flash") {
        Write-Host "  * $m (极速推荐: 极速响应/多模态理解绘图)" -ForegroundColor Yellow
      } elseif ($m -like "openpangu*") {
        Write-Host "  * $m (OpenPangu 盘古基础模型)"
      } else {
        Write-Host "  * $m"
      }
    }
  } else {
    Write-Host "  内核连接状态:  未连接" -ForegroundColor Red
    Write-Host "  提示: 请检查 CodeArts 桌面端是否已启动并正常运行。" -ForegroundColor Yellow
  }
} catch {
  Write-Host "[!] 获取健康状态响应失败: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
