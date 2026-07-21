# Production Setup

## Управление процессами

```bash
/workspace/scripts/arb-ctl.sh start    # запустить все
/workspace/scripts/arb-ctl.sh stop     # остановить
/workspace/scripts/arb-ctl.sh restart  # перезапустить
/workspace/scripts/arb-ctl.sh status   # статус
/workspace/scripts/arb-ctl.sh logs     # последние логи
/workspace/scripts/arb-ctl.sh url      # текущий tunnel URL
```

## Что управляет чем

- **supervisord** — главный менеджер процессов. Автоперезапуск при падении.
  Управляет: `api`, `bot`, `cloudflared`, `tunnel-sync`, `watchdog`.

- **outer-watchdog.sh** — «супервизор над супервизором». Если supervisord
  упал, перезапускает его. Запускается через nohup отдельно.

- **watchdog.py** — внутри supervisor. Раз в 5 минут пингует API и
  Telegram, при падении перезапускает через `supervisorctl` и шлёт
  алерт в Telegram напрямую (chat_id 6492055524).

- **tunnel_url_sync.py** — внутри supervisor. Каждую минуту читает лог
  cloudflared, обновляет `tunnel_url.txt` и webapp/index.html.

## Cloudflare Tunnel

Free-туннель `https://*.trycloudflare.com`. Меняется при рестарте —
`tunnel_url_sync` подхватывает новый URL автоматически.

## Где лежит

```
/workspace/
├── arb_tracker_bot1_full/      # код бота
├── supervisor/
│   ├── supervisord.conf        # конфиг
│   └── supervisor.sock          # control socket
├── scripts/
│   ├── arb-ctl.sh              # CLI
│   ├── boot.sh                 # запускает supervisord
│   ├── watchdog.py             # мониторинг
│   ├── tunnel_url_sync.py       # URL sync
│   └── outer-watchdog.sh        # supervisor over watchdog
└── logs/
    ├── api.{out,err}.log
    ├── bot.{out,err}.log
    ├── cloudflared.{out,err}.log
    ├── watchdog.{out,err}.log
    ├── tunnel-sync.{out,err}.log
    ├── supervisord.log
    └── tunnel_url.txt
```
