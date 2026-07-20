# Arbitrage Tracker — start in background (Windows / PowerShell)
# Запускает API и бота в фоне, логи пишет в bot.log / api.log.
# Окна PowerShell НЕ открывает — всё в фоне.
# Запускать:  powershell -ExecutionPolicy Bypass -File .\start-bg.ps1
# Остановить: powershell -ExecutionPolicy Bypass -File .\stop.ps1

$ErrorActionPreference = "Stop"

# ── Валидация ────────────────────────────────────────────────────
if (-not (Test-Path .env)) {
    Write-Host "❌ Нет .env" -ForegroundColor Red
    exit 1
}
$tokenLine = Select-String -Path .env -Pattern "^BOT_TOKEN=" | Select-Object -First 1
if (-not $tokenLine) {
    Write-Host "❌ В .env нет BOT_TOKEN" -ForegroundColor Red
    exit 1
}

# ── Убиваем старые процессы ────────────────────────────────────
Write-Host "🛑 Останавливаю старые процессы..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn app.main*" -or
    $_.CommandLine -like "*app/bot/bot.py*"
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# ── Создаём таблицы ─────────────────────────────────────────────
Write-Host "📦 Создаю таблицы..." -ForegroundColor Cyan
python main.py 2>&1 | Out-Null
Write-Host "  ✓ готово" -ForegroundColor Green

# ── Запускаем API в фоне ───────────────────────────────────────
Write-Host "🌐 Запускаю API в фоне (лог → api.log)..." -ForegroundColor Cyan
$apiDir = (Get-Location).Path
Start-Process powershell -ArgumentList @(
    "-NoProfile", "-NoExit", "-Command",
    "cd '$apiDir'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 2>&1 | Tee-Object -FilePath api.log"
) -WindowStyle Hidden
Start-Sleep -Seconds 5

# Проверяем
$apiOk = $false
for ($i=0; $i -lt 10; $i++) {
    try {
        $r = Invoke-WebRequest "http://127.0.0.1:8000/trades/" -TimeoutSec 2 -UseBasicParsing
        if ($r.StatusCode -eq 200) { $apiOk = $true; break }
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $apiOk) {
    Write-Host "❌ API не поднялся. Лог:" -ForegroundColor Red
    if (Test-Path api.log) { Get-Content api.log -Tail 20 | ForEach-Object { Write-Host "  $_" } }
    exit 1
}
Write-Host "  ✓ API живой" -ForegroundColor Green

# ── Запускаем бота в фоне ──────────────────────────────────────
Write-Host "🤖 Запускаю бота в фоне (лог → bot.log)..." -ForegroundColor Cyan
$botDir = (Get-Location).Path
Start-Process powershell -ArgumentList @(
    "-NoProfile", "-NoExit", "-Command",
    "cd '$botDir'; python app/bot/bot.py 2>&1 | Tee-Object -FilePath bot.log"
) -WindowStyle Hidden
Start-Sleep -Seconds 5

# Проверяем лог
if (Test-Path bot.log) {
    $logTail = Get-Content bot.log -Tail 5
    if ($logTail -match "Бот запущен|Start polling") {
        Write-Host "  ✓ Бот живой" -ForegroundColor Green
        Write-Host ""
        Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host "  ✅ Готово. Открой Telegram → @arb_tracker_cex_bot" -ForegroundColor Green
        Write-Host "  Логи: bot.log, api.log" -ForegroundColor Green
        Write-Host "  Стоп:  .\stop.ps1" -ForegroundColor Green
        Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
    } else {
        Write-Host "❌ Бот не поднялся. Лог bot.log:" -ForegroundColor Red
        $logTail | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
        exit 1
    }
} else {
    Write-Host "❌ bot.log не создан — что-то совсем не так" -ForegroundColor Red
    exit 1
}
