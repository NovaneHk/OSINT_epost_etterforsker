# Register a daily Windows Scheduled Task for the OSINT database backup.
# Run this script ONCE as Administrator.
#
# Usage:
#   PowerShell -ExecutionPolicy Bypass -File scripts\schedule_backup.ps1
#
# To remove the task later:
#   Unregister-ScheduledTask -TaskName "OsintDbBackup" -Confirm:$false

$TaskName   = "OsintDbBackup"
$ScriptPath = "$PSScriptRoot\run_backup.ps1"
$TriggerTime = "02:00"   # 2 AM daily

$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
               -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$ScriptPath`""

$trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
        -Settings $settings -Principal $principal -Description "Daily OSINT PostgreSQL backup"

    Write-Host "[OK] Scheduled task '$TaskName' registered — runs daily at $TriggerTime" -ForegroundColor Green
    Write-Host "     Backup script: $ScriptPath"
    Write-Host "     To run immediately: Start-ScheduledTask -TaskName '$TaskName'"
} catch {
    Write-Host "[ERROR] Failed to register scheduled task: $_" -ForegroundColor Red
    Write-Host "Make sure you are running PowerShell as Administrator." -ForegroundColor Yellow
    exit 1
}
