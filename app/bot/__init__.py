"""Telegram-бот для Arbitrage Tracker.

Структура:
    * ``api``        — HTTP-клиент к локальному FastAPI (httpx).
    * ``formatters`` — превращение JSON-ответов API в читабельный текст.
    * ``keyboards``  — инлайн-кнопки для навигации.
    * ``handlers``   — обработчики команд aiogram, сгруппированные по теме.
    * ``bot.py``     — точка входа, регистрация хендлеров и polling.
"""
