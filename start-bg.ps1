# Arbitrage Tracker - start in background (Windows / PowerShell)
# Runs the API and the bot in hidden PowerShell windows.
# Logs go to bot.log / api.log in the project root.
# Run:   powershell -ExecutionPolicy Bypass -File .\start-bg.ps1
# Stop:  powershell -ExecutionPolicy Bypass -File .\stop.ps1

$ErrorActionPreference = "Stop"

# ── Validation ────────────────────────────────────────────────────
if (-not (Test-Path .env)) {
    Write-Host "ERROR: .env not found" -ForegroundColor Red
    exit 1
}
$tokenLine = Select-String -Path .env -Pattern "^BOT_TOKEN=" | Select-Object -First 1
if (-not $tokenLine) {
    Write-Host "ERROR: BOT_TOKEN is missing in .env" -ForegroundColor Red
    exit 1
}

# ── Kill old processes ───────────────────────────────────────────
Write-Host "Killing old processes (if any)..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn app.main*" -or
    $_.CommandLine -like "*app/bot/bot.py*"
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# ── Create tables (idempotent) ─────────────────────────────────
Write-Host "Creating tables (python main.py)..." -ForegroundColor Cyan
python main.py 2>&1 | Out-Null
Write-Host "  ok" -ForegroundColor Green

# ── Start API in background ─────────────────────────────────────
Write-Host "Starting API in background (log -> api.log)..." -ForegroundColor Cyan
$apiDir = (Get-Location).Path
Start-Process powershell -ArgumentList @(
    "-NoProfile", "-NoExit", "-Command",
    "cd '$apiDir'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 2>&1 | Tee-Object -FilePath api.log"
) -WindowStyle Hidden
Start-Sleep -Seconds 5

# Wait for /trades/ to respond
$apiOk = $false
for ($i=0; $i -lt 10; $i++) {
    try {
        $r = Invoke-WebRequest "http://127.0.0.1:8000/trades/" -TimeoutSec 2 -UseBasicParsing
        if ($r.StatusCode -eq 200) { $apiOk = $true; break }
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $apiOk) {
    Write-Host "ERROR: API did not start. Log tail:" -ForegroundColor Red
    if (Test-Path api.log) { Get-Content api.log -Tail 20 | ForEach-Object { Write-Host "  $_" } }
    exit 1
}
Write-Host "  ok: API is up on http://127.0.0.1:8000" -ForegroundColor Green

# ── Start bot in background ──────────────────────────────────────
Write-Host "Starting bot in background (log -> bot.log)..." -ForegroundColor Cyan
$botDir = (Get-Location).Path
Start-Process powershell -ArgumentList @(
    "-NoProfile", "-NoExit", "-Command",
    "cd '$botDir'; python app/bot/bot.py 2>&1 | Tee-Object -FilePath bot.log"
) -WindowStyle Hidden
Start-Sleep -Seconds 5

# Verify bot started
if (Test-Path bot.log) {
    $logTail = Get-Content bot.log -Tail 8
    if ($logTail -match "Bot started|Start polling|Run polling") {
        Write-Host "  ok: bot is polling" -ForegroundColor Green
        Write-Host ""
        Write-Host "=================================================" -ForegroundColor Green
        Write-Host "  ALL GOOD. Open Telegram -> @arb_tracker_cex_bot" -ForegroundColor Green
        Write-Host "  Logs:  bot.log, api.log" -ForegroundColor Green
        Write-Host "  Stop:  powershell -ExecutionPolicy Bypass -File .\stop.ps1" -ForegroundColor Green
        Write-Host "=================================================" -ForegroundColor Green
    } else {
        Write-Host "ERROR: bot did not start. Log tail:" -ForegroundColor Red
        $logTail | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
        exit 1
    }
} else {
    Write-Host "ERROR: bot.log was not created" -ForegroundColor Red
    exit 1
}
