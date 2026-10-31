"""Точка входа: Telegram-бот поверх сессий Claude."""

from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, Message
from aiogram.utils.chat_action import ChatActionSender

from .agent import Agent
from .codex_agent import CodexAgent
from .config import Settings, load_settings
from .exercises import ExerciseDb
from .render import Renderer
from .scheduler import Ask, build_scheduler
from .telegram_text import send_text

log = logging.getLogger("trainer_bot")

TEMPLATE_DIR = Path(__file__).parent / "workspace_template"

HELP = (
    "Я твой персональный тренер на AI.\n\n"
    "Просто пиши: «составь план на месяц», «покажи технику выпада», «сделал 3×10 приседа с 60 кг».\n"
    "Можно присылать фото (еда, техника, весы).\n\n"
    "/new — новая беседа (как /clear), план и журнал сохраняются\n"
    "/stop — прервать текущий ответ\n"
    "/status — состояние сессии"
)

COMMANDS = [
    BotCommand(command="new", description="Новая беседа (очистить контекст)"),
    BotCommand(command="clear", description="То же, что /new"),
    BotCommand(command="stop", description="Прервать ответ"),
    BotCommand(command="status", description="Состояние сессии"),
    BotCommand(command="help", description="Помощь"),
]


def prepare_workspace(settings: Settings) -> None:
    """Раскладывает шаблон тренера в рабочую папку, не перезаписывая существующие файлы."""
    settings.workspace.mkdir(parents=True, exist_ok=True)
    for src in TEMPLATE_DIR.rglob("*"):
        dst = settings.workspace / src.relative_to(TEMPLATE_DIR)
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        elif not dst.exists():
            shutil.copy2(src, dst)
            log.info("Создан %s", dst)
    for name in ("out", "inbox"):
        (settings.workspace / name).mkdir(exist_ok=True)


def make_ask(bot: Bot, agent: Agent) -> Ask:
    async def ask(chat_id: int, prompt: str) -> None:
        async with ChatActionSender.typing(bot=bot, chat_id=chat_id):
            await agent.ask(chat_id, prompt, on_text=lambda text: send_text(bot, chat_id, text))

    return ask


def build_router(settings: Settings, bot: Bot, agent: Agent, ask: Ask) -> Router:
    router = Router()
    allowed = F.from_user.id.in_(set(settings.allowed_users))

    async def ask_safely(message: Message, prompt: str) -> None:
        try:
            await ask(message.chat.id, prompt)
        except Exception as e:
            await message.answer(f"⚠️ Ошибка: {type(e).__name__}: {e}\nПопробуй ещё раз или /new")

    @router.message(CommandStart(), allowed)
    @router.message(Command("help"), allowed)
    async def start(message: Message) -> None:
        await message.answer(HELP)

    @router.message(Command("new", "clear"), allowed)
    async def new(message: Message) -> None:
        await agent.reset(message.chat.id)
        await message.answer("🧹 Контекст очищен. План и журнал на месте — начинаем новую беседу.")

    @router.message(Command("stop"), allowed)
    async def stop(message: Message) -> None:
        stopped = await agent.interrupt(message.chat.id)
        await message.answer("⏹ Остановил" if stopped else "Сейчас ничего не выполняется")

    @router.message(Command("status"), allowed)
    async def status(message: Message) -> None:
        info = agent.info(message.chat.id)
        await message.answer(
            f"Движок: {settings.engine}\n"
            f"Сессия: {info.session_id or '— (новая)'}\n"
            f"Процесс запущен: {'да' if info.active else 'нет'}\n"
            f"Ходов с запуска: {info.turns}\n"
            + ("Оплата: подписка ChatGPT (лимиты Codex)\n" if settings.engine == "codex"
               else f"Стоимость: ${info.cost_usd:.3f}\n")
            +
            f"Рабочая папка: {settings.workspace}"
        )

    @router.message(F.photo, allowed)
    async def photo(message: Message) -> None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        rel = Path("inbox") / f"{stamp}.jpg"
        await bot.download(message.photo[-1], destination=settings.workspace / rel)
        caption = message.caption or "(без подписи)"
        await ask_safely(message, f"Пользователь прислал фото: {rel} — посмотри изображение доступным инструментом.\nПодпись: {caption}")

    @router.message(F.document, allowed)
    async def document(message: Message) -> None:
        name = Path(message.document.file_name or "file").name
        rel = Path("inbox") / f"{datetime.now():%Y%m%d-%H%M%S}-{name}"
        await bot.download(message.document, destination=settings.workspace / rel)
        await ask_safely(message, f"Пользователь прислал файл: {rel}\nПодпись: {message.caption or '(без подписи)'}")

    @router.message(F.text, allowed)
    async def text(message: Message) -> None:
        await ask_safely(message, message.text)

    @router.message()
    async def denied(message: Message) -> None:
        user = message.from_user
        log.warning("Отклонено сообщение от %s (@%s)", user.id if user else "?", user.username if user else "?")
        if user:
            await message.answer(f"Это приватный бот. Твой Telegram id: {user.id}")

    return router


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    prepare_workspace(settings)

    bot = Bot(settings.telegram_token)
    renderer = Renderer(width=settings.render_width)
    agent_cls = CodexAgent if settings.engine == "codex" else Agent
    agent = agent_cls(settings, bot, renderer, ExerciseDb(settings.exercises_dir))

    ask = make_ask(bot, agent)
    dp = Dispatcher()
    dp.include_router(build_router(settings, bot, agent, ask))

    scheduler = build_scheduler(settings, ask)
    scheduler.start()

    await bot.set_my_commands(COMMANDS)
    log.info("Бот запущен, рабочая папка %s", settings.workspace)
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await agent.close()
        await renderer.close()
        await bot.session.close()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
