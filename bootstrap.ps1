# Arbitrage Tracker — bootstrap script
# Делает ВСЁ: подтягивает код, ставит зависимости, создаёт .env,
# создаёт БД, запускает API и бота.
#
# Запуск одной командой из ЛЮБОЙ директории (даже без git clone):
#   irm https://raw.githubusercontent.com/kartlikovmurat-art/arb_tracker_bot/main/bootstrap.ps1 | iex
#
# Или скачать и запустить:
#   iwr -OutFile bootstrap.ps1 https://raw.githubusercontent.com/kartlikovmurat-art/arb_tracker_bot/main/bootstrap.ps1
#   powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1

$ErrorActionPreference = "Stop"
$RepoUrl   = "https://github.com/kartlikovmurat-art/arb_tracker_bot.git"
$RawMain   = "https://raw.githubusercontent.com/kartlikovmurat-art/arb_tracker_bot/main"
$ProjectDir = "arb_tracker_bot"
$Token      = "8889026369:AAH5g4izws1Q-r2uEzbVumQ9WnrbKzq-Rl8"

function Step($n, $text) { Write-Host "`n[$n] $text" -ForegroundColor Cyan }
function Ok($text)      { Write-Host "  ✓ $text" -ForegroundColor Green }
function Warn($text)    { Write-Host "  ⚠ $text" -ForegroundColor Yellow }
function Err($text)     { Write-Host "  ✗ $text" -ForegroundColor Red }

# ── 1. Определяем корень проекта ───────────────────────────────────
Step "1" "Ищу корень проекта..."

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$root = $null

# Если скрипт лежит внутри проекта — используем его корень.
if (Test-Path (Join-Path $scriptDir "app/bot/bot.py")) {
    $root = $scriptDir
    Ok "Корень найден (скрипт внутри проекта): $root"
} else {
    # Иначе — стандартные пути: текущая директория или подпапка.
    $candidates = @(
        (Get-Location).Path,
        (Join-Path (Get-Location).Path $ProjectDir),
        "$HOME\$ProjectDir",
        "$HOME\Documents\$ProjectDir",
        "$HOME\Desktop\$ProjectDir",
        "C:\$ProjectDir",
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path (Join-Path $c "app/bot/bot.py"))) {
            $root = (Resolve-Path $c).Path
            break
        }
    }
}

# Если нигде нет — клонируем.
if (-not $root) {
    Warn "Проект не найден, клонирую..."
    $cloneTo = Join-Path (Get-Location) $ProjectDir
    git clone $RepoUrl $cloneTo
    if ($LASTEXITCODE -ne 0) {
        Err "git clone провалился. Проверь интернет и доступ к GitHub."
        exit 1
    }
    $root = (Resolve-Path $cloneTo).Path
    Ok "Склонировано в $root"
}

Set-Location $root
Ok "Работаю в: $root"

# ── 2. git pull ───────────────────────────────────────────────────
Step "2" "Подтягиваю свежий код (git pull)..."
$branch = git rev-parse --abbrev-ref HEAD 2>&1
if ($LASTEXITCODE -ne 0) {
    Warn "Это не git-репозиторий. Переинициализирую..."
    Remove-Item -Recurse -Force .git -ErrorAction SilentlyContinue
    git init
    git remote add origin $RepoUrl
    git fetch origin
    git checkout -b main origin/main
} else {
    Write-Host "  Ветка: $branch"
    git pull --rebase origin $branch 2>&1 | Out-Null
}
Ok "Код актуален"

# ── 3. .env ───────────────────────────────────────────────────────
Step "3" "Проверяю .env..."
if (-not (Test-Path .env)) {
    if (Test-Path .env.example) {
        Copy-Item .env.example .env
        Ok ".env создан из .env.example"
    } else {
        @"
BOT_TOKEN=$Token
DATABASE_URL=sqlite+aiosqlite:///./db.sqlite3
API_URL=http://127.0.0.1:8000
ADMIN_ID=
BOT_PROXY=
LOG_LEVEL=INFO
"@ | Out-File .env -Encoding UTF8
        Ok ".env создан вручную"
    }
} else {
    Ok ".env уже есть"
}

# Подменяем токен если он пустой или старый
$envContent = Get-Content .env
$hasNewToken = $false
$newContent = @()
foreach ($line in $envContent) {
    if ($line -match "^BOT_TOKEN=(.+)$") {
        $val = $Matches[1].Trim()
        if ($val -eq "your_bot_token_here" -or $val -eq "") {
            $newContent += "BOT_TOKEN=$Token"
            $hasNewToken = $true
        } else {
            $newContent += $line
            $hasNewToken = $true
        }
    } else {
        $newContent += $line
    }
}
if (-not $hasNewToken) { $newContent += "BOT_TOKEN=$Token" }
$newContent | Out-File .env -Encoding UTF8
Ok "BOT_TOKEN проверен/установлен"

# ── 4. Зависимости ────────────────────────────────────────────────
Step "4" "Ставлю зависимости (pip install -r requirements.txt)..."
python -m pip install --upgrade pip 2>&1 | Out-Null
pip install -r requirements.txt 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Err "pip install упал. Проверь requirements.txt"
    exit 1
}
Ok "Зависимости установлены"

# ── 5. Таблицы ───────────────────────────────────────────────────
Step "5" "Создаю таблицы (python main.py)..."
python main.py 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Err "main.py упал"
    exit 1
}
Ok "БД готова"

# ── 6. Убиваем старые процессы ───────────────────────────────────
Step "6" "Останавливаю старые процессы (если висят)..."
Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn app.main*" -or
    $_.CommandLine -like "*app/bot/bot.py*"
} | ForEach-Object {
    Write-Host "  Убиваю PID=$($_.Id)"
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2
Ok "Чисто"

# ── 7. Запуск API в фоне ─────────────────────────────────────────
Step "7" "Запускаю FastAPI (порт 8000) в фоне..."
$apiDir = (Get-Location).Path
Start-Process powershell -ArgumentList @(
    "-NoProfile", "-NoExit", "-Command",
    "cd '$apiDir'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 2>&1 | Tee-Object -FilePath api.log"
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
    Err "API не поднялся за 15 секунд. Лог:"
    if (Test-Path api.log) { Get-Content api.log -Tail 25 | ForEach-Object { Write-Host "    $_" -ForegroundColor Red } }
    exit 1
}
Ok "API живой на http://127.0.0.1:8000"

# ── 8. Запуск бота в фоне ───────────────────────────────────────
Step "8" "Запускаю Telegram-бота в фоне..."
$botDir = (Get-Location).Path
Start-Process powershell -ArgumentList @(
    "-NoProfile", "-NoExit", "-Command",
    "cd '$botDir'; python app/bot/bot.py 2>&1 | Tee-Object -FilePath bot.log"
) -WindowStyle Hidden
Start-Sleep -Seconds 6

# ── 9. Финальная проверка ────────────────────────────────────────
Step "9" "Проверяю токен и бота..."
$token = (Select-String -Path .env -Pattern "^BOT_TOKEN=" | Select-Object -First 1) -replace "^BOT_TOKEN=", ""
try {
    $botInfo = Invoke-RestMethod "https://api.telegram.org/bot${token}/getMe" -TimeoutSec 10
    if (-not $botInfo.ok) {
        Err "Токен невалиден: $($botInfo.description)"
        exit 1
    }
    Ok "Бот: @${($botInfo.result.username)} (id=$($botInfo.result.id))"
} catch {
    Err "Не достучался до api.telegram.org: $($_.Exception.Message)"
    exit 1
}

# ── 10. Лог бота ─────────────────────────────────────────────────
Write-Host "`n[10] Лог бота (последние 10 строк bot.log):" -ForegroundColor Cyan
if (Test-Path bot.log) {
    Get-Content bot.log -Tail 10 | ForEach-Object { Write-Host "    $_" }
} else {
    Warn "bot.log ещё не создан"
}

# ── Готово ────────────────────────────────────────────────────────
Write-Host @"

╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║   ✅  ВСЁ РАБОТАЕТ                                              ║
║                                                                ║
║   Бот:  @${($botInfo.result.username)}                                  ║
║   API:  http://127.0.0.1:8000                                  ║
║                                                                ║
║   👉  Открой Telegram, найди @${($botInfo.result.username)} → /start           ║
║                                                                ║
║   📄  Логи:   bot.log  (бот)                                   ║
║              api.log  (API)                                    ║
║                                                                ║
║   🛑  Остановить:  powershell -ExecutionPolicy Bypass -File   ║
║                     .\stop.ps1                                 ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Green
