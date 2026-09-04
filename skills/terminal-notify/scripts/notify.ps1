# Claude Code 终端通知 hook
#   用法: powershell -NoProfile -ExecutionPolicy Bypass -File notify.ps1 -Event Notification|Stop
#   仅当承载 Claude Code 的终端窗口"不在前台"时才弹 Windows 通知。
#   设置环境变量 CLAUDE_NOTIFY_DISABLE=1 可临时关闭。

param([ValidateSet('Notification', 'Stop', 'Active')][string]$Event = 'Notification')

$ErrorActionPreference = 'Stop'
if ($env:CLAUDE_NOTIFY_DISABLE -eq '1') { exit 0 }

# ---------- 1. 读取 hook 的 stdin（按 UTF-8 解码，避免中文乱码） ----------
$payload = $null
try {
    $stdin = [Console]::OpenStandardInput()
    $buf = New-Object System.IO.MemoryStream
    $stdin.CopyTo($buf)
    $raw = [Text.Encoding]::UTF8.GetString($buf.ToArray())
    if ($raw.Trim()) { $payload = $raw | ConvertFrom-Json }
} catch { }

# ---------- 2. 活动标签追踪 ----------
# Windows Terminal 所有标签共用一个进程，API 无法区分「哪个标签是活动的」。
# 折衷：你最后输入的那个会话 = 你正在看的标签。UserPromptSubmit 打戳，通知时比对。
$stampFile = Join-Path $env:TEMP 'claude-active-session.txt'
$sid = if ($payload.session_id) { [string]$payload.session_id } else { '' }

# 记录「本会话 = 哪个窗口的第几个标签」。只在你输入时调用，此刻活动标签必定是本会话。
function Save-TabLocation([string]$sessionId) {
    Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes -EA Stop
    Add-Type -Namespace CCTab -Name W -MemberDefinition @'
[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, System.Text.StringBuilder s, int n);
'@ -EA Stop

    $hwnd = [CCTab.W]::GetForegroundWindow()
    $cls = New-Object Text.StringBuilder 256
    [void][CCTab.W]::GetClassNameW($hwnd, $cls, 256)
    if ($cls.ToString() -notlike '*CASCADIA*') { return }   # 不是 Windows Terminal，跳过

    $root = [Windows.Automation.AutomationElement]::FromHandle($hwnd)
    $cond = New-Object Windows.Automation.PropertyCondition(
        [Windows.Automation.AutomationElement]::ControlTypeProperty,
        [Windows.Automation.ControlType]::TabItem)
    $tabs = @($root.FindAll([Windows.Automation.TreeScope]::Descendants, $cond))

    $idx = -1
    for ($i = 0; $i -lt $tabs.Count; $i++) {
        $sel = $false
        try { $sel = $tabs[$i].GetCurrentPattern([Windows.Automation.SelectionItemPattern]::Pattern).Current.IsSelected } catch { }
        if ($sel) { $idx = $i; break }
    }
    if ($idx -lt 0) { return }

    $mapFile = Join-Path $env:TEMP 'claude-tab-map.json'
    $map = @{}
    if (Test-Path -LiteralPath $mapFile) {
        try {
            $o = [IO.File]::ReadAllText($mapFile, [Text.Encoding]::UTF8) | ConvertFrom-Json
            foreach ($p in $o.PSObject.Properties) { $map[$p.Name] = $p.Value }
        } catch { }
    }
    $map[$sessionId] = [pscustomobject]@{ index = $idx; hwnd = [int64]$hwnd }
    [IO.File]::WriteAllText($mapFile, ($map | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding $false))
}

if ($Event -eq 'Active') {
    if ($sid) {
        try { Set-Content -LiteralPath $stampFile -Value $sid -NoNewline -Encoding ASCII } catch { }
        # 记录本会话当前所在的标签索引，供 toast 点击时跳回
        try { Save-TabLocation $sid } catch { }
    }
    exit 0
}

function Test-IsActiveTab {
    if (-not $sid) { return $true }   # 无 session_id 时不做标签判断
    try {
        if (-not (Test-Path -LiteralPath $stampFile)) { return $true }
        return ((Get-Content -LiteralPath $stampFile -Raw).Trim() -eq $sid)
    } catch { return $true }
}

# ---------- 3. 判断承载终端是否在前台 ----------
function Test-TerminalForeground {
    Add-Type -Namespace ClaudeNotify -Name Win -MemberDefinition @'
[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
[DllImport("kernel32.dll")] public static extern IntPtr CreateToolhelp32Snapshot(uint flags, uint pid);
[DllImport("kernel32.dll")] public static extern bool Process32First(IntPtr h, ref PROCESSENTRY32 e);
[DllImport("kernel32.dll")] public static extern bool Process32Next(IntPtr h, ref PROCESSENTRY32 e);
[DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);
[StructLayout(LayoutKind.Sequential, CharSet=CharSet.Ansi)]
public struct PROCESSENTRY32 {
  public uint dwSize; public uint cntUsage; public uint th32ProcessID;
  public IntPtr th32DefaultHeapID; public uint th32ModuleID; public uint cntThreads;
  public uint th32ParentProcessID; public int pcPriClassBase; public uint dwFlags;
  [MarshalAs(UnmanagedType.ByValTStr, SizeConst=260)] public string szExeFile;
}
'@ -UsingNamespace System.Runtime.InteropServices

    $fgPid = 0
    [void][ClaudeNotify.Win]::GetWindowThreadProcessId([ClaudeNotify.Win]::GetForegroundWindow(), [ref]$fgPid)
    if ($fgPid -le 0) { return $false }   # 无前台窗口（锁屏等）-> 视为不在前台

    # 一次快照取全部 pid->ppid，然后在内存里向上走祖先链
    $parent = @{}
    $snap = [ClaudeNotify.Win]::CreateToolhelp32Snapshot(2, 0)   # TH32CS_SNAPPROCESS
    try {
        $e = New-Object ClaudeNotify.Win+PROCESSENTRY32
        $e.dwSize = [Runtime.InteropServices.Marshal]::SizeOf($e)
        if ([ClaudeNotify.Win]::Process32First($snap, [ref]$e)) {
            do { $parent[[int]$e.th32ProcessID] = [int]$e.th32ParentProcessID }
            while ([ClaudeNotify.Win]::Process32Next($snap, [ref]$e))
        }
    } finally { [void][ClaudeNotify.Win]::CloseHandle($snap) }

    $cur = $PID
    for ($i = 0; $i -lt 16; $i++) {
        if ($cur -eq $fgPid) { return $true }      # 祖先中命中前台进程 => 终端在前台
        if (-not $parent.ContainsKey($cur)) { break }
        $next = $parent[$cur]
        if ($next -le 0 -or $next -eq $cur) { break }
        $cur = $next
    }
    return $false
}

# 仅当「窗口在前台」且「本会话是你最后输入的标签」时才静默
try { if ((Test-TerminalForeground) -and (Test-IsActiveTab)) { exit 0 } } catch { }

# ---------- 4. 组织通知内容 ----------
function Get-LastAssistantText([string]$path) {
    if (-not $path -or -not (Test-Path -LiteralPath $path)) { return $null }
    try {
        # 只读文件尾部，避免大 transcript 拖慢 hook
        $fs = [IO.File]::Open($path, 'Open', 'Read', 'ReadWrite')
        try {
            $take = [Math]::Min($fs.Length, 200KB)
            [void]$fs.Seek(-$take, 'End')
            $bytes = New-Object byte[] $take
            [void]$fs.Read($bytes, 0, $take)
        } finally { $fs.Dispose() }

        $lines = [Text.Encoding]::UTF8.GetString($bytes) -split "`n"
        for ($i = $lines.Count - 1; $i -ge 0; $i--) {
            $line = $lines[$i].Trim()
            if (-not $line.StartsWith('{')) { continue }
            try { $obj = $line | ConvertFrom-Json } catch { continue }
            if ($obj.type -ne 'assistant') { continue }
            $text = $obj.message.content | Where-Object { $_.type -eq 'text' } |
                    ForEach-Object { $_.text } | Select-Object -Last 1
            if ($text -and $text.Trim()) { return $text.Trim() }
        }
    } catch { }
    return $null
}

# 取回复的结尾（结论通常在最后），并清掉 markdown 噪声
function Format-Tail([string]$text) {
    if (-not $text) { return $null }

    # 代码块/表格/分隔线在通知里没有可读性，先去掉
    $text = $text -replace '(?s)```.*?```', ' '
    $text = $text -replace '`([^`]*)`', '$1'

    $lines = @()
    foreach ($raw in ($text -split "`n")) {
        $l = $raw.Trim()
        if (-not $l) { continue }
        if ($l -match '^\s*\|?\s*[-:\s|]+\s*\|?\s*$') { continue }   # 表格分隔/水平线
        $l = $l -replace '^\s*(#{1,6}|[-*+>]|\d+\.)\s*', ''          # 列表/标题/引用前缀
        $l = $l -replace '^\s*\|\s*', '' -replace '\s*\|\s*$', ''    # 表格首尾竖线
        $l = $l -replace '\*\*([^*]+)\*\*', '$1'                     # 粗体
        $l = $l -replace '(?<!\*)\*([^*]+)\*(?!\*)', '$1'            # 斜体
        $l = $l.Trim()
        if ($l) { $lines += $l }
    }
    if (-not $lines.Count) { return $null }

    # 末行够长就单独用；太短才往前补，避免把不相干的列表项拼进来
    $pick = @($lines[-1])
    for ($i = $lines.Count - 2; $i -ge 0 -and ($pick -join ' ').Length -lt 40 -and $pick.Count -lt 3; $i--) {
        $pick = , $lines[$i] + $pick
    }

    $s = ($pick -join ' ') -replace '\s+', ' '
    $s = $s.Trim()
    if ($s.Length -gt 158) { $s = '…' + $s.Substring($s.Length - 158) }   # 保留结尾
    return $s
}

# cwd 会随 shell 内的 cd 漂移（例如 Bash 工具切过目录），
# 用 transcript 首条记录里的启动目录作为项目名，回退到 payload.cwd
function Get-ProjectName {
    $p = $payload.transcript_path
    if ($p -and (Test-Path -LiteralPath $p)) {
        try {
            $n = 0
            foreach ($line in [IO.File]::ReadLines($p)) {
                $l = $line.Trim()
                if ($l.StartsWith('{')) {
                    try { $o = $l | ConvertFrom-Json } catch { $o = $null }
                    if ($o -and $o.cwd) { return Split-Path -Leaf ([string]$o.cwd) }
                }
                if (++$n -ge 40) { break }   # 只看开头几行
            }
        } catch { }
    }
    if ($payload.cwd) { return Split-Path -Leaf ([string]$payload.cwd) }
    return ''
}

$cwd = Get-ProjectName

if ($Event -eq 'Stop') {
    $title = if ($cwd) { "Claude Code · $cwd" } else { 'Claude Code' }
    $line1 = '✅ 任务完成'
    $line2 = Format-Tail (Get-LastAssistantText $payload.transcript_path)
    $sound = 'ms-winsoundevent:Notification.Default'
} else {
    $title = if ($cwd) { "Claude Code · $cwd" } else { 'Claude Code' }
    $line1 = '🔔 需要你的确认'
    $line2 = if ($payload.message) { [string]$payload.message } else { '等待输入' }
    $sound = 'ms-winsoundevent:Notification.Reminder'
}

if ($line2) {
    $line2 = ($line2 -replace '\s+', ' ').Trim()
    if ($line2.Length -gt 160) { $line2 = $line2.Substring(0, 160) + '…' }
}

# ---------- 5. 弹出 Windows 通知 ----------
$appId = 'ClaudeCode.Notify'
# 注册一次显示名，让通知中心显示 "Claude Code" 而不是 PowerShell
try {
    $key = 'HKCU:\Software\Classes\AppUserModelId\' + $appId
    if (-not (Test-Path $key)) {
        [void](New-Item -Path $key -Force)
        [void](New-ItemProperty -Path $key -Name DisplayName -Value 'Claude Code' -PropertyType String -Force)
    }
} catch { }

[void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
[void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime]

$esc = { param($s) [Security.SecurityElement]::Escape([string]$s) }
# 仅当本会话确实记录过标签位置时才让通知可点击（非 WT 终端不会有记录）
$launchUri = ''
if ($sid) {
    try {
        $mapFile = Join-Path $env:TEMP 'claude-tab-map.json'
        if (Test-Path -LiteralPath $mapFile) {
            $mm = [IO.File]::ReadAllText($mapFile, [Text.Encoding]::UTF8) | ConvertFrom-Json
            if ($mm.$sid) { $launchUri = "claudecode://focus/$sid" }
        }
    } catch { }
}
$body = "<text>$(& $esc $line1)</text>"
if ($line2) { $body += "<text>$(& $esc $line2)</text>" }

$xml = @"
<toast duration="short" activationType="protocol" launch="$(& $esc $launchUri)">
  <visual><binding template="ToastGeneric">
    <text>$(& $esc $title)</text>
    $body
  </binding></visual>
  <audio src="$sound"/>
</toast>
"@

$doc = New-Object Windows.Data.Xml.Dom.XmlDocument
$doc.LoadXml($xml)
$toast = New-Object Windows.UI.Notifications.ToastNotification $doc
$toast.Group = 'claude-code'
$toast.Tag = $Event
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
exit 0
