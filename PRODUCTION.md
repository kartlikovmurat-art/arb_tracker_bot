# Production Setup

## 24/7 без нашего участия — полная автоматизация

Три уровня защиты от падений:

1. **supervisord** (PID 998) — главный менеджер 6 процессов. `autorestart=true` у каждого.
   - `api` — FastAPI на :8000
   - `bot` — Telegram-бот
   - `cloudflared` — HTTPS-туннель (API наружу)
   - `tunnel-sync` — копирует URL туннеля в файл
   - `webapp-rebuild` — пересобирает HTML, если URL сменился
   - `watchdog` — каждые 5 мин пингует API, шлёт алерты

2. **outer-watchdog.sh** (отдельный bash-цикл) — если supervisord упал, поднимает его за 30 секунд.

3. **Mavis cron** (task_id `421918292459595`) — каждые 5 минут вызывает меня. Я:
   - проверяю статус процессов
   - проверяю tunnel (curl /health)
   - если URL сменился — пересобираю HTML, редеплою через `website_deploy`, обновляю BotFather menu button
   - уведомляю тебя в Telegram

## Управление

```bash
/workspace/scripts/arb-ctl.sh start    # запустить все
/workspace/scripts/arb-ctl.sh stop     # остановить
/workspace/scripts/arb-ctl.sh restart  # перезапустить
/workspace/scripts/arb-ctl.sh status   # статус
/workspace/scripts/arb-ctl.sh logs     # последние логи
/workspace/scripts/arb-ctl.sh url      # текущий tunnel URL
```

## Что задеплоено

- **Mini App** на `https://5w867zwmjd2n7.space.minimax.io/`
- **API** на `https://combining-thunder-stages-intranet.trycloudflare.com/` (URL может меняться при рестарте cloudflared — cron автоматически обновит)
- **BotFather menu button** → Mini App

## Файлы

```
/workspace/
├── arb_tracker_bot1_full/      # код бота
├── supervisor/
│   ├── supervisord.conf        # конфиг 6 процессов
│   └── supervisor.sock
├── scripts/
│   ├── arb-ctl.sh              # CLI
│   ├── boot.sh                 # запуск supervisord
│   ├── outer-watchdog.sh       # супервизор над супервизором
│   ├── watchdog.py             # мониторинг + Telegram алерты
│   ├── tunnel_url_sync.py       # URL sync
│   └── webapp_redeploy.py       # пересборка HTML
├── logs/                       # все логи
│   ├── api.{out,err}.log
│   ├── bot.{out,err}.log
│   ├── cloudflared.{out,err}.log
│   ├── watchdog.{out,err}.log
│   ├── tunnel-sync.{out,err}.log
│   ├── webapp-redeploy.{out,err}.log
│   ├── supervisord.log
│   ├── outer-watchdog.log
│   └── tunnel_url.txt
└── webapp_build/               # HTML для редеплоя
    └── index.html              # const API = '<tunnel>'
```

## Как Mavis автоматически реагирует

Каждые 5 минут `cron arb-bot-healthcheck` (task_id `421918292459595`) запускает Mavis. Я:
1. Читаю `/workspace/scripts/arb-ctl.sh status`
2. Если что-то упало — `arb-ctl.sh restart <имя>`, читаю логи
3. Пингую tunnel — если не отвечает, рестарт cloudflared
4. Сравниваю URL в `/workspace/webapp_build/index.html` с `tunnel_url.txt`
5. Если разные — пересобираю HTML, редеплою через `website_deploy`, обновляю BotFather menu button
6. Шлю тебе краткий отчёт в Telegram (chat_id 6492055524)

## Чтобы бот работал 24/7

Просто **ничего не делай** 😎
- Не выключай Mavis-сервер (ноут может спать)
- Mavis cron вызывает меня каждые 5 минут
- supervisord держит процессы
- outer-watchdog поднимает supervisord
- Я (Mavis) автоматически редеплою Mini App при смене URL
