import asyncio
import os
import socket
import sys
from pathlib import Path

# Allow running this script directly from the repository root with `python app/bot/bot.py`.
root_path = Path(__file__).resolve().parents[2]
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import CommandStart
from aiogram.types import Message
import json
from aiogram.filters import Command
from decimal import Decimal, InvalidOperation
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.config.settings import API_URL, BOT_TOKEN


async def main():

    proxy_url = (
        os.getenv("BOT_PROXY")
        or os.getenv("TELEGRAM_PROXY")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("https_proxy")
        or os.getenv("HTTP_PROXY")
        or os.getenv("http_proxy")
    )

    # Try to build an aiohttp-backed session for aiogram. Prefer IPv4 and
    # allow falling back to a plain aiohttp.ClientSession if AiohttpSession
    # construction fails (missing aiohttp-socks or proxy issues).
    session = None
    try:
        session = AiohttpSession(proxy=proxy_url)
        # Prefer IPv4 to avoid IPv6 routing issues on some CI/containers
        try:
            session._connector_init["family"] = socket.AF_INET
        except Exception:
            # Not critical; continue with default connector settings
            pass
    except Exception as exc:
        print("AiohttpSession creation failed (proxy support may be missing):", exc)
        # Fall back to a plain aiohttp client session that aiogram accepts.
        try:
            # aiogram accepts an `aiohttp.ClientSession` as well
            fallback = aiohttp.ClientSession()
            session = fallback
            print("Fell back to plain aiohttp.ClientSession for Telegram session")
        except Exception as exc2:
            print("Failed to create fallback aiohttp session:", exc2)
            session = None
    # If BOT_TOKEN is not provided, skip attempting Telegram connection
    # and run the offline demo instead so the API can be validated locally.
    async def run_offline_demo():
        demo_payload = {
            "coin": "OFFLINE",
            "buy_exchange": "DemoBuy",
            "sell_exchange": "DemoSell",
            "amount": 0.1,
            "buy_price": 100,
            "sell_price": 110,
            "trade_type": "CEX_CEX",
            "status": "PENDING",
        }

        # Normalize (keeps parity with interactive path)
        if "trade_type" in demo_payload and isinstance(demo_payload["trade_type"], str):
            demo_payload["trade_type"] = demo_payload["trade_type"].replace("-", "_").replace(" ", "_").upper()
        if "status" in demo_payload and isinstance(demo_payload["status"], str):
            demo_payload["status"] = demo_payload["status"].upper()

        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post(f"{API_URL}/trades/", json=demo_payload, timeout=10) as resp:
                    text = await resp.text()
                    print("API response status:", resp.status)
                    print(text)
        except Exception as err:
            print("Offline demo failed to call API:", err)

    if proxy_url:
        print(f"Using proxy for Telegram requests: {proxy_url}")
    else:
        print("No proxy environment variable configured for Telegram requests.")

    if not BOT_TOKEN:
        print("BOT_TOKEN not set; skipping Telegram. Running offline demo.")
        await run_offline_demo()
        return

    bot = Bot(
        token=BOT_TOKEN,
        session=session,
    )

    dp = Dispatcher(storage=MemoryStorage())


    class TradeForm(StatesGroup):
        coin = State()
        buy_exchange = State()
        sell_exchange = State()
        amount = State()
        buy_price = State()
        sell_price = State()
        strategy = State()
        note = State()


    @dp.message(CommandStart())
    async def start(message: Message):
        await message.answer(
            "👋 Добро пожаловать в Arbitrage Tracker Bot!"
        )

    @dp.message(Command("add_trade"))
    async def add_trade(message: Message):
        """Add trade by sending JSON after the command.

        Example:
        /add_trade {"coin":"BTC","buy_exchange":"Binance","sell_exchange":"Bybit","amount":0.5,"buy_price":60000,"sell_price":62000}
        """
        # support inline JSON after command
        payload = message.text.removeprefix("/add_trade").strip()

        if payload:
            try:
                data = json.loads(payload)
            except Exception:
                await message.answer("Невалидный JSON. Проверьте синтаксис.")
                return
            # Normalize enums before sending
            def normalize_payload(payload: dict) -> dict:
                if not isinstance(payload, dict):
                    return payload
                if "trade_type" in payload and isinstance(payload["trade_type"], str):
                    v = payload["trade_type"].replace("-", "_").replace(" ", "_").upper()
                    payload["trade_type"] = v
                if "status" in payload and isinstance(payload["status"], str):
                    payload["status"] = payload["status"].upper()
                return payload

            data = normalize_payload(data)

            try:
                async with aiohttp.ClientSession() as session_http:
                    async with session_http.post(f"{API_URL}/trades/", json=data) as resp:
                        text = await resp.text()
                        if resp.status in (200, 201):
                            await message.answer("Сделка сохранена.")
                        else:
                            await message.answer(f"Ошибка API {resp.status}: {text}")
            except Exception as exc:
                await message.answer(f"Не удалось отправить запрос к API: {exc}")
            return

        # otherwise start FSM dialog
        await message.answer("Ввод новой сделки. Отправьте /cancel чтобы отменить.\nВведите монету (например BTC):")
        await TradeForm.coin.set()


    @dp.message(Command("cancel"))
    async def cancel_flow(message: Message, state: FSMContext):
        current = await state.get_state()
        if current is None:
            await message.answer("Нет активного ввода.")
            return
        await state.clear()
        await message.answer("Ввод сделки отменён.")


    @dp.message(TradeForm.coin)
    async def process_coin(message: Message, state: FSMContext):
        await state.update_data(coin=message.text.strip())
        await TradeForm.next()
        await message.answer("Введите биржу покупки (buy_exchange):")


    @dp.message(TradeForm.buy_exchange)
    async def process_buy_exchange(message: Message, state: FSMContext):
        await state.update_data(buy_exchange=message.text.strip())
        await TradeForm.next()
        await message.answer("Введите биржу продажи (sell_exchange):")


    @dp.message(TradeForm.sell_exchange)
    async def process_sell_exchange(message: Message, state: FSMContext):
        await state.update_data(sell_exchange=message.text.strip())
        await TradeForm.next()
        await message.answer("Введите объём (amount), например 0.5:")


    @dp.message(TradeForm.amount)
    async def process_amount(message: Message, state: FSMContext):
        text = message.text.strip()
        try:
            val = Decimal(text)
        except InvalidOperation:
            await message.answer("Неверный формат числа для объёма. Введите число, например 0.5 или отправьте /cancel.")
            return
        if val <= 0:
            await message.answer("Объём должен быть больше нуля. Попробуйте снова или отправьте /cancel.")
            return
        await state.update_data(amount=str(val))
        await TradeForm.next()
        await message.answer("Введите цену покупки (buy_price):")


    @dp.message(TradeForm.buy_price)
    async def process_buy_price(message: Message, state: FSMContext):
        text = message.text.strip()
        try:
            val = Decimal(text)
        except InvalidOperation:
            await message.answer("Неверный формат числа для цены покупки. Введите число или /cancel.")
            return
        if val <= 0:
            await message.answer("Цена покупки должна быть больше нуля. Попробуйте снова или отправьте /cancel.")
            return
        await state.update_data(buy_price=str(val))
        await TradeForm.next()
        await message.answer("Введите цену продажи (sell_price):")


    @dp.message(TradeForm.sell_price)
    async def process_sell_price(message: Message, state: FSMContext):
        text = message.text.strip()
        try:
            val = Decimal(text)
        except InvalidOperation:
            await message.answer("Неверный формат числа для цены продажи. Введите число или /cancel.")
            return
        if val <= 0:
            await message.answer("Цена продажи должна быть больше нуля. Попробуйте снова или отправьте /cancel.")
            return
        await state.update_data(sell_price=str(val))
        await TradeForm.next()
        await message.answer("Введите стратегию (опционально) или отправьте '-' для пропуска:")


    @dp.message(TradeForm.strategy)
    async def process_strategy(message: Message, state: FSMContext):
        text = message.text.strip()
        if text != "-":
            await state.update_data(strategy=text)
        await TradeForm.next()
        await message.answer("Введите комментарий/примечание (опционально) или отправьте '-' для пропуска:")


    @dp.message(TradeForm.note)
    async def process_note(message: Message, state: FSMContext):
        text = message.text.strip()
        if text != "-":
            await state.update_data(note=text)

        data = await state.get_data()

        # Normalize enums before sending
        if "trade_type" in data and isinstance(data["trade_type"], str):
            data["trade_type"] = data["trade_type"].replace("-", "_").replace(" ", "_").upper()
        if "status" in data and isinstance(data["status"], str):
            data["status"] = data["status"].upper()

        try:
            async with aiohttp.ClientSession() as session_http:
                async with session_http.post(f"{API_URL}/trades/", json=data) as resp:
                    text_resp = await resp.text()
                    if resp.status in (200, 201):
                        await message.answer("Сделка сохранена.")
                    else:
                        await message.answer(f"Ошибка API {resp.status}: {text_resp}")
        except Exception as exc:
            await message.answer(f"Не удалось отправить запрос к API: {exc}")

        await state.clear()


    # Try to contact Telegram. If network is unavailable or token is invalid,
    # fall back to an offline demo mode that posts a sample trade to the API
    # so we can validate API/DB behavior without Telegram connectivity.
    # Try to contact Telegram with retries; on repeated failure, run offline demo.
    try:
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                me = await bot.get_me()
                print(f"Bot started: @{me.username}")
                # Connected successfully; start polling (blocking)
                await dp.start_polling(bot)
                return
            except Exception as exc:
                print(f"Attempt {attempt} to contact Telegram failed: {exc}")
                if attempt < max_attempts:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
    except Exception as exc:
        # Ensure the aiohttp session is closed to avoid warnings
        try:
            await session.close()
        except Exception:
            pass

        print("Telegram connection failed after retries:", exc)
        print("Entering offline demo: will POST a sample trade to the API and exit.")
        await run_offline_demo()


if __name__ == "__main__":
    asyncio.run(main())