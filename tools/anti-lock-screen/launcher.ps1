[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Clear-Host

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "          防锁屏工具启动器 (Anti-Lock Screen)         " -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  [1] 后台静默运行 (推荐，无窗口/弹窗，日志写入 logs 目录)"
Write-Host "  [2] 前台调试运行 (显示绿色提示窗、Toast 通知与控制台)"
Write-Host "  [3] 停止正在运行的防锁屏进程"
Write-Host "  [Q] 退出启动器"
Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "提示: 10 秒内未按键将自动进入 [2] 前台调试运行" -ForegroundColor Yellow
Write-Host ""

$timeout = 10
$choice = $null

while ($timeout -gt 0) {
    # 动态在同一行刷新倒计时
    Write-Host -NoNewline ("`r倒计时 [{0,2}s] 自动选择 [2] | 请按数字键 [1, 2, 3]: " -f $timeout)
    
    # 1秒内细分为10次检查，提高按键响应速度（100ms延迟内响应）
    for ($i = 0; $i -lt 10; $i++) {
        $keyAvailable = $false
        try {
            $keyAvailable = [Console]::KeyAvailable
        } catch {
            $keyAvailable = $false
        }

        if ($keyAvailable) {
            $keyInfo = [Console]::ReadKey($true)
            $char = $keyInfo.KeyChar.ToString()
            if ($char -in '1', '2', '3') {
                $choice = $char
                break
            } elseif ($char -in 'q', 'Q' -or $keyInfo.Key -eq [ConsoleKey]::Escape) {
                Write-Host "`r已取消并退出。                                            " -ForegroundColor Gray
                exit 0
            }
        }
        Start-Sleep -Milliseconds 100
    }

    if ($choice) { break }
    $timeout--
}

if (-not $choice) {
    $choice = '2'
    Write-Host ("`r倒计时结束 [ 0s]，已自动选择 [2] 前台调试运行!                    ") -ForegroundColor Yellow
} else {
    Write-Host ("`r您已选择 [{0}]!                                                    " -f $choice) -ForegroundColor Green
}
Write-Host ""

$scriptPath = Join-Path $PSScriptRoot "anti-lock-screen-v2.ps1"

switch ($choice) {
    '1' {
        Write-Host "正在启动后台静默进程..." -ForegroundColor Cyan
        Start-Process powershell.exe -WindowStyle Hidden -ArgumentList "-ExecutionPolicy Bypass -File `"$scriptPath`" -Silent"
        Write-Host "后台静默进程已启动成功！(日志保存在 tools/anti-lock-screen/logs 目录)" -ForegroundColor Green
        Start-Sleep -Seconds 2
        exit 0
    }
    '2' {
        Write-Host "正在以前台调试模式启动（按 Ctrl+C 可停止）..." -ForegroundColor Cyan
        Write-Host ""
        & powershell.exe -ExecutionPolicy Bypass -File $scriptPath
    }
    '3' {
        Write-Host "正在停止所有正在运行的防锁屏进程..." -ForegroundColor Cyan
        $procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*anti-lock-screen-v2.ps1*' }
        if ($procs) {
            $procs | ForEach-Object {
                Stop-Process -Id $_.ProcessId -Force
                Write-Host ("已终止防锁屏进程 PID: {0}" -f $_.ProcessId) -ForegroundColor Yellow
            }
            Write-Host "防锁屏进程已全部停止。" -ForegroundColor Green
        } else {
            Write-Host "未检测到正在运行的防锁屏进程。" -ForegroundColor Gray
        }
        Write-Host ""
        Write-Host "按任意键退出..."
        try { $null = [Console]::ReadKey($true) } catch {}
        exit 0
    }
}