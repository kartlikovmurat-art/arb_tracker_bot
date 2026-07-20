# Arbitrage Tracker Bot

Телеграм-бот + FastAPI-сервис для учёта завершённых арбитражных сделок.
Это **личная CRM арбитражного трейдера**: бот фиксирует сделки,
сервис хранит историю, считает статистику и формирует отчёты.

> Бот **не** ищет арбитраж и **не** торгует. Он только записывает
> результат уже завершённой сделки. История — единственный источник
> истины, вся аналитика считается из неё.

## Возможности

- 💼 Учёт сделок: монета, биржи, объём, цены, комиссии, стратегия, заметка.
- 📊 Аналитика: общая статистика, по монетам / биржам / стратегиям / дням / месяцам.
- 📈 Кривая доходности по датам.
- 📋 Просмотр сделок с пагинацией и фильтрами (по монете, по бирже).
- 📤 Экспорт всей истории в Excel одним сообщением.
- 🛡 Безопасный Telegram-стек на `httpx` (без `aiohttp`).

## Архитектура

```
Telegram Bot (aiogram 3, httpx)  ──HTTP──▶  FastAPI (SQLAlchemy, SQLite/Postgres)
        ▲                                            │
        │ пользователь                                ▼
        └──── история, статистика, экспорт ◀─── доменный слой
```

| Слой         | Где                                     |
|--------------|------------------------------------------|
| Точка входа  | `main.py` (создаёт таблицы)              |
| Telegram-бот | `app/bot/` (см. ниже)                   |
| API          | `app/api/` (FastAPI-роутеры)             |
| Бизнес-логика| `app/application/use_cases/`            |
| Домен        | `app/core/entities/`, `app/core/services/` |
| Хранилище    | `app/infrastructure/` (SQLAlchemy, репозитории) |

### Структура `app/bot/`

```
app/bot/
├── bot.py              # точка входа, HttpxSession, polling
├── api/
│   └── client.py       # HTTP-клиент к FastAPI
├── formatters/
│   └── text.py         # JSON → читабельный текст для Telegram
├── keyboards/
│   └── inline.py       # инлайн-кнопки (пагинация, /help)
└── handlers/
    ├── common.py       # /start, /help, /cancel
    ├── add_trade.py    # /add_trade (FSM и JSON)
    ├── view.py         # /trades, /trades_id, /trades_coin, /trades_exchange
    ├── analytics.py    # /stats, /month, /daily, /coin, /exchange, /strategy, /equity
    ├── export.py       # /export
    └── pagination.py   # callback'и пагинации
```

## Команды бота

| Команда                          | Что делает                                     |
|----------------------------------|------------------------------------------------|
| `/start`                         | Приветствие                                    |
| `/help`                          | Этот список с кнопками-подсказками             |
| `/cancel`                        | Отменить текущий ввод                          |
| `/add_trade`                     | Пошаговый ввод сделки (FSM)                    |
| `/add_trade {…JSON…}`            | Добавить сделку одной строкой JSON             |
| `/trades`                        | Последние сделки (с пагинацией)                |
| `/trades_id 42`                  | Подробности сделки №42                         |
| `/trades_coin BTC`               | Все сделки по монете BTC                       |
| `/trades_exchange Binance`       | Все сделки по бирже                            |
| `/stats`                         | Общая статистика (P/L, win-rate, ROI)          |
| `/month`                         | Статистика по месяцам                          |
| `/daily`                         | Статистика по дням                             |
| `/coin`                          | Статистика по монетам                          |
| `/exchange`                      | Статистика по биржам                           |
| `/strategy`                      | Статистика по стратегиям                       |
| `/equity`                        | Кривая доходности                              |
| `/export`                        | Выгрузить все сделки в Excel                   |

### Пример JSON для быстрого добавления

```json
{
  "coin": "BTC",
  "buy_exchange": "Binance",
  "sell_exchange": "Bybit",
  "amount": "0.1",
  "buy_price": "60000",
  "sell_price": "60500",
  "buy_fee": "5",
  "withdrawal_fee": "0.5",
  "trade_type": "CEX_CEX",
  "status": "COMPLETED",
  "strategy": "spread-hunter",
  "note": "manual test"
}
```

Команда: `/add_trade {"coin":"BTC", …}`.

## Быстрый старт (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Откройте .env и впишите BOT_TOKEN
.\.venv\Scripts\python.exe main.py        # создаст таблицы
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
.\.venv\Scripts\python.exe app\bot\bot.py
```

## Запуск тестов

```bash
pytest -q
```

Покрываются:

- HTTP-клиент бота (`tests/test_bot_api_client.py`)
- Текстовые форматтеры (`tests/test_bot_formatters.py`)
- Хендлеры и пагинация (`tests/test_bot_handlers.py`)
- Существующие тесты репозиториев, мапперов, калькулятора и API

## Безопасность

- Токен бота хранится в `.env`, который в `.gitignore`.
- Если токен когда-либо утекал, см. `RECOVERY.md` — там пошаговый
  план: новый токен у `@BotFather`, чистка истории, обновление
  зависимостей.
- Прокси для Telegram — переменная `BOT_PROXY`.

## Принципы проекта

1. История — единственный источник истины. Никогда не удалять
   сделки «для красоты отчёта».
2. Любая статистика пересчитывается из истории.
3. Каждая цифра объяснима: «прибыль +1250» → сделки → детали.
4. Минимум ручных вычислений: пользователь только вводит данные.
5. Модули независимы: Telegram — лишь один из способов доступа.
