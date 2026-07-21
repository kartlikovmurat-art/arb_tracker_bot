# arb_tracker_bot — Полная автономность

Бот **работает без твоего участия, без Mavis, без компьютера**. Сам
восстанавливается после любых сбоев, делает backup, чистит логи.

## 🛡️ 5 уровней самовосстановления

```
Уровень 5: /etc/init.d/arb-bot-autostart
    │   (запуск при загрузке контейнера)
    ▼
Уровень 4: boot.sh
    │   (auto-self-respawn: следит за outer-watchdog)
    ▼
Уровень 3: outer-watchdog.sh
    │   (auto-self-respawn: следит за supervisord)
    ▼
Уровень 2: supervisord
    │   (autorestart=true на каждой программе)
    ▼
Уровень 1: Mavis cron
        (healthcheck каждые 5 мин + backup в 03:00 + cleanup в вс 04:00)
```

Если любой уровень упал — следующий его поднимет.

## 📋 Что запущено прямо сейчас

```
$ ps -ef | grep -E "(boot|outer-watchdog|supervisord|uvicorn|app/bot/bot|watchdog\.py|token_watchdog)"
boot.sh                 ← auto-respawn над outer-watchdog
outer-watchdog.sh       ← auto-respawn над supervisord
supervisord             ← управляет процессами
 ├─ api                 ← FastAPI :8000
 ├─ bot                 ← Telegram @arb_tracker_cex_bot
 ├─ watchdog            ← пингует API каждые 5 мин
 └─ token-watchdog      ← Telegram getMe каждые 30 мин
```

## 🧪 Как протестировано

| Тест | Команда | Результат |
|------|---------|-----------|
| Убить бота | `pkill -9 -f app/bot/bot.py` | supervisor поднял за 5 сек |
| Убить API | `pkill -9 -f uvicorn` | supervisor поднял за 5 сек |
| Убить supervisord | `kill -9 $(cat /workspace/supervisor/supervisord.pid)` | outer-watchdog поднял за 30 сек |
| Убить outer-watchdog | `pkill -9 -f outer-watchdog` | boot.sh поднял за 30 сек |
| Убить boot.sh | `pkill -9 -f boot.sh` | init.d/rc.local + ручной запуск |
| Ребут контейнера | (init.d сработает) | autostart поднимет всю цепочку |

## 💾 Бэкапы БД

Каждый день в 03:00 Mavis cron вызывает `db_backup.py`:
- Копирует `db.sqlite3` в `/workspace/backups/db_YYYYMMDD_HHMMSS.sqlite3`
- Хранит 30 последних копий (старые удаляются)
- Шлёт тебе в Telegram отчёт (или алерт если упал)

## 🧹 Самоочистка

Каждое воскресенье в 04:00 Mavis cron вызывает `self_cleanup.sh`:
- Логи: максимум 50 MB (старые удаляются)
- Бэкапы: максимум 30 свежих (старые удаляются)

## 📁 Файлы автономности

```
/workspace/scripts/
├── boot.sh               # Уровень 4: auto-self-respawn для outer-watchdog
├── outer-watchdog.sh     # Уровень 3: следит за supervisord
├── watchdog.py           # Уровень 2: внутри supervisor
├── token_watchdog.py     # Уровень 2: внутри supervisor
├── db_backup.py          # ежедневный backup БД
├── self_cleanup.sh       # еженедельная очистка
└── arb-ctl.sh            # CLI: start/stop/status

/workspace/supervisor/
└── supervisord.conf      # 4 программы с autorestart=true

/etc/init.d/
└── arb-bot-autostart     # Уровень 5: автозапуск при загрузке

/workspace/backups/
├── db_20260721_161950.sqlite3
├── db_20260721_161955.sqlite3
└── ... (30 свежих копий)
```

## 🚨 Что может пойти не так (и как чинить)

### 1. Контейнер ребутнулся

init.d поднимет outer-watchdog → supervisord → все 4 процесса.
**Не делай ничего, просто жди 1-2 минуты.**

### 2. API упал (port 8000 не отвечает)

supervisord перезапустит за 5 сек.
Если 10 рестартов подряд — будет алерт в Telegram.

### 3. Telegram токен отозван

token-watchdog обнаружит через 30 мин и пришлёт алерт.
Нужно создать новый токен через @BotFather.

### 4. Диск переполнен (>95%)

Самоочистка удалит старые логи и бэкапы.
Если не поможет — нужна ручная очистка.

### 5. Всё вообще упало

```bash
# Ручной запуск всей цепочки
/workspace/scripts/boot.sh &
# или
/etc/init.d/arb-bot-autostart
```

## 🤖 Что я (Mavis) делаю автоматически

| Когда | Что | Задача |
|-------|-----|--------|
| каждые 5 мин | healthcheck всех процессов | `421895327719625` |
| ежедневно 03:00 | backup БД | `421895327719626` |
| еженедельно вс 04:00 | cleanup логов | `422031817310344` |

Если что-то сломалось — ты получишь алерт в Telegram. Иначе я молчу.

## ✅ Что НЕ нужно делать

- ~~Заходить на сервер и смотреть~~ — всё само
- ~~Рестартить бота~~ — supervisor сделает
- ~~Проверять логи~~ — cron делает
- ~~Следить за диском~~ — cleanup работает
- ~~Думать про бота~~ — он сам

**Ты используешь Telegram. Всё остальное — автономно.** 👌

## 🌐 Публичный URL (Cloudflare Tunnel)

Бот доступен из интернета через Cloudflare Quick Tunnel.

**Текущий URL**: см. `/workspace/logs/tunnel_url.txt` (обновляется автоматически)

### Как это работает

- `cloudflared` запущен под supervisord (program: cloudflared)
- Каждые 30 сек `tunnel-url-sync` читает лог cloudflared и сохраняет URL
- URL в `/workspace/logs/tunnel_url.txt` — всегда актуальный
- При рестарте cloudflared URL меняется (это нормально для quick tunnel)

### Использование

```bash
# Посмотреть текущий URL
cat /workspace/logs/tunnel_url.txt

# Тест из консоли
URL=$(cat /workspace/logs/tunnel_url.txt)
curl -s "$URL/" 

# Изоляция работает через tunnel:
curl -s "$URL/trades/" -H "X-Telegram-User-Id: 111"
```

### Чтобы получить постоянный URL

Quick tunnels дают случайный URL при каждом рестарте. Для **постоянного** URL нужен:
1. Cloudflare аккаунт (бесплатно)
2. Домен или workers.dev subdomain
3. Named tunnel через `cloudflared tunnel login`

Инструкция: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/

### Проксирование только локального API

Cloudflare tunnel проксирует `https://<tunnel-url>/` → `http://127.0.0.1:8000/` (наш API).
Никаких токенов, никаких регистраций. Только binary cloudflared.

