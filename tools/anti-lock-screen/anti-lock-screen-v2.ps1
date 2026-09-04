# Anti Screen Lock Script v2
# Uses keybd_event for more reliable key simulation
#
# Usage:
#   .\anti-lock-screen-v2.ps1            # debug mode: shows popup + console output
#   .\anti-lock-screen-v2.ps1 -Silent   # silent mode: no popup, no console, log only

param(
    [int]$IntervalSeconds = 60,
    [switch]$Silent
)

$logDir = Join-Path $PSScriptRoot "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}
$logFile = Join-Path $logDir "anti-lock.log"

if (-not $Silent) {
    Write-Host "=== Anti Lock Screen v2 Started (interval: $IntervalSeconds sec) ===" -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
}

# Define key simulation type
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class KeySim {
    [DllImport("user32.dll", SetLastError = true)]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);

    public const byte VK_PAUSE = 0x13;
    public const uint KEYEVENTF_KEYDOWN = 0x0000;
    public const uint KEYEVENTF_KEYUP = 0x0002;

    public static void PressPause() {
        keybd_event(VK_PAUSE, 0, KEYEVENTF_KEYDOWN, UIntPtr.Zero);
        keybd_event(VK_PAUSE, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
    }
}
"@

function Log-Msg {
    param([string]$Msg)
    $ts = Get-Date -Format "HH:mm:ss"
    "$ts $Msg" | Out-File -FilePath $logFile -Append
}

# Show green "A" popup at top-left (debug mode only)
function Show-GreenIcon {
    try {
        Add-Type -AssemblyName System.Windows.Forms

        $form = New-Object System.Windows.Forms.Form
        $form.Text = "Anti-Lock"
        $form.Size = New-Object System.Drawing.Size(80, 80)
        $form.StartPosition = "Manual"
        $form.Location = New-Object System.Drawing.Point(10, 10)
        $form.FormBorderStyle = "None"
        $form.TopMost = $true
        $form.ShowInTaskbar = $false
        $form.BackColor = [System.Drawing.Color]::FromArgb(34, 139, 34)

        $label = New-Object System.Windows.Forms.Label
        $label.Text = "A"
        $label.Font = New-Object System.Drawing.Font("Arial", 36, [System.Drawing.FontStyle]::Bold)
        $label.ForeColor = [System.Drawing.Color]::White
        $label.AutoSize = $false
        $label.Size = $form.Size
        $label.TextAlign = "MiddleCenter"
        $form.Controls.Add($label)

        $form.Show()
        Start-Sleep -Milliseconds 2000
        $form.Close()
        $form.Dispose()
        Log-Msg "Green icon shown"
    } catch {
        Log-Msg "Green icon error: $($_.Exception.Message)"
    }
}

# Toast notification (debug mode only)
function Show-Toast {
    param([string]$Message)

    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

        $template = @"
<toast>
    <visual>
        <binding template="ToastText02">
            <text id="1">Anti-Lock</text>
            <text id="2">$Message</text>
        </binding>
    </visual>
</toast>
"@
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("AntiLock").Show($toast)
        Log-Msg "Toast shown: $Message"
    } catch {
        Log-Msg "Toast error: $($_.Exception.Message)"
    }
}

$random = New-Object System.Random

$mode = if ($Silent) { "silent" } else { "debug" }
Log-Msg "Script started (mode: $mode, PID: $PID, random interval 1-5 min)"

try {
    while ($true) {
        # Send Pause key
        [KeySim]::PressPause()
        Log-Msg "Pause key sent"

        # Show green icon and toast only in debug mode
        if (-not $Silent) {
            Show-GreenIcon
            Show-Toast -Message "Anti-Lock active"
        }

        # Random interval between 60 and 300 seconds (1-5 minutes)
        $IntervalSeconds = $random.Next(60, 301)
        Log-Msg "Next run in $IntervalSeconds seconds"
        Start-Sleep -Seconds $IntervalSeconds
    }
} finally {
    Log-Msg "Script stopped"
}
