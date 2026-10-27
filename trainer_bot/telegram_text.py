"""Отправка ответов Claude в Telegram: упрощённый Markdown и разбиение длинных сообщений."""

from __future__ import annotations

import re

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

TELEGRAM_LIMIT = 4000

_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_HEADER = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)


def to_legacy_markdown(text: str) -> str:
    """Claude пишет CommonMark, Telegram понимает «legacy» Markdown: *жирный*, _курсив_, `код`."""
    text = _BOLD.sub(r"*\1*", text)
    return _HEADER.sub(r"*\1*", text)


def split_message(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    chunks = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text.strip():
        chunks.append(text)
    return chunks


async def send_text(bot: Bot, chat_id: int, text: str) -> None:
    for chunk in split_message(text):
        try:
            await bot.send_message(chat_id, to_legacy_markdown(chunk), parse_mode=ParseMode.MARKDOWN)
        except TelegramBadRequest:
            # Незакрытая звёздочка или подчёркивание — шлём как есть.
            await bot.send_message(chat_id, chunk, parse_mode=None)
