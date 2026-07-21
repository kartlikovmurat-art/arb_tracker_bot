# Снять задачу автозапуска Arbitrage Tracker из Task Scheduler.
#
#   powershell -ExecutionPolicy Bypass -File deploy\windows\uninstall-autostart.ps1

$ErrorActionPreference = "Stop"
$TaskName = "ArbitrageTrackerBot"

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $existing) {
    Write-Host "Task '$TaskName' is not registered. Nothing to do." -ForegroundColor Yellow
    exit 0
}

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Task '$TaskName' removed." -ForegroundColor Green
