# Деплой и автозапуск Arbitrage Tracker

Этот бот — Python-процесс, который должен крутиться **24/7**. Если
комп выключить, бот умрёт. Ниже три варианта: от «на 5 минут
настроить» до «поставил и забыл». Выберите один.

---

## TL;DR — если лень читать

| Вариант | Стоимость | Сложность | Когда выбирать |
|---|---|---|---|
| **Render.com (Blueprint)** | 0 $ | 🟢 одна кнопка | Хочется бесплатно и быстро |
| **Fly.io** | 0 $ | 🟡 нужен `flyctl` | Хочется бесплатно и поближе к РФ/СНГ |
| **Oracle Cloud Free Tier** | 0 $ навсегда | 🟠 нужна регистрация | Хочется VPS, но бесплатно |
| **VPS 3–5 $/мес** | ~300 ₽/мес | 🟠 SSH + пара команд | Хочется «поставил и забыл» |
| **Свой комп (Windows)** | 0 $ | 🟡 Task Scheduler | Только для теста или локалхоста |

Везде, где упоминается **«положить в .env BOT_TOKEN»** — это
значит, что вам нужно один раз получить токен у `@BotFather`
(`/mybots` → ваш бот → API Token → Reset token), и вписать его
в файл `.env` рядом с ботом.

---

## Вариант 1. Render.com (рекомендую для старта)

Render даёт бесплатный web-сервис и бесплатный background worker.
Бот работает 24/7, бесплатно, без своей VPS. Один минус: на
бесплатном тарифе сервисы засыпают после 15 минут без запросов
— **но воркер (бот) у Render не засыпает**, polling идёт
непрерывно.

**Шаги:**

1. Залейте код на GitHub (если ещё не там).
2. Зайдите на https://render.com → **New +** → **Blueprint**.
3. Укажите репо `kartlikovmurat-art/arb_tracker_bot`.
4. Render найдёт `render.yaml` в корне и покажет план:
   - `arb-tracker-api` — FastAPI (web)
   - `arb-tracker-bot` — Telegram-бот (worker)
5. На шаге настройки введите значение `BOT_TOKEN`.
6. Жмите **Apply**. Через 3–5 минут оба сервиса подняты.
7. Проверьте: `https://arb-tracker-api.onrender.com/trades/` —
   должен ответить `[]`.

> ⚠️ На бесплатном плане Render **эфемерная файловая система**:
> SQLite-файл теряется при пересборке. Для одного юзера это
> терпимо (теряется только база), но если хочется надёжно —
> создайте PostgreSQL на Render (бесплатно 90 дней, потом ~$1/мес)
> и пропишите `DATABASE_URL=postgresql+asyncpg://...` в env.

---

## Ваariant 2. Fly.io

Fly даёт 3 shared-CPU VM с 256 MB RAM бесплатно. Близкие к РФ
регионы: `ams` (Амстердам), `fra` (Франкфурт), `arn` (Стокгольм).

**Шаги:**

```bash
# 1. Установите flyctl
curl -L https://fly.io/install.sh | sh

# 2. Залогиньтесь (откроется браузер)
fly auth signup          # или fly auth login

# 3. Поднимите приложение по fly.toml
fly launch --copy-config --name arb-tracker

# 4. Положите секреты
fly secrets set BOT_TOKEN="1234567890:AAxxxx..."

# 5. Создайте persistent volume для SQLite
fly volumes create arb_data --size 1

# 6. Задеплойте
fly deploy
```

Всё. Бот и API стартанут внутри одной VM. Если VM упадёт — Fly
автоматически поднимет новую.

---

## Вариант 3. Oracle Cloud Free Tier

**Навсегда бесплатный** VPS (4 CPU, 24 GB RAM на Ampere A1).
Только нужна банковская карта для регистрации (не спишут ни
цента, если не вылезать за лимиты).

**Шаги:**

1. https://cloud.oracle.com/ → завести аккаунт.
2. Compute → Instances → Create Instance → Shape: `VM.Standard.A1.Flex` (4 OCPU, 24 GB RAM), Image: **Ubuntu 22.04** или **24.04**.
3. SSH на сервер:
   ```bash
   ssh ubuntu@<PUBLIC_IP>
   ```
4. Запустите авто-установщик из этого репо:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/kartlikovmurat-art/arb_tracker_bot/main/deploy/systemd/install-vps.sh | sudo bash
   ```
5. Когда попросит — отредактируйте `.env`:
   ```bash
   sudo -u arb nano /opt/arb-tracker/.env
   ```
   Впишите `BOT_TOKEN=...`.
6. Перезапустите:
   ```bash
   sudo systemctl restart arb-tracker-{api,bot}
   ```
7. Проверьте:
   ```bash
   sudo journalctl -u arb-tracker-bot -f
   ```
   Должно появиться `Бот запущен: @<ваш_бот>`.

Готово. Сервер работает 24/7, supervisor в `run_bot.py`
перезапускает бота при любом падении, systemd перезапускает
supervisor, logrotate чистит логи. Полный «set and forget».

---

## Вариант 4. Любой VPS за 3–5 $/мес

Подойдёт Timeweb, Aéza, Selectel, Hetzner, DigitalOcean, и т.д.
Алгоритм такой же, как в варианте 3 —

```bash
sudo bash deploy/systemd/install-vps.sh
```

(скрипт работает на любом Ubuntu 22.04+, Debian 12+).

---

## Вариант 5. Свой компьютер (Windows)

Имеет смысл **только** если вы не выключаете комп. Удобно для
теста, но для прод-нагрузки плохо.

**Шаги:**

1. Один раз настройте запуск по инструкции из `README.md`
   (или через `start-bg.ps1`).
2. Зарегистрируйте задачу в планировщике:
   ```powershell
   powershell -ExecutionPolicy Bypass -File deploy\windows\install-autostart.ps1
   ```
3. Бот будет стартовать при загрузке Windows, даже если вы
   не залогинены (задача крутится под SYSTEM).
4. Если комп выключится — бот, конечно, ляжет. Когда включите —
   поднимется сам.

---

## Если Telegram не отвечает (api.telegram.org заблокирован)

В РФ, Беларуси, Казахстане часто блокируют api.telegram.org. У
бота уже есть поддержка прокси через `BOT_PROXY` в `.env`. Если
ваш сервер в этих странах — поднимите SSH-туннель до зарубежного
сервера:

```bash
sudo bash deploy/scripts/setup-tunnel.sh
# впишите IP вашего зарубежного сервера

# потом в /opt/arb-tracker/.env допишите:
# BOT_PROXY=socks5://127.0.0.1:1080

sudo systemctl restart arb-tracker-bot
```

`HttpxSession` подхватит прокси автоматически (это и есть та
причина, по которой мы ушли с aiohttp — он плохо дружил с
SOCKS5 на Windows).

---

## Управление после деплоя

| Действие | Команда |
|---|---|
| Посмотреть логи бота (live) | `sudo journalctl -u arb-tracker-bot -f` |
| Логи API | `sudo journalctl -u arb-tracker-api -f` |
| Перезапустить бота | `sudo systemctl restart arb-tracker-bot` |
| Остановить всё | `sudo systemctl stop arb-tracker-{api,bot}` |
| Обновить код | `cd /opt/arb-tracker && sudo -u arb git pull && sudo systemctl restart arb-tracker-{api,bot}` |
| Бэкап БД | `cp /opt/arb-tracker/db.sqlite3 ~/backup-$(date +%F).sqlite3` |
| Или прямо в боте | `/backup` (отдаст JSON-файл со всеми сделками) |

---

## Что делает supervisor (`run_bot.py`)

```text
Бот упал?  →  ждём 1с  →  поднимаем заново
упал опять?  →  ждём 2с  →  поднимаем
упал опять?  →  ждём 4с  →  поднимаем
...
до 60с между попытками
успешно проработал 30с?  →  сбрасываем счётчик
```

Стоп: один `Ctrl+C` для supervisor, второй — для принудительного
выхода. systemd и так знает, что процесс не вечный, поэтому
рестартит его, если он завершился «неожиданно».

---

## Health-check (как узнать, жив ли бот)

```bash
# На сервере
curl -fsS http://127.0.0.1:8000/trades/ | head -c 200

# Извне (если у вас Reverse Proxy)
curl -fsS https://api.example.com/trades/ | head -c 200
```

Если ответ пришёл и это JSON (даже пустой `[]`) — API жив. Бот
может быть жив, даже если API только что перезапускается: бот
ждёт ответа, ретраит, supervisor следит.

---

## Безопасность

- **Никогда** не коммитьте `.env` в git. В репо уже лежит
  `.gitignore` с `.env` в списке.
- Если токен утёк (случайно закоммитили, показали кому-то) —
  идите в `@BotFather` → `/mybots` → **API Token → Reset token**,
  впишите новый в `.env`, перезапустите бота.
- В `.env.example` есть `ADMIN_ID` — это ваш Telegram user_id
  для админ-команд. Узнать свой id: `@userinfobot`.

Подробности о ротации токена — в `RECOVERY.md`.
