"""Текст справки /help.

Вынесен в отдельный модуль, чтобы его можно было рендерить
из тестов без поднятия диспетчера.
"""
from __future__ import annotations


HELP_TEXT = (
    "📚 <b>Команды Arbitrage Tracker</b>\n"
    "─" * 24 + "\n\n"
    "➕ <b>Добавление сделки</b>\n"
    "<code>/add_trade</code> — пошаговый ввод (FSM)\n"
    "<code>/add_trade {\"coin\":\"BTC\",...}</code> — одной строкой JSON\n"
    "<code>/cancel</code> — отменить текущий ввод\n\n"
    "📋 <b>Просмотр сделок</b>\n"
    "<code>/trades</code> — последние сделки (с пагинацией)\n"
    "<code>/trades_id &lt;id&gt;</code> — детали конкретной сделки\n"
    "<code>/trades_coin &lt;BTC&gt;</code> — фильтр по монете\n"
    "<code>/trades_exchange &lt;Binance&gt;</code> — фильтр по бирже\n\n"
    "📊 <b>Аналитика</b>\n"
    "<code>/stats</code> — общая статистика\n"
    "<code>/month</code> — по месяцам\n"
    "<code>/daily</code> — по дням\n"
    "<code>/coin</code> — по монетам\n"
    "<code>/exchange</code> — по биржам\n"
    "<code>/strategy</code> — по стратегиям\n"
    "<code>/equity</code> — кривая доходности\n\n"
    "📤 <b>Экспорт</b>\n"
    "<code>/export</code> — выгрузить все сделки в Excel\n"
)
