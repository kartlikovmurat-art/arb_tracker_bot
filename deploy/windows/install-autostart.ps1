# Arbitrage Tracker — автозапуск на Windows через Task Scheduler.
#
# Бот стартует при загрузке компьютера, даже если пользователь не
# залогинен. Если процесс упал — supervisor (run_bot.py) перезапустит
# его сам, а Task Scheduler ещё раз поднимет, если упал supervisor.
#
# Использование:
#   powershell -ExecutionPolicy Bypass -File deploy\windows\install-autostart.ps1
#
# Что делает:
#   1. Регистрирует задачу в Task Scheduler:
#        • Trigger: AtStartup
#        • Action:  python run_bot.py
#        • Run whether user is logged on or not
#        • Restart on failure
#   2. Запускает задачу немедленно (чтобы не ждать перезагрузки).
#
# Удаление:
#   Unregister-ScheduledTask -TaskName "ArbitrageTrackerBot" -Confirm:$false

$ErrorActionPreference = "Stop"

$TaskName    = "ArbitrageTrackerBot"
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$Python      = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogDir      = Join-Path $ProjectRoot "logs"
$StdOut      = Join-Path $LogDir "bot.out.log"
$StdErr      = Join-Path $LogDir "bot.err.log"

if (-not (Test-Path $Python)) {
    Write-Host "ERROR: $Python not found. Create venv first:" -ForegroundColor Red
    Write-Host "  python -m venv .venv && .venv\Scripts\python -m pip install -r requirements.txt openpyxl" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# Если уже есть старая задача — снимаем.
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$action = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "run_bot.py" `
    -WorkingDirectory $ProjectRoot

# AtStartup + каждые 5 минут повтор, если процесс умер
$trigger = New-ScheduledTaskTrigger -AtStartup
$trigger.Delay = "PT30S"  # дать сети подняться

$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -RunLevel Highest `
    -LogonType ServiceAccount

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)  # без лимита

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Arbitrage Tracker Telegram bot (auto-restart supervisor)" `
    | Out-Null

Write-Host "Task '$TaskName' registered." -ForegroundColor Green
Write-Host "Starting it now..." -ForegroundColor Cyan
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 4

$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "Last run:    $($info.LastRunTime)" -ForegroundColor Gray
Write-Host "Result:      $($info.LastTaskResult)" -ForegroundColor Gray
Write-Host "Status:      $($info.Status.ToString())" -ForegroundColor Gray
Write-Host ""
Write-Host "Manage:" -ForegroundColor Yellow
Write-Host "  Disable auto-start:  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
Write-Host "  Run manually:        Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Status:              Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Logs:                Get-Content '$ProjectRoot\bot.log' -Wait"
