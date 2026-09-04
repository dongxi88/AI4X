# Claude Code 终端通知 —— 安装脚本
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1
#   参数: -Uninstall 卸载   -NoClickJump 不装点击跳转   -DryRun 只报告不改动
#
# 幂等：重复执行安全。会自动备份 settings.json。
# 兼容 PowerShell 5.1 与 7（不使用 7 专属的 ConvertFrom-Json -AsHashtable）。

[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$NoClickJump,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$ok = @(); $warn = @(); $fail = @()
function Say($m) { Write-Host $m }
function Good($m) { $script:ok += $m;   Write-Host "  [OK]   $m" -ForegroundColor Green }
function Warn($m) { $script:warn += $m; Write-Host "  [注意] $m" -ForegroundColor Yellow }
function Bad($m)  { $script:fail += $m; Write-Host "  [失败] $m" -ForegroundColor Red }

# ---------- 0. 路径 ----------
# 注意：Git Bash 的 $HOME 可能与 Windows 的 USERPROFILE 不同，这里一律以 Windows 侧为准
$cfgDir = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $env:USERPROFILE '.claude' }
$hooksDir = Join-Path $cfgDir 'hooks'
$settings = Join-Path $cfgDir 'settings.json'
$srcDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$notifyDst = Join-Path $hooksDir 'notify.ps1'
$focusDst  = Join-Path $hooksDir 'focus-tab.ps1'
# 通知必须用 Windows PowerShell 5.1：PS7(含 preview) 加载不了 WinRT，弹不出 toast
$ps51 = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'

Say ''
Say '=== Claude Code 终端通知 安装程序 ==='
Say "配置目录: $cfgDir"
if ($DryRun) { Say '(DryRun：只检查不改动)' }
Say ''

# ---------- 1. 环境检查 ----------
Say '[1/5] 检查环境'
if (-not (Test-Path $ps51)) {
    Bad "找不到 Windows PowerShell 5.1: $ps51"
    Say '   通知依赖它加载 WinRT，无法继续。'
    exit 1
}
Good "Windows PowerShell 5.1 就位"

# 探测 WinRT 是否真的可用（比只看文件存在更可靠）
$probe = & $ps51 -NoProfile -Command @'
try {
  [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime]
  'YES'
} catch { 'NO' }
'@ 2>$null
if ($probe -match 'YES') { Good 'WinRT 通知 API 可用' } else { Bad 'WinRT 通知 API 不可用（系统可能被精简）'; exit 1 }

# 终端类型：决定是否启用点击跳转
$isWT = [bool]$env:WT_SESSION
if ($isWT) {
    Good '检测到 Windows Terminal —— 支持点击跳转标签'
} else {
    Warn '非 Windows Terminal —— 通知正常，点击跳转不可用（自动降级）'
    $NoClickJump = $true
}

# ---------- 2. 卸载分支 ----------
if ($Uninstall) {
    Say ''
    Say '[卸载] 移除 hooks 配置与协议注册'
    if (Test-Path $settings) {
        $bak = "$settings.bak.uninstall-$(Get-Date -Format yyyyMMdd-HHmmss)"
        if (-not $DryRun) {
            Copy-Item $settings $bak -Force
            $j = Get-Content $settings -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($j.hooks) {
                foreach ($ev in @('Notification', 'Stop', 'UserPromptSubmit')) {
                    if ($j.hooks.PSObject.Properties.Name -contains $ev) {
                        $j.hooks.PSObject.Properties.Remove($ev)
                    }
                }
            }
            $out = $j | ConvertTo-Json -Depth 100
            [IO.File]::WriteAllText($settings, $out, (New-Object Text.UTF8Encoding $false))
        }
        Good "已移除 hooks（备份: $(Split-Path -Leaf $bak)）"
    }
    if (-not $DryRun) {
        Remove-Item 'HKCU:\Software\Classes\claudecode' -Recurse -Force -EA SilentlyContinue
        Remove-Item $notifyDst, $focusDst -Force -EA SilentlyContinue
        Remove-Item (Join-Path $env:TEMP 'claude-active-session.txt') -Force -EA SilentlyContinue
        Remove-Item (Join-Path $env:TEMP 'claude-tab-map.json') -Force -EA SilentlyContinue
    }
    Good '已移除协议注册与脚本'
    Say ''
    Say '卸载完成。重启 Claude Code 生效。'
    exit 0
}

# ---------- 3. 安装脚本文件 ----------
Say ''
Say '[2/5] 安装脚本'
if (-not (Test-Path $hooksDir)) {
    if (-not $DryRun) { New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null }
    Good "创建目录 $hooksDir"
}

# 关键：写入必须带 UTF-8 BOM。
# PS 5.1 在中文(GBK)环境下会把无 BOM 的 UTF-8 脚本按 GBK 解码，导致整片语法错误。
function Copy-WithBom($src, $dst) {
    if (-not (Test-Path $src)) { throw "源文件缺失: $src" }
    $bytes = [IO.File]::ReadAllBytes($src)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $out = $bytes
    } else {
        $out = [byte[]](0xEF, 0xBB, 0xBF) + $bytes
    }
    if (-not $DryRun) { [IO.File]::WriteAllBytes($dst, $out) }
}

Copy-WithBom (Join-Path $srcDir 'notify.ps1') $notifyDst
Good "notify.ps1 -> $notifyDst"
if (-not $NoClickJump) {
    Copy-WithBom (Join-Path $srcDir 'focus-tab.ps1') $focusDst
    Good "focus-tab.ps1 -> $focusDst"
}

# 装完立刻验证语法，避免编码问题留到运行时才暴露
if (-not $DryRun) {
    foreach ($f in @($notifyDst, $focusDst)) {
        if (-not (Test-Path $f)) { continue }
        $errs = $null
        [void][Management.Automation.Language.Parser]::ParseFile($f, [ref]$null, [ref]$errs)
        if ($errs) { Bad "$(Split-Path -Leaf $f) 语法错误: $($errs[0].Message)"; exit 1 }
    }
    Good '脚本语法校验通过'
}

# ---------- 4. 注册点击跳转协议 ----------
Say ''
Say '[3/5] 点击跳转'
if ($NoClickJump) {
    Warn '跳过（非 WT 或已用 -NoClickJump 指定）'
} else {
    $key = 'HKCU:\Software\Classes\claudecode'
    $cmd = "`"$ps51`" -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$focusDst`" -Uri `"%1`""
    if (-not $DryRun) {
        New-Item -Path $key -Force | Out-Null
        Set-ItemProperty -Path $key -Name '(Default)' -Value 'URL:Claude Code'
        Set-ItemProperty -Path $key -Name 'URL Protocol' -Value ''
        New-Item -Path "$key\shell\open\command" -Force | Out-Null
        Set-ItemProperty -Path "$key\shell\open\command" -Name '(Default)' -Value $cmd
    }
    Good '已注册 claudecode: 协议'
}

# ---------- 5. 合并 settings.json ----------
Say ''
Say '[4/5] 配置 hooks'
if (-not (Test-Path $settings)) {
    if (-not $DryRun) {
        [IO.File]::WriteAllText($settings, '{}', (New-Object Text.UTF8Encoding $false))
    }
    Good '创建 settings.json'
}

$bak = "$settings.bak.notify-$(Get-Date -Format yyyyMMdd-HHmmss)"
if (-not $DryRun) { Copy-Item $settings $bak -Force }
Good "已备份 -> $(Split-Path -Leaf $bak)"

# 合并而非覆盖：settings.json 里通常还有 model / env / permissions / statusLine 等，
# 整体重写会全部丢失。这里只增删 hooks 下的三个键。
$raw = Get-Content $settings -Raw -Encoding UTF8
if (-not $raw.Trim()) { $raw = '{}' }
$json = $raw | ConvertFrom-Json

$evMap = @{
    'Notification'     = 'Notification'
    'Stop'             = 'Stop'
    'UserPromptSubmit' = 'Active'
}

if (-not ($json.PSObject.Properties.Name -contains 'hooks') -or -not $json.hooks) {
    $json | Add-Member -NotePropertyName hooks -NotePropertyValue ([pscustomobject]@{}) -Force
}

$existingOther = @()
foreach ($ev in $evMap.Keys) {
    # 若该事件已有别的 hook（非本工具的），提示用户而不是静默覆盖
    if ($json.hooks.PSObject.Properties.Name -contains $ev) {
        $cur = $json.hooks.$ev | ConvertTo-Json -Depth 20 -Compress
        if ($cur -notmatch 'notify\.ps1') { $existingOther += $ev }
    }
    $entry = [pscustomobject]@{
        hooks = @([pscustomobject]@{
            type    = 'command'
            command = "`"$ps51`" -NoProfile -ExecutionPolicy Bypass -File `"$notifyDst`" -Event $($evMap[$ev])"
            timeout = 10
        })
    }
    $json.hooks | Add-Member -NotePropertyName $ev -NotePropertyValue @($entry) -Force
}

if ($existingOther.Count) {
    Warn "以下事件原有其它 hook，已被本工具替换: $($existingOther -join ', ')"
    Warn "如需保留，请从备份 $(Split-Path -Leaf $bak) 中手动合并"
}

if (-not $DryRun) {
    $out = $json | ConvertTo-Json -Depth 100
    [IO.File]::WriteAllText($settings, $out, (New-Object Text.UTF8Encoding $false))
}
Good '已写入 Notification / Stop / UserPromptSubmit'

# ---------- 6. 自检 ----------
Say ''
Say '[5/5] 自检'
if ($DryRun) {
    Warn 'DryRun 模式，跳过实际验证'
} else {
    # 确认原有配置没被写坏
    $verify = Get-Content $settings -Raw -Encoding UTF8 | ConvertFrom-Json
    $kept = @()
    foreach ($k in @('model', 'env', 'permissions', 'statusLine', 'enabledPlugins')) {
        if ($verify.PSObject.Properties.Name -contains $k) { $kept += $k }
    }
    if ($kept.Count) { Good "原有配置完好: $($kept -join ', ')" }
    if (-not $verify.hooks.Notification) { Bad 'hooks 写入失败' }

    # 真正弹一条通知验证链路
    $testPayload = @{
        session_id = 'install-selftest'
        cwd        = (Split-Path -Parent $cfgDir)
        message    = '安装成功 —— 这是一条测试通知'
    } | ConvertTo-Json -Compress
    $tmp = Join-Path $env:TEMP 'cc-notify-selftest.json'
    [IO.File]::WriteAllText($tmp, $testPayload, (New-Object Text.UTF8Encoding $false))
    # 用 cmd 重定向，确保 stdin 是文件而非管道对象
    & cmd /c "`"$ps51`" -NoProfile -ExecutionPolicy Bypass -File `"$notifyDst`" -Event Notification < `"$tmp`"" 2>&1 | Out-Null
    Remove-Item $tmp -Force -EA SilentlyContinue
    Good '已触发测试通知'
    Say '       (若终端在前台会被有意抑制 —— 这是正常行为)'
}

# ---------- 完成 ----------
Say ''
Say '================================'
if ($fail.Count) {
    Say "安装未完成：$($fail.Count) 项失败"
    exit 1
}
Say '安装完成'
Say ''
Say '生效方式: 重启 Claude Code（hooks 在会话启动时加载）'
Say '临时静音: 设置环境变量 CLAUDE_NOTIFY_DISABLE=1'
Say "卸载:     powershell -File `"$($MyInvocation.MyCommand.Path)`" -Uninstall"
if ($warn.Count) {
    Say ''
    Say "有 $($warn.Count) 条注意事项，见上方黄色提示"
}
Say ''
