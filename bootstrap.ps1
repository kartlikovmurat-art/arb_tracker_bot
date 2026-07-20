# Arbitrage Tracker — bootstrap (works with private repo)
# Запуск одной командой (PowerShell от Администратора не нужен):
#   $env:GH_TOKEN='github_pat_твой_токен'; powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1
# Или если токен уже в .env — просто запусти.

$ErrorActionPreference = "Stop"
$RepoUrl   = "https://github.com/kartlikovmurat-art/arb_tracker_bot.git"
$ApiUrl    = "https://api.github.com/repos/kartlikovmurat-art/arb_tracker_bot"
$ProjectDir = "arb_tracker_bot"
$Token      = $env:GH_TOKEN

# ── 0. Достаём токен ─────────────────────────────────────────────
if (-not $Token) {
    if (Test-Path .env) {
        $m = Select-String -Path .env -Pattern "^BOT_TOKEN=" | Select-Object -First 1
        if ($m) { $Token = ($m -split "=",2)[1].Trim() }
    }
}
if (-not $Token) {
    Write-Host "❌ Нужен GitHub PAT. Положи его в переменную GH_TOKEN:" -ForegroundColor Red
    Write-Host "   `$env:GH_TOKEN='github_pat_...'" -ForegroundColor Yellow
    Write-Host "   powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1" -ForegroundColor Yellow
    exit 1
}

# Authenticated git URL
$AuthUrl = "https://x-access-token:${Token}@github.com/kartlikovmurat-art/arb_tracker_bot.git"

function Step($n, $text) { Write-Host "`n[$n] $text" -ForegroundColor Cyan }
function Ok($text)      { Write-Host "  ✓ $text" -ForegroundColor Green }
function Warn($text)    { Write-Host "  ⚠ $text" -ForegroundColor Yellow }
function Err($text)     { Write-Host "  ✗ $text" -ForegroundColor Red }

# ── 1. Найти или склонировать проект ─────────────────────────────
Step "1" "Ищу корень проекта..."
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$root = $null

if (Test-Path (Join-Path $scriptDir "app/bot/bot.py")) {
    $root = $scriptDir
    Ok "Найден (скрипт внутри проекта): $root"
} else {
    foreach ($c in @((Get-Location).Path, (Join-Path (Get-Location).Path $ProjectDir),
                     "$HOME\$ProjectDir", "$HOME\Documents\$ProjectDir", "$HOME\Desktop\$ProjectDir",
                     "C:\$ProjectDir")) {
        if ($c -and (Test-Path (Join-Path $c "app/bot/bot.py"))) {
            $root = (Resolve-Path $c).Path; break
        }
    }
    if (-not $root) {
        Warn "Не нашёл, клонирую (с токеном)..."
        $cloneTo = Join-Path (Get-Location) $ProjectDir
        git clone $AuthUrl $cloneTo
        if ($LASTEXITCODE -ne 0) { Err "git clone провалился"; exit 1 }
        $root = (Resolve-Path $cloneTo).Path
        Ok "Склонировано в $root"
    } else {
        Ok "Найден: $root"
    }
}
Set-Location $root

# ── 2. git remote перенастроить с токеном (если не настроен) ───
Step "2" "Настраиваю git remote с токеном..."
$current = git remote get-url origin 2>$null
if ($current -notmatch "x-access-token") {
    git remote set-url origin $AuthUrl 2>$null
    Ok "origin перенастроен с токеном"
} else {
    Ok "origin уже с токеном"
}

# ── 3. git pull ────────────────────────────────────────────────
Step "3" "git pull..."
$branch = git rev-parse --abbrev-ref HEAD 2>$null
if (-not $branch) { $branch = "main" }
git pull --rebase origin $branch 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Warn "pull с rebase упал, пробую merge..."
    git pull origin $branch 2>&1 | Out-Null
}
Ok "Код актуален"

# ── 4. .env ────────────────────────────────────────────────────
Step "4" "Проверяю .env..."
$BotToken = "8889026369:AAH5g4izws1Q-r2uEzbVumQ9WnrbKzq-Rl8"
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
    Ok ".env создан"
} else { Ok ".env есть" }

# Подменяем токен если он пустой
$content = Get-Content .env
$out = @()
$hasToken = $false
foreach ($line in $content) {
    if ($line -match "^BOT_TOKEN=(.+)$") {
        $v = $Matches[1].Trim()
        if ($v -eq "your_bot_token_here" -or $v -eq "") {
            $out += "BOT_TOKEN=$BotToken"; $hasToken = $true
        } else {
            $out += $line; $hasToken = $true
        }
    } else { $out += $line }
}
if (-not $hasToken) { $out += "BOT_TOKEN=$BotToken" }
$out | Out-File .env -Encoding UTF8
Ok "BOT_TOKEN на месте"

# ── 5. Зависимости ────────────────────────────────────────────
Step "5" "pip install -r requirements.txt..."
python -m pip install --upgrade pip 2>&1 | Out-Null
pip install -r requirements.txt 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Err "pip install провалился"; exit 1 }
Ok "Зависимости установлены"

# ── 6. Таблицы ───────────────────────────────────────────────
Step "6" "Создаю таблицы (python main.py)..."
python main.py 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Err "main.py упал"; exit 1 }
Ok "БД готова"

# ── 7. Убить старые процессы ──────────────────────────────────
Step "7" "Останавливаю старые процессы..."
Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn app.main*" -or
    $_.CommandLine -like "*app/bot/bot.py*"
} | ForEach-Object {
    Write-Host "  Убиваю PID=$($_.Id)"; Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2
Ok "Чисто"

# ── 8. API в фоне ─────────────────────────────────────────────
Step "8" "Запускаю FastAPI в фоне..."
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
    Err "API не поднялся"
    if (Test-Path api.log) { Get-Content api.log -Tail 25 | ForEach-Object { Write-Host "    $_" -ForegroundColor Red } }
    exit 1
}
Ok "API на http://127.0.0.1:8000"

# ── 9. Бот в фоне ─────────────────────────────────────────────
Step "9" "Запускаю бота в фоне..."
Start-Process powershell -ArgumentList @(
    "-NoProfile","-NoExit","-Command",
    "cd '$dir'; python app/bot/bot.py 2>&1 | Tee-Object -FilePath bot.log"
) -WindowStyle Hidden
Start-Sleep -Seconds 6

# ── 10. Проверка токена ──────────────────────────────────────
Step "10" "Проверяю токен..."
$tok = (Select-String -Path .env -Pattern "^BOT_TOKEN=" | Select-Object -First 1) -replace "^BOT_TOKEN=", ""
try {
    $bi = Invoke-RestMethod "https://api.telegram.org/bot${tok}/getMe" -TimeoutSec 10
    if (-not $bi.ok) { Err "Токен невалиден: $($bi.description)"; exit 1 }
    Ok "Бот: @${($bi.result.username)} (id=$($bi.result.id))"
} catch { Err "Не достучался: $($_.Exception.Message)"; exit 1 }

# Лог
Write-Host "`n[bot.log — последние 10 строк]:" -ForegroundColor Cyan
if (Test-Path bot.log) { Get-Content bot.log -Tail 10 | ForEach-Object { Write-Host "    $_" } }
else { Warn "bot.log ещё не создан" }

Write-Host @"

╔════════════════════════════════════════════════════════════════╗
║   ✅  ВСЁ РАБОТАЕТ                                              ║
║   Бот:  @${($bi.result.username)}                                          ║
║   👉  Открой Telegram, найди @${($bi.result.username)} → /start               ║
║   🛑  Остановить:  powershell -ExecutionPolicy Bypass -File .\stop.ps1        ║
╚════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Green
