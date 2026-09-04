# Installs the Hermes 24/7 daemon as a Windows Scheduled Task.
# Run in an elevated (Administrator) PowerShell for a machine-level task,
# or without elevation for a user-level task.
# Usage: .\scripts\install_daemon_task.ps1 [-TaskName HermesAGI-Daemon]
param([string]$TaskName = "HermesAGI-Daemon")

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\PREM KUMAR\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path -LiteralPath $Python)) { $Python = (Get-Command python.exe).Source }
$Log = Join-Path $Root ".hermes\daemon-task.log"
New-Item -ItemType Directory -Path (Join-Path $Root ".hermes") -Force | Out-Null

$Cmd = "`"$Python`" -m hermes_agi daemon run >> `"$Log`" 2>&1"
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c $Cmd" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable -DontStopOnIdleEnd
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Settings $Settings -Principal $Principal -Force | Out-Null
Write-Host "Installed task '$TaskName' (root=$Root log=$Log). Start now with: Start-ScheduledTask -TaskName $TaskName"
