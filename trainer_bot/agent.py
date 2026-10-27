"""Сессии Claude по чатам: одна живая сессия на чат, id сохраняется между перезапусками."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from aiogram import Bot
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

from .config import Settings
from .exercises import ExerciseDb
from .render import Renderer
from .tools import ALLOWED_TOOL_IDS, SERVER_NAME, build_server

log = logging.getLogger(__name__)

TELEGRAM_CONTEXT = """
Ты общаешься с пользователем через Telegram-бота, а не в терминале.
- Пользователь видит только твой текст и то, что ты отправишь инструментами mcp__tg__*.
  Файлы, которые ты просто записал на диск, он не увидит.
- Пиши коротко, как в мессенджере. Форматирование: *жирный*, _курсив_, `код`, списки.
  Без таблиц и заголовков #: Telegram их не отображает. Таблицы и красивые планы делай
  HTML-артефактом и отправляй через mcp__tg__send_artifact.
- Сообщения в квадратных скобках [Напоминание ...] присылает планировщик, а не человек.
"""

OnText = Callable[[str], Awaitable[None]]


class SessionStore:
    """chat_id → session_id в JSON-файле, чтобы /clear и рестарт бота работали предсказуемо."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, str] = json.loads(path.read_text()) if path.exists() else {}

    def get(self, chat_id: int) -> str | None:
        return self._data.get(str(chat_id))

    def set(self, chat_id: int, session_id: str) -> None:
        self._data[str(chat_id)] = session_id
        self._save()

    def drop(self, chat_id: int) -> None:
        self._data.pop(str(chat_id), None)
        self._save()

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2))


@dataclass
class ChatState:
    client: ClaudeSDKClient
    lock: asyncio.Lock
    cost_usd: float = 0.0
    turns: int = 0


@dataclass(frozen=True)
class SessionInfo:
    session_id: str | None
    active: bool
    cost_usd: float
    turns: int


class Agent:
    def __init__(self, settings: Settings, bot: Bot, renderer: Renderer, exercises: ExerciseDb):
        self.settings = settings
        self.bot = bot
        self.renderer = renderer
        self.exercises = exercises
        self.store = SessionStore(settings.state_dir / "sessions.json")
        self._chats: dict[int, ChatState] = {}
        self._create_lock = asyncio.Lock()

    def _options(self, chat_id: int) -> ClaudeAgentOptions:
        tools = ["Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch", "TodoWrite"]
        if self.settings.allow_bash:
            tools.append("Bash")

        return ClaudeAgentOptions(
            cwd=str(self.settings.workspace),
            resume=self.store.get(chat_id),
            system_prompt={"type": "preset", "preset": "claude_code", "append": TELEGRAM_CONTEXT},
            # "project" подхватывает CLAUDE.md и .claude/ из рабочей папки тренера.
            setting_sources=["project"],
            mcp_servers={
                SERVER_NAME: build_server(chat_id, self.bot, self.settings.workspace, self.renderer, self.exercises)
            },
            allowed_tools=tools + ALLOWED_TOOL_IDS,
            # Спросить разрешения некого: всё, что не в allowed_tools, отклоняется.
            permission_mode="dontAsk",
            model=self.settings.model,
            max_budget_usd=self.settings.max_budget_usd,
        )

    async def _chat(self, chat_id: int) -> ChatState:
        async with self._create_lock:
            state = self._chats.get(chat_id)
            if state is None:
                client = ClaudeSDKClient(options=self._options(chat_id))
                await client.connect()
                state = ChatState(client=client, lock=asyncio.Lock())
                self._chats[chat_id] = state
            return state

    async def ask(self, chat_id: int, prompt: str, on_text: OnText) -> None:
        """Отправляет сообщение в сессию; каждый текстовый блок ответа уходит в on_text сразу."""
        state = await self._chat(chat_id)
        async with state.lock:
            try:
                await state.client.query(prompt)
                async for message in state.client.receive_response():
                    if isinstance(message, AssistantMessage) and message.parent_tool_use_id is None:
                        for block in message.content:
                            if isinstance(block, TextBlock) and block.text.strip():
                                await on_text(block.text)
                    elif isinstance(message, ResultMessage):
                        self.store.set(chat_id, message.session_id)
                        state.cost_usd += message.total_cost_usd or 0.0
                        state.turns += 1
                        if message.is_error:
                            await on_text(f"⚠️ Claude завершил ход с ошибкой: {message.subtype}")
            except Exception:
                # Процесс CLI мог упасть: выкидываем клиента, следующий запрос поднимет его с resume.
                log.exception("Ошибка в сессии чата %s", chat_id)
                await self._disconnect(chat_id)
                raise

    async def interrupt(self, chat_id: int) -> bool:
        state = self._chats.get(chat_id)
        if state is None or not state.lock.locked():
            return False
        await state.client.interrupt()
        return True

    async def reset(self, chat_id: int) -> None:
        """Аналог /clear: следующая реплика начнёт новую сессию."""
        state = self._chats.get(chat_id)
        if state is not None:
            await self.interrupt(chat_id)
            # Дождаться, пока прерванный ход отдаст ResultMessage и отпустит сессию.
            async with state.lock:
                await self._disconnect(chat_id)
        self.store.drop(chat_id)

    def info(self, chat_id: int) -> SessionInfo:
        state = self._chats.get(chat_id)
        return SessionInfo(
            session_id=self.store.get(chat_id),
            active=state is not None,
            cost_usd=state.cost_usd if state else 0.0,
            turns=state.turns if state else 0,
        )

    async def _disconnect(self, chat_id: int) -> None:
        state = self._chats.pop(chat_id, None)
        if state is None:
            return
        try:
            await state.client.disconnect()
        except Exception:
            log.warning("Не удалось корректно закрыть сессию чата %s", chat_id, exc_info=True)

    async def close(self) -> None:
        for chat_id in list(self._chats):
            await self._disconnect(chat_id)
