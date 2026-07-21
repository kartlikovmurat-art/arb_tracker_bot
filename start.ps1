# Arbitrage Tracker - start script (Windows / PowerShell)
# Runs the API and the Telegram bot in two SEPARATE visible windows.
# Run:   powershell -ExecutionPolicy Bypass -File .\start.ps1
# Stop:  close both windows, or run  .\stop.ps1

$ErrorActionPreference = "Stop"

# ── Validation ────────────────────────────────────────────────────
if (-not (Test-Path .env)) {
    Write-Host "No .env found. Creating from .env.example..." -ForegroundColor Yellow
    if (Test-Path .env.example) {
        Copy-Item .env.example .env
    } else {
        Write-Host "ERROR: .env.example is also missing" -ForegroundColor Red
        exit 1
    }
    Write-Host "Open .env and set BOT_TOKEN, then run this script again." -ForegroundColor Red
    notepad .env
    exit 1
}

$envContent = Get-Content .env -Raw
if ($envContent -notmatch "BOT_TOKEN=\S+") {
    Write-Host "ERROR: BOT_TOKEN is empty in .env" -ForegroundColor Red
    exit 1
}

# ── Create tables (idempotent) ─────────────────────────────────
Write-Host "`nCreating tables..." -ForegroundColor Cyan
python main.py

# ── Start API in a new window ───────────────────────────────────
Write-Host "`nStarting FastAPI on http://127.0.0.1:8000 (new window)..." -ForegroundColor Cyan
$apiCmd = "python -m uvicorn app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $apiCmd -WindowStyle Normal
Start-Sleep -Seconds 4

# Health check
try {
    $health = Invoke-RestMethod "http://127.0.0.1:8000/trades/" -TimeoutSec 5
    Write-Host "  ok: API responds, $($health.Count) trades in DB" -ForegroundColor Green
} catch {
    Write-Host "ERROR: API is not responding. Check the first window." -ForegroundColor Red
    exit 1
}

# ── Start bot in a new window ───────────────────────────────────
Write-Host "`nStarting Telegram bot (new window)..." -ForegroundColor Cyan
# run_bot.py — обёртка с авто-перезапуском. Если бот упадёт
# (сеть, API, баг), он сам поднимется обратно.
$botCmd = "python run_bot.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $botCmd -WindowStyle Normal
Start-Sleep -Seconds 4

# ── Final token check ──────────────────────────────────────────
Write-Host "`nChecking token via @BotFather getMe..." -ForegroundColor Cyan
$tokenLine = Select-String -Path .env -Pattern "^BOT_TOKEN="
$token = ($tokenLine -split "=", 2)[1].Trim()
try {
    $botInfo = Invoke-RestMethod "https://api.telegram.org/bot${token}/getMe" -TimeoutSec 5
    if ($botInfo.ok) {
        Write-Host "  ok: bot @${($botInfo.result.username)} is alive" -ForegroundColor Green
    } else {
        Write-Host "ERROR: token is invalid" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "ERROR: cannot reach api.telegram.org" -ForegroundColor Red
    exit 1
}

Write-Host @"

================================================
  ALL GOOD.
  - API runs in a separate PowerShell window.
  - Bot runs in another PowerShell window.
  - Open Telegram -> @${($botInfo.result.username)} -> /start
  - To stop everything, close both windows
    or run:  powershell -ExecutionPolicy Bypass -File .\stop.ps1
  - Auto-restart: ENABLED (run_bot.py wraps the bot)
================================================
"@ -ForegroundColor Green
