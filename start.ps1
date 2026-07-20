# Arbitrage Tracker — start script (Windows / PowerShell)
# Запускает API и Telegram-бота в двух отдельных окнах.
# Запускать из корня проекта:  powershell -ExecutionPolicy Bypass -File .\start.ps1

$ErrorActionPreference = "Stop"

# ── 1. Проверки ─────────────────────────────────────────────────────
if (-not (Test-Path .env)) {
    Write-Host "❌ Нет файла .env. Создаю из .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "⚠️  Открой .env и впиши BOT_TOKEN (от @BotFather)" -ForegroundColor Red
    notepad .env
    exit 1
}

$envContent = Get-Content .env -Raw
if ($envContent -notmatch "BOT_TOKEN=\S+") {
    Write-Host "❌ В .env не заполнен BOT_TOKEN" -ForegroundColor Red
    exit 1
}

# ── 2. Создание таблиц (один раз) ─────────────────────────────────
Write-Host "`n📦 Создаю таблицы..." -ForegroundColor Cyan
python main.py

# ── 3. Запуск API в новом окне ────────────────────────────────────
Write-Host "`n🌐 Запускаю FastAPI (http://127.0.0.1:8000)..." -ForegroundColor Cyan
$apiCmd = "python -m uvicorn app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $apiCmd -WindowStyle Normal
Start-Sleep -Seconds 4

# Проверяем что API живой
try {
    $health = Invoke-RestMethod "http://127.0.0.1:8000/trades/" -TimeoutSec 5
    Write-Host "✅ API отвечает: $($health.Count) сделок в базе" -ForegroundColor Green
} catch {
    Write-Host "❌ API не отвечает. Проверь окно с uvicorn." -ForegroundColor Red
    exit 1
}

# ── 4. Запуск бота в новом окне ───────────────────────────────────
Write-Host "`n🤖 Запускаю Telegram-бота..." -ForegroundColor Cyan
$botCmd = "python app/bot/bot.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $botCmd -WindowStyle Normal
Start-Sleep -Seconds 4

# ── 5. Финальная проверка ────────────────────────────────────────
Write-Host "`n🔎 Проверяю токен у @BotFather..." -ForegroundColor Cyan
$tokenLine = Select-String -Path .env -Pattern "^BOT_TOKEN="
$token = ($tokenLine -split "=", 2)[1].Trim()
try {
    $botInfo = Invoke-RestMethod "https://api.telegram.org/bot${token}/getMe" -TimeoutSec 5
    if ($botInfo.ok) {
        Write-Host "✅ Бот живой: @${($botInfo.result.username)}" -ForegroundColor Green
    } else {
        Write-Host "❌ Токен невалидный" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Не удалось достучаться до api.telegram.org" -ForegroundColor Red
    exit 1
}

Write-Host @"

╔════════════════════════════════════════════════════════════╗
║  ✅ Всё готово!                                            ║
║                                                            ║
║  • API работает в отдельном окне (http://127.0.0.1:8000)   ║
║  • Бот работает в отдельном окне (long-polling)            ║
║                                                            ║
║  👉 Открой Telegram → найди @${($botInfo.result.username)}     ║
║     → /start                                               ║
║                                                            ║
║  Чтобы остановить — закрой оба окна PowerShell.            ║
╚════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Green
