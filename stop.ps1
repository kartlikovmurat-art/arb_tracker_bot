# Arbitrage Tracker - stop script (Windows / PowerShell)
# Kills any uvicorn / app/bot/bot.py / run_bot.py process.

Write-Host "Stopping running processes..." -ForegroundColor Yellow

$procs = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn app.main*" -or
    $_.CommandLine -like "*app/bot/bot.py*" -or
    $_.CommandLine -like "*run_bot.py*"
}

if ($procs) {
    foreach ($p in $procs) {
        Write-Host "  Killing PID=$($p.Id)" -ForegroundColor DarkYellow
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "  Nothing to stop." -ForegroundColor DarkGray
}

Write-Host "Done." -ForegroundColor Green
