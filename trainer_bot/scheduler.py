"""Проактивные сообщения тренера: утренний план и вечерний чек-ин."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import Settings

log = logging.getLogger(__name__)

MORNING_PROMPT = (
    "[Напоминание: утро] Посмотри plan.md и log.md. Если сегодня тренировочный день — "
    "пришли карточку тренировки артефактом и коротко мотивируй. Если день отдыха — "
    "одной фразой напомни про восстановление. Ничего не пиши, если план ещё не составлен."
)

EVENING_PROMPT = (
    "[Напоминание: вечер] Если сегодня по плану была тренировка, а в log.md нет записи "
    "за сегодня — коротко спроси, как прошло. Иначе ничего не отвечай, просто закончи ход."
)

Ask = Callable[[int, str], Awaitable[None]]


def build_scheduler(settings: Settings, ask: Ask) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    chat_id = settings.owner_chat_id

    async def run(prompt: str) -> None:
        try:
            await ask(chat_id, prompt)
        except Exception:
            log.exception("Ошибка в запланированной задаче")

    jobs = [("morning", settings.morning_reminder, MORNING_PROMPT), ("evening", settings.evening_checkin, EVENING_PROMPT)]
    for job_id, at, prompt in jobs:
        if at is None:
            continue
        hour, minute = at
        scheduler.add_job(run, CronTrigger(hour=hour, minute=minute), args=[prompt], id=job_id)
        log.info("Запланировано %s на %02d:%02d (%s)", job_id, hour, minute, settings.timezone)
    return scheduler
