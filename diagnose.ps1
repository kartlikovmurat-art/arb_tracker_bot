# Arbitrage Tracker — diagnose script (Windows / PowerShell)
# Собирает всю диагностику, чтобы сразу было видно, что не так.
# Запускать:  powershell -ExecutionPolicy Bypass -File .\diagnose.ps1
# Результат: один большой отчёт — копируй и кидай мне в чат.

$ErrorActionPreference = "Continue"
$report = New-Object System.Text.StringBuilder

function Out-Line($color, [string]$text) {
    Write-Host $text -ForegroundColor $color
    [void]$report.AppendLine($text)
}

Out-Line Cyan "═══════════════════════════════════════════════════════════════"
Out-Line Cyan  " Arbitrage Tracker — диагностика"
Out-Line Cyan  " $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Out-Line Cyan "═══════════════════════════════════════════════════════════════"

# ── 1. Python ────────────────────────────────────────────────────────
Out-Line Yellow "`n[1] Python"
$pyVer = python --version 2>&1
Out-Line White "  $pyVer"

# ── 2. Установленные пакеты ─────────────────────────────────────────
Out-Line Yellow "`n[2] Версии пакетов (pip show)"
foreach ($pkg in @("aiogram","httpx","fastapi","sqlalchemy","aiosqlite","alembic","pytest","respx")) {
    $info = pip show $pkg 2>&1 | Select-String -Pattern "^Version:" | Select-Object -First 1
    if ($info) {
        Out-Line White "  $pkg : $($info -replace '^Version:\s*','')"
    } else {
        Out-Line Red    "  $pkg : ❌ НЕ УСТАНОВЛЕН"
    }
}

# ── 3. .env ──────────────────────────────────────────────────────────
Out-Line Yellow "`n[3] Файл .env"
if (Test-Path .env) {
    Out-Line Green "  ✓ существует"
    $envContent = Get-Content .env
    foreach ($line in $envContent) {
        if ($line -match "BOT_TOKEN=" -and $line -notmatch "your_bot_token_here") {
            Out-Line White  "  $line" -ErrorAction SilentlyContinue
            $token = ($line -split "=",2)[1].Trim()
            Out-Line White  "  (токен виден, длина = $($token.Length) символов)"
        } elseif ($line -match "BOT_TOKEN=") {
            Out-Line Red    "  ⚠️  BOT_TOKEN не заполнен (your_bot_token_here)"
        } else {
            Out-Line DarkGray "  $line"
        }
    }
} else {
    Out-Line Red    "  ❌ Файл .env не найден в текущей директории"
    Out-Line Yellow "  💡 Создай: Copy-Item .env.example .env   и заполни BOT_TOKEN"
}

# ── 4. Git ───────────────────────────────────────────────────────────
Out-Line Yellow "`n[4] Git"
try {
    $branch = git rev-parse --abbrev-ref HEAD 2>&1
    Out-Line White "  Ветка: $branch"
    $log = git log --oneline -5 2>&1
    Out-Line White  "  Последние коммиты:"
    foreach ($l in $log) { Out-Line DarkGray "    $l" }
    $status = git status --short 2>&1
    if ($status) {
        Out-Line Yellow "  Незакоммиченные изменения:"
        foreach ($s in $status) { Out-Line DarkGray "    $s" }
    } else {
        Out-Line Green "  ✓ Рабочее дерево чистое"
    }
} catch {
    Out-Line Red    "  ❌ Не git-репозиторий или git недоступен"
}

# ── 5. main.py / таблицы ────────────────────────────────────────────
Out-Line Yellow "`n[5] База данных"
if (Test-Path db.sqlite3) {
    $size = (Get-Item db.sqlite3).Length
    Out-Line Green "  ✓ db.sqlite3 ($([math]::Round($size/1024,1)) KB)"
} else {
    Out-Line Yellow "  ℹ db.sqlite3 не существует — создастся при python main.py"
}

# ── 6. Токен живой? ─────────────────────────────────────────────────
Out-Line Yellow "`n[6] Проверка токена через Bot API"
if (Test-Path .env) {
    $tokenLine = Select-String -Path .env -Pattern "^BOT_TOKEN=" | Select-Object -First 1
    if ($tokenLine) {
        $token = ($tokenLine -split "=",2)[1].Trim()
        if ($token -and $token -ne "your_bot_token_here") {
            try {
                $resp = Invoke-RestMethod "https://api.telegram.org/bot${token}/getMe" -TimeoutSec 10
                if ($resp.ok) {
                    Out-Line Green "  ✓ Бот живой: @${($resp.result.username)} (id=$($resp.result.id))"
                    Out-Line Green "  Имя: $($resp.result.first_name)"
                } else {
                    Out-Line Red    "  ❌ Telegram вернул ошибку: $($resp.description)"
                }
            } catch {
                Out-Line Red    "  ❌ Не удалось достучаться до api.telegram.org"
                Out-Line Red    "  $($_.Exception.Message)"
            }
        } else {
            Out-Line Red    "  ❌ BOT_TOKEN пустой"
        }
    }
}

# ── 7. Файлы бота в репо ────────────────────────────────────────────
Out-Line Yellow "`n[7] Структура app/bot/ в локальном клоне"
if (Test-Path app/bot/bot.py) {
    $hasPrepare = Select-String -Path app/bot/bot.py -Pattern "prepare_value" -Quiet
    $hasBuild   = Select-String -Path app/bot/bot.py -Pattern "build_form_data" -Quiet
    if ($hasPrepare) {
        Out-Line Green "  ✓ HttpxSession использует prepare_value (новый код, PR #3)"
    } elseif ($hasBuild) {
        Out-Line Red    "  ❌ HttpxSession ещё использует build_form_data — старый код!"
        Out-Line Yellow "     Нужно: git pull origin main"
    } else {
        Out-Line Yellow "  ⚠ Не нашёл ни prepare_value, ни build_form_data"
    }
    $files = Get-ChildItem app/bot -Recurse -File -Filter "*.py" | Select-Object -ExpandProperty FullName
    Out-Line White  "  Файлов в app/bot: $($files.Count)"
    foreach ($f in $files) {
        $rel = $f -replace [regex]::Escape((Get-Location).Path + "\"), ''
        Out-Line DarkGray "    $rel"
    }
} else {
    Out-Line Red "  ❌ app/bot/bot.py не найден — ты не в корне проекта?"
    Out-Line White "  Текущая директория: $(Get-Location)"
}

# ── 8. Проверка конфликтующих процессов ─────────────────────────────
Out-Line Yellow "`n[8] Запущенные процессы"
$botProcs = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*app/bot/bot.py*"
}
$apiProcs = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*"
}
if ($botProcs) {
    foreach ($p in $botProcs) {
        Out-Line White "  Бот: PID=$($p.Id), started=$($p.StartTime)"
    }
} else {
    Out-Line DarkGray "  Бот: не запущен"
}
if ($apiProcs) {
    foreach ($p in $apiProcs) {
        Out-Line White "  API: PID=$($p.Id), started=$($p.StartTime)"
    }
} else {
    Out-Line DarkGray "  API: не запущен"
}

# ── 9. API живой? ──────────────────────────────────────────────────
Out-Line Yellow "`n[9] API на :8000"
try {
    $r = Invoke-WebRequest "http://127.0.0.1:8000/trades/" -TimeoutSec 3 -UseBasicParsing
    Out-Line Green "  ✓ /trades/ → $($r.StatusCode)"
} catch {
    if ($_.Exception.Message -match "connection|refused|10061") {
        Out-Line Red    "  ✗ API не слушает :8000"
        Out-Line Yellow "    Запусти сначала: python -m uvicorn app.main:app --port 8000"
    } else {
        Out-Line Red    "  ✗ Ошибка: $($_.Exception.Message)"
    }
}

# ── 10. Лог бота если есть ─────────────────────────────────────────
Out-Line Yellow "`n[10] Лог бота (bot.log, последние 30 строк)"
if (Test-Path bot.log) {
    Get-Content bot.log -Tail 30 | ForEach-Object { Out-Line DarkGray "  $_" }
} else {
    Out-Line DarkGray "  (нет файла bot.log)"
}

# ── Итог ───────────────────────────────────────────────────────────
Out-Line Cyan "`n═══════════════════════════════════════════════════════════════"
Out-Line Cyan " Скопируй вывод всего этого отчёта и кинь мне сюда."
Out-Line Cyan "═══════════════════════════════════════════════════════════════"

# Сохраним в файл
$report | Out-File -FilePath diagnose-report.txt -Encoding UTF8
Out-Line Yellow "`n💾 Отчёт сохранён в diagnose-report.txt"
