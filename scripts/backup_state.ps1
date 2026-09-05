# Backup / restore the harness continuity state (.hermes/).
# Usage:
#   .\scripts\backup_state.ps1 backup                # -> .hermes-backup\<timestamp>.zip
#   .\scripts\backup_state.ps1 restore <zip>         # restores (keeps a pre-restore copy)
#   .\scripts\backup_state.ps1 list
param([string]$Action = "backup", [string]$File = "")

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$State = Join-Path $Root ".hermes"
$Vault = Join-Path $Root ".hermes-backup"

if ($Action -eq "list") {
    if (Test-Path -LiteralPath $Vault) { Get-ChildItem -LiteralPath $Vault -Filter "*.zip" | Format-Table Name, Length, LastWriteTime }
    else { Write-Host "no backups yet" }
    exit 0
}
if ($Action -eq "backup") {
    if (-not (Test-Path -LiteralPath $State)) { Write-Host "nothing to back up (.hermes missing)"; exit 0 }
    New-Item -ItemType Directory -Path $Vault -Force | Out-Null
    $Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $Zip = Join-Path $Vault "hermes-state-$Stamp.zip"
    Compress-Archive -Path (Join-Path $State "*") -DestinationPath $Zip -Force
    Write-Host "backup -> $Zip"
    exit 0
}
if ($Action -eq "restore") {
    if (-not $File -or -not (Test-Path -LiteralPath $File)) { Write-Host "usage: backup_state.ps1 restore <zip>"; exit 1 }
    if (Test-Path -LiteralPath $State) {
        New-Item -ItemType Directory -Path $Vault -Force | Out-Null
        $Pre = Join-Path $Vault ("pre-restore-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".zip")
        Compress-Archive -Path (Join-Path $State "*") -DestinationPath $Pre -Force
        Write-Host "pre-restore copy -> $Pre"
    }
    else { New-Item -ItemType Directory -Path $State -Force | Out-Null }
    Expand-Archive -Path $File -DestinationPath $State -Force
    Write-Host "restored $File -> $State"
    exit 0
}
Write-Host "unknown action: $Action (backup|restore|list)"
exit 1
