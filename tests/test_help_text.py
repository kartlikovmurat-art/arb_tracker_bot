"""Тесты для модуля справки и санити-проверки.

Эти тесты страхуют от регрессии, которая положила бот в проде:
help_text.py был обрезан и не компилировался — диспетчер не
стартовал, бот мгновенно падал с SyntaxError.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.bot.handlers.help_text import HELP_TEXT


def test_help_text_compiles() -> None:
    """Файл справки должен быть валидным Python-модулем."""
    src = Path(__file__).resolve().parents[1] / "app" / "bot" / "handlers" / "help_text.py"
    text = src.read_text(encoding="utf-8")
    ast.parse(text)


def test_help_text_is_non_empty_string() -> None:
    assert isinstance(HELP_TEXT, str)
    assert len(HELP_TEXT) > 200


def test_help_text_covers_main_commands() -> None:
    """Все ключевые команды должны упоминаться в /help."""
    must_have = [
        "/start", "/menu", "/help", "/cancel",
        "/add_trade", "/trades", "/trades_id", "/trades_edit", "/trades_delete",
        "/stats", "/month", "/daily", "/coin", "/exchange", "/strategy",
        "/equity", "/equity_chart", "/export", "/import", "/backup",
        "/search", "/goal", "/today", "/week", "/last", "/calc",
    ]
    for cmd in must_have:
        assert cmd in HELP_TEXT, f"Missing command in HELP_TEXT: {cmd}"


def test_help_text_ends_with_paren_close() -> None:
    """Регрессия: предыдущий файл был обрезан и не закрывал HELP_TEXT = (…)."""
    src = Path(__file__).resolve().parents[1] / "app" / "bot" / "handlers" / "help_text.py"
    text = src.read_text(encoding="utf-8")
    # HELP_TEXT = ( ... ) — последняя непустая строка должна быть ")"
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert lines[-1].strip() == ")", (
        f"help_text.py must end with closing ')' for the tuple. Last line: {lines[-1]!r}"
    )
