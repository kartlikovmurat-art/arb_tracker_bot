# Arbitrage Tracker — stop script (Windows / PowerShell)
# Останавливает API и Telegram-бота.

Write-Host "🛑 Останавливаю процессы..." -ForegroundColor Yellow

Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn app.main*" -or
    $_.CommandLine -like "*app/bot/bot.py*"
} | ForEach-Object {
    Write-Host "  Убиваю PID=$($_.Id): $($_.CommandLine.Substring(0, [Math]::Min(60, $_.CommandLine.Length)))" -ForegroundColor DarkYellow
    Stop-Process -Id $_.Id -Force
}

Write-Host "✅ Готово." -ForegroundColor Green
