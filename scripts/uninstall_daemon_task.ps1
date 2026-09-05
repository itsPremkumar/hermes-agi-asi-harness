# Removes the Hermes 24/7 daemon Scheduled Task.
# Usage: .\scripts\uninstall_daemon_task.ps1 [-TaskName HermesAGI-Daemon]
param([string]$TaskName = "HermesAGI-Daemon")

$ErrorActionPreference = "Stop"
Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Removed task '$TaskName'."
