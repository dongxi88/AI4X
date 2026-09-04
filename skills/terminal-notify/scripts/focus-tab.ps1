# toast 点击回调：把 Windows Terminal 切到指定标签
#   由 claudecode: 协议触发，URI 形如 claudecode://focus/<session_id>

param([string]$Uri)

$ErrorActionPreference = 'SilentlyContinue'

$sid = ''
if ($Uri -match 'focus/([^/?#]+)') { $sid = $matches[1] }

# 会话 -> 标签索引 的映射由 notify.ps1 -Event Active 写入
$map = Join-Path $env:TEMP 'claude-tab-map.json'
$idx = -1
$hwndWanted = 0
if ($sid -and (Test-Path -LiteralPath $map)) {
    try {
        $m = [IO.File]::ReadAllText($map, [Text.Encoding]::UTF8) | ConvertFrom-Json
        $rec = $m.$sid
        if ($rec) { $idx = [int]$rec.index; $hwndWanted = [int64]$rec.hwnd }
    } catch { }
}

Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
Add-Type -Namespace CCFocus -Name W -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
[DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
[DllImport("kernel32.dll")] public static extern int GetCurrentThreadId();
[DllImport("user32.dll")] public static extern bool AttachThreadInput(int a, int b, bool f);
public delegate bool EnumProc(IntPtr h, IntPtr p);
'@

# 找到所有 Windows Terminal 顶层窗口
$wins = @()
$cb = [CCFocus.W+EnumProc] {
    param($h, $p)
    if ([CCFocus.W]::IsWindowVisible($h)) {
        $c = New-Object Text.StringBuilder 256
        [void][CCFocus.W]::GetClassNameW($h, $c, 256)
        if ($c.ToString() -like '*CASCADIA*') { $script:wins += $h }
    }
    return $true
}
[void][CCFocus.W]::EnumWindows($cb, [IntPtr]::Zero)
if (-not $wins.Count) { exit 0 }

# 优先用记录的窗口句柄，否则用第一个
$target = $wins | Where-Object { [int64]$_ -eq $hwndWanted } | Select-Object -First 1
if (-not $target) { $target = $wins[0] }

# 先把窗口拉到前台（AttachThreadInput 绕过前台锁定限制）
try {
    if ([CCFocus.W]::IsIconic($target)) { [void][CCFocus.W]::ShowWindow($target, 9) }
    $fgPid = 0
    $fgThread = [CCFocus.W]::GetWindowThreadProcessId([CCFocus.W]::GetForegroundWindow(), [ref]$fgPid)
    $myThread = [CCFocus.W]::GetCurrentThreadId()
    [void][CCFocus.W]::AttachThreadInput($myThread, $fgThread, $true)
    [void][CCFocus.W]::SetForegroundWindow($target)
    [void][CCFocus.W]::AttachThreadInput($myThread, $fgThread, $false)
} catch { }

# 再切到目标标签
if ($idx -ge 0) {
    try {
        $root = [Windows.Automation.AutomationElement]::FromHandle($target)
        $cond = New-Object Windows.Automation.PropertyCondition(
            [Windows.Automation.AutomationElement]::ControlTypeProperty,
            [Windows.Automation.ControlType]::TabItem)
        $tabs = @($root.FindAll([Windows.Automation.TreeScope]::Descendants, $cond))
        if ($idx -lt $tabs.Count) {
            $tabs[$idx].GetCurrentPattern([Windows.Automation.SelectionItemPattern]::Pattern).Select()
        }
    } catch { }
}
exit 0
