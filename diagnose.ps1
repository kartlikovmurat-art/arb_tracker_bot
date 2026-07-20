# Arbitrage Tracker - diagnostic script (Windows / PowerShell)
# Collects everything we need to debug a broken install in one shot.
# Run:   powershell -ExecutionPolicy Bypass -File .\diagnose.ps1
# Result: a big report - copy it and send it back to the assistant.

$ErrorActionPreference = "Continue"

function Section([string]$title) { Write-Host "`n=== $title ===" -ForegroundColor Cyan }

# ── 1. Python ────────────────────────────────────────────────────
Section "1. Python"
$pyVer = python --version 2>&1
Write-Host "  $pyVer"

# ── 2. Package versions ─────────────────────────────────────────
Section "2. Package versions (pip show)"
foreach ($pkg in @("aiogram","httpx","fastapi","sqlalchemy","aiosqlite","alembic","pytest","respx")) {
    $info = pip show $pkg 2>&1 | Select-String -Pattern "^Version:" | Select-Object -First 1
    if ($info) {
        Write-Host "  $pkg : $($info -replace '^Version:\s*','')" -ForegroundColor White
    } else {
        Write-Host "  $pkg : NOT INSTALLED" -ForegroundColor Red
    }
}

# ── 3. .env ──────────────────────────────────────────────────────
Section "3. .env file"
if (Test-Path .env) {
    Write-Host "  exists" -ForegroundColor Green
    $envContent = Get-Content .env
    foreach ($line in $envContent) {
        if ($line -match "BOT_TOKEN=" -and $line -notmatch "your_bot_token_here") {
            Write-Host "  $line" -ForegroundColor White
            $token = ($line -split "=",2)[1].Trim()
            Write-Host "  (token length = $($token.Length) chars)" -ForegroundColor DarkGray
        } elseif ($line -match "BOT_TOKEN=") {
            Write-Host "  WARNING: BOT_TOKEN is the placeholder" -ForegroundColor Red
        } else {
            Write-Host "  $line" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Host "  NOT FOUND. Create it: Copy-Item .env.example .env" -ForegroundColor Red
}

# ── 4. Git ──────────────────────────────────────────────────────
Section "4. Git"
try {
    $branch = git rev-parse --abbrev-ref HEAD 2>&1
    Write-Host "  Branch: $branch"
    $log = git log --oneline -5 2>&1
    Write-Host "  Last 5 commits:"
    foreach ($l in $log) { Write-Host "    $l" -ForegroundColor DarkGray }
    $status = git status --short 2>&1
    if ($status) {
        Write-Host "  Uncommitted changes:" -ForegroundColor Yellow
        foreach ($s in $status) { Write-Host "    $s" -ForegroundColor DarkGray }
    } else {
        Write-Host "  Working tree clean" -ForegroundColor Green
    }
} catch {
    Write-Host "  ERROR: not a git repo or git not available" -ForegroundColor Red
}

# ── 5. Database ─────────────────────────────────────────────────
Section "5. Database (db.sqlite3)"
if (Test-Path db.sqlite3) {
    $size = (Get-Item db.sqlite3).Length
    Write-Host "  exists ($([math]::Round($size/1024,1)) KB)" -ForegroundColor Green
} else {
    Write-Host "  does not exist yet. Will be created by 'python main.py'" -ForegroundColor Yellow
}

# ── 6. Token via Bot API ────────────────────────────────────────
Section "6. Token check (getMe)"
if (Test-Path .env) {
    $tokenLine = Select-String -Path .env -Pattern "^BOT_TOKEN=" | Select-Object -First 1
    if ($tokenLine) {
        $token = ($tokenLine -split "=",2)[1].Trim()
        if ($token -and $token -ne "your_bot_token_here") {
            try {
                $resp = Invoke-RestMethod "https://api.telegram.org/bot${token}/getMe" -TimeoutSec 10
                if ($resp.ok) {
                    Write-Host "  ok: bot @${($resp.result.username)} (id=$($resp.result.id))" -ForegroundColor Green
                } else {
                    Write-Host "  ERROR: Telegram says: $($resp.description)" -ForegroundColor Red
                }
            } catch {
                Write-Host "  ERROR: cannot reach api.telegram.org" -ForegroundColor Red
                Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
            }
        } else {
            Write-Host "  ERROR: BOT_TOKEN is empty" -ForegroundColor Red
        }
    }
}

# ── 7. bot.py structure ─────────────────────────────────────────
Section "7. app/bot/bot.py in local clone"
if (Test-Path app/bot/bot.py) {
    $hasPrepare = Select-String -Path app/bot/bot.py -Pattern "prepare_value" -Quiet
    $hasBuild   = Select-String -Path app/bot/bot.py -Pattern "self.build_form_data" -Quiet
    if ($hasPrepare) {
        Write-Host "  ok: HttpxSession uses prepare_value (PR #3 fix is here)" -ForegroundColor Green
    } elseif ($hasBuild) {
        Write-Host "  ERROR: still uses build_form_data - old code, need git pull" -ForegroundColor Red
    } else {
        Write-Host "  WARNING: neither prepare_value nor build_form_data found" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ERROR: app/bot/bot.py not found. Wrong directory?" -ForegroundColor Red
    Write-Host "  Current: $(Get-Location)" -ForegroundColor Yellow
}

# ── 8. Running processes ────────────────────────────────────────
Section "8. Running processes"
$botProcs = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*app/bot/bot.py*" }
$apiProcs = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" }
if ($botProcs) {
    foreach ($p in $botProcs) { Write-Host "  Bot:  PID=$($p.Id), started=$($p.StartTime)" }
} else { Write-Host "  Bot:  not running" -ForegroundColor DarkGray }
if ($apiProcs) {
    foreach ($p in $apiProcs) { Write-Host "  API:  PID=$($p.Id), started=$($p.StartTime)" }
} else { Write-Host "  API:  not running" -ForegroundColor DarkGray }

# ── 9. API on :8000 ───────────────────────────────────────────
Section "9. API on :8000"
try {
    $r = Invoke-WebRequest "http://127.0.0.1:8000/trades/" -TimeoutSec 3 -UseBasicParsing
    Write-Host "  ok: /trades/ -> $($r.StatusCode)" -ForegroundColor Green
} catch {
    if ($_.Exception.Message -match "connection|refused|10061") {
        Write-Host "  ERROR: API is not listening on :8000" -ForegroundColor Red
    } else {
        Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# ── 10. bot.log tail ──────────────────────────────────────────
Section "10. bot.log (last 30 lines)"
if (Test-Path bot.log) {
    Get-Content bot.log -Tail 30 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
} else { Write-Host "  (no bot.log)" -ForegroundColor DarkGray }

Write-Host "`n=== Copy the entire output above and send it to the assistant ===" -ForegroundColor Cyan
