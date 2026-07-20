# Arbitrage Tracker - bootstrap (works with private repo)
# Run with:  $env:GH_TOKEN='github_pat_...'; powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1
# Or just:   powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1
#            (then the script will try to read the token from .env)

$ErrorActionPreference = "Stop"
$ProjectDir = "arb_tracker_bot"
$BotToken   = "8889026369:AAH5g4izws1Q-r2uEzbVumQ9WnrbKzq-Rl8"

# ── 0. Get token ─────────────────────────────────────────────
$Token = $env:GH_TOKEN
if (-not $Token) {
    if (Test-Path .env) {
        $m = Select-String -Path .env -Pattern "^BOT_TOKEN=" | Select-Object -First 1
        if ($m) { $Token = ($m -split "=",2)[1].Trim() }
    }
}
if (-not $Token) {
    Write-Host "ERROR: GitHub PAT required." -ForegroundColor Red
    Write-Host "  Set it: `$env:GH_TOKEN='github_pat_...'" -ForegroundColor Yellow
    exit 1
}
$AuthUrl = "https://x-access-token:${Token}@github.com/kartlikovmurat-art/arb_tracker_bot.git"

function Step($n, $text) { Write-Host "`n[$n] $text" -ForegroundColor Cyan }
function Ok($text)      { Write-Host "  ok: $text" -ForegroundColor Green }
function Warn($text)    { Write-Host "  WARN: $text" -ForegroundColor Yellow }
function Err($text)     { Write-Host "  ERROR: $text" -ForegroundColor Red }

# ── 1. Find or clone project ─────────────────────────────────
Step "1" "Locating project root..."
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$root = $null

if (Test-Path (Join-Path $scriptDir "app/bot/bot.py")) {
    $root = $scriptDir
    Ok "found (script is inside project): $root"
} else {
    foreach ($c in @((Get-Location).Path,
                     (Join-Path (Get-Location).Path $ProjectDir),
                     "$HOME\$ProjectDir",
                     "$HOME\Documents\$ProjectDir",
                     "$HOME\Desktop\$ProjectDir",
                     "C:\$ProjectDir")) {
        if ($c -and (Test-Path (Join-Path $c "app/bot/bot.py"))) {
            $root = (Resolve-Path $c).Path; break
        }
    }
    if (-not $root) {
        Warn "not found, cloning (with token)..."
        $cloneTo = Join-Path (Get-Location) $ProjectDir
        git clone $AuthUrl $cloneTo
        if ($LASTEXITCODE -ne 0) { Err "git clone failed"; exit 1 }
        $root = (Resolve-Path $cloneTo).Path
        Ok "cloned to $root"
    } else { Ok "found: $root" }
}
Set-Location $root

# ── 2. Configure remote with token ──────────────────────────
Step "2" "Setting git remote with token..."
$current = git remote get-url origin 2>$null
if ($current -notmatch "x-access-token") {
    git remote set-url origin $AuthUrl 2>$null
    Ok "origin reconfigured with token"
} else { Ok "origin already has token" }

# ── 3. git pull ─────────────────────────────────────────────
Step "3" "git pull..."
$branch = git rev-parse --abbrev-ref HEAD 2>$null
if (-not $branch) { $branch = "main" }
git pull --rebase origin $branch 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Warn "rebase failed, trying merge..."
    git pull origin $branch 2>&1 | Out-Null
}
Ok "code is up to date"

# ── 4. .env ─────────────────────────────────────────────────
Step "4" "Checking .env..."
if (-not (Test-Path .env)) {
    if (Test-Path .env.example) { Copy-Item .env.example .env }
    else {
        @"
BOT_TOKEN=$BotToken
DATABASE_URL=sqlite+aiosqlite:///./db.sqlite3
API_URL=http://127.0.0.1:8000
ADMIN_ID=
BOT_PROXY=
LOG_LEVEL=INFO
"@ | Out-File .env -Encoding UTF8
    }
    Ok ".env created"
} else { Ok ".env exists" }

$content = Get-Content .env
$out = @()
$hasToken = $false
foreach ($line in $content) {
    if ($line -match "^BOT_TOKEN=(.+)$") {
        $v = $Matches[1].Trim()
        if ($v -eq "your_bot_token_here" -or $v -eq "") {
            $out += "BOT_TOKEN=$BotToken"; $hasToken = $true
        } else { $out += $line; $hasToken = $true }
    } else { $out += $line }
}
if (-not $hasToken) { $out += "BOT_TOKEN=$BotToken" }
$out | Out-File .env -Encoding UTF8
Ok "BOT_TOKEN is set"

# ── 5. Dependencies ────────────────────────────────────────
Step "5" "pip install -r requirements.txt..."
python -m pip install --upgrade pip 2>&1 | Out-Null
pip install -r requirements.txt 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Err "pip install failed"; exit 1 }
Ok "dependencies installed"

# ── 6. Tables ─────────────────────────────────────────────
Step "6" "python main.py (create tables)..."
python main.py 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Err "main.py failed"; exit 1 }
Ok "DB ready"

# ── 7. Kill old processes ────────────────────────────────
Step "7" "Killing old processes..."
Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn app.main*" -or
    $_.CommandLine -like "*app/bot/bot.py*"
} | ForEach-Object {
    Write-Host "  killing PID=$($_.Id)"; Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2
Ok "clean"

# ── 8. API in background ────────────────────────────────
Step "8" "Starting API in background..."
$dir = (Get-Location).Path
Start-Process powershell -ArgumentList @(
    "-NoProfile","-NoExit","-Command",
    "cd '$dir'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 2>&1 | Tee-Object -FilePath api.log"
) -WindowStyle Hidden
Start-Sleep -Seconds 5
$apiOk = $false
for ($i=0; $i -lt 15; $i++) {
    try {
        $r = Invoke-WebRequest "http://127.0.0.1:8000/trades/" -TimeoutSec 2 -UseBasicParsing
        if ($r.StatusCode -eq 200) { $apiOk = $true; break }
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $apiOk) {
    Err "API did not start"
    if (Test-Path api.log) { Get-Content api.log -Tail 25 | ForEach-Object { Write-Host "    $_" -ForegroundColor Red } }
    exit 1
}
Ok "API on http://127.0.0.1:8000"

# ── 9. Bot in background ────────────────────────────────
Step "9" "Starting bot in background..."
Start-Process powershell -ArgumentList @(
    "-NoProfile","-NoExit","-Command",
    "cd '$dir'; python app/bot/bot.py 2>&1 | Tee-Object -FilePath bot.log"
) -WindowStyle Hidden
Start-Sleep -Seconds 6

# ── 10. Token check ─────────────────────────────────────
Step "10" "Token check via getMe..."
$tok = (Select-String -Path .env -Pattern "^BOT_TOKEN=" | Select-Object -First 1) -replace "^BOT_TOKEN=", ""
try {
    $bi = Invoke-RestMethod "https://api.telegram.org/bot${tok}/getMe" -TimeoutSec 10
    if (-not $bi.ok) { Err "token invalid: $($bi.description)"; exit 1 }
    Ok "bot: @${($bi.result.username)} (id=$($bi.result.id))"
} catch { Err "cannot reach api.telegram.org: $($_.Exception.Message)"; exit 1 }

Write-Host "`n[bot.log - last 10 lines]:" -ForegroundColor Cyan
if (Test-Path bot.log) { Get-Content bot.log -Tail 10 | ForEach-Object { Write-Host "    $_" } }
else { Warn "bot.log not created yet" }

Write-Host @"

============================================================
  ALL GOOD.
  Bot:  @${($bi.result.username)}
  Open Telegram -> @${($bi.result.username)} -> /start
  Stop:  powershell -ExecutionPolicy Bypass -File .\stop.ps1
============================================================
"@ -ForegroundColor Green
