# Daily News Globe — one-shot Windows Task Scheduler setup.
#
# Usage:
#   .\setup_schedule.ps1 -SendKey "SCTxxxxxxxx"       # configure + test + register
#   .\setup_schedule.ps1 -SendKey "SCTxxx" -TestOnly  # just send a test push, no scheduling
#   .\setup_schedule.ps1 -Unregister                  # remove both scheduled tasks
#
# Registers:
#   GlobeNews-Server     — pythonw server.py at user login (background, no console)
#   GlobeNews-DailyPush  — python  push.py  every day at 08:00 (WeChat link push)
#
# Requires elevation? No — these tasks run as the current user.

param(
    [string]$SendKey,
    [switch]$TestOnly,
    [switch]$Unregister,
    [string]$DailyTime = "08:00"
)

$ErrorActionPreference = 'Stop'
$projectDir = $PSScriptRoot

function Get-PythonPath {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { throw "python.exe not found in PATH" }
    return $py.Source
}

function Get-PythonwPath {
    param([string]$PythonExe)
    $pythonw = Join-Path (Split-Path -Parent $PythonExe) "pythonw.exe"
    if (Test-Path $pythonw) { return $pythonw } else { return $PythonExe }
}

if ($Unregister) {
    foreach ($name in 'GlobeNews-Server', 'GlobeNews-DailyPush') {
        if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
            Unregister-ScheduledTask -TaskName $name -Confirm:$false
            Write-Host "Removed: $name"
        } else {
            Write-Host "Not found: $name"
        }
    }
    return
}

# --- Configure SENDKEY ---
if ($SendKey) {
    $configPath = Join-Path $projectDir "config.json"
    @{ sct_sendkey = $SendKey } | ConvertTo-Json | Out-File -FilePath $configPath -Encoding utf8 -Force
    Write-Host "Wrote $configPath"
}

# --- Test push ---
$python = Get-PythonPath
Write-Host "`n--- Test push ---" -ForegroundColor Cyan
$env:PYTHONUTF8 = "1"
& $python (Join-Path $projectDir "push.py")
if ($LASTEXITCODE -ne 0) {
    Write-Host "Test push failed. Fix config first, then re-run." -ForegroundColor Red
    return
}

if ($TestOnly) {
    Write-Host "`n[--TestOnly] Skipping schedule registration." -ForegroundColor Yellow
    return
}

# --- Register: server (at logon, hidden via pythonw) ---
$pythonw = Get-PythonwPath -PythonExe $python

$serverAction = New-ScheduledTaskAction `
    -Execute $pythonw `
    -Argument "server.py" `
    -WorkingDirectory $projectDir

$serverTrigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$serverSettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$serverPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName "GlobeNews-Server" `
    -Action $serverAction `
    -Trigger $serverTrigger `
    -Settings $serverSettings `
    -Principal $serverPrincipal `
    -Description "Daily News Globe — local HTTP server + RSS fetcher" `
    -Force | Out-Null

Write-Host "`nRegistered: GlobeNews-Server (auto-start at logon)" -ForegroundColor Green

# --- Register: daily push ---
$pushAction = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "push.py" `
    -WorkingDirectory $projectDir

$pushTrigger = New-ScheduledTaskTrigger -Daily -At $DailyTime

$pushSettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

$pushPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName "GlobeNews-DailyPush" `
    -Action $pushAction `
    -Trigger $pushTrigger `
    -Settings $pushSettings `
    -Principal $pushPrincipal `
    -Description "Daily News Globe — WeChat push at $DailyTime" `
    -Force | Out-Null

Write-Host "Registered: GlobeNews-DailyPush (daily $DailyTime)" -ForegroundColor Green

# --- Start the server right now so the URL works immediately ---
Write-Host "`n--- Starting server now ---" -ForegroundColor Cyan
Start-ScheduledTask -TaskName "GlobeNews-Server"
Start-Sleep -Seconds 2

# --- Print final summary ---
function Get-LanIp {
    $s = New-Object System.Net.Sockets.UdpClient
    try { $s.Connect("10.254.254.254", 1); return $s.Client.LocalEndPoint.Address.ToString() }
    catch { return "127.0.0.1" }
    finally { $s.Close() }
}

$lan = Get-LanIp
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  DONE"                                    -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "  Phone URL (LAN):  http://$lan`:8765/"
Write-Host "  Daily push:       $DailyTime"
Write-Host "  Server logs:      $projectDir\server.log"
Write-Host ""
Write-Host "  Manual control:"
Write-Host "    Start-ScheduledTask -TaskName GlobeNews-Server"
Write-Host "    Stop-ScheduledTask  -TaskName GlobeNews-Server"
Write-Host "    .\setup_schedule.ps1 -Unregister     # remove both tasks"
Write-Host ""
Write-Host "  Firewall: if your phone can't reach $lan`:8765, you may need to"
Write-Host "  approve the firewall prompt the first time, or run as admin:"
Write-Host "    New-NetFirewallRule -DisplayName 'GlobeNews 8765' -Direction Inbound -LocalPort 8765 -Protocol TCP -Action Allow"
Write-Host ""
