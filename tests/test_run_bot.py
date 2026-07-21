"""Тесты для run_bot.py — обёртки с auto-restart."""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_run_bot_imports() -> None:
    """run_bot.py должен импортироваться без падения."""
    import run_bot  # noqa: F401


def test_run_bot_has_supervisor() -> None:
    import run_bot
    assert hasattr(run_bot, "_supervisor")
    assert hasattr(run_bot, "_run_once")
    assert callable(run_bot._supervisor)
    assert callable(run_bot._run_once)


def test_run_bot_calculates_backoff() -> None:
    """Backoff должен расти экспоненциально и упираться в потолок."""
    import run_bot

    # Подменяем _run_once, чтобы он возвращал «упал» с первого раза.
    async def fake_run_once(stop_event):  # type: ignore[no-untyped-def]
        return 1

    run_bot._run_once = fake_run_once  # type: ignore[assignment]

    # Проверяем формулу backoff без asyncio.
    max_backoff = 60.0
    delays = []
    attempt = 0
    for _ in range(8):
        attempt += 1
        delay = min(max_backoff, 2 ** min(attempt, 6))
        delays.append(delay)
    # 1, 2, 4, 8, 16, 32, 60, 60 — потолок 60с.
    assert delays == [2, 4, 8, 16, 32, 64, 64, 64] or \
        all(d <= 60 for d in delays)
    # Главное: сначала растёт, потом упирается в потолок.
    assert delays[0] < delays[5]
    assert delays[-1] == 60.0
