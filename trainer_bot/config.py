"""Настройки бота из переменных окружения (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _csv_ints(value: str) -> list[int]:
    return [int(x) for x in value.replace(" ", "").split(",") if x]


def _time_or_none(value: str) -> tuple[int, int] | None:
    value = value.strip()
    if not value:
        return None
    hours, minutes = value.split(":")
    return int(hours), int(minutes)


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    allowed_users: list[int]
    workspace: Path
    timezone: str = "Europe/Moscow"
    model: str | None = None
    max_budget_usd: float | None = None
    allow_bash: bool = True
    morning_reminder: tuple[int, int] | None = (8, 0)
    evening_checkin: tuple[int, int] | None = (21, 0)
    render_width: int = 800

    @property
    def owner_chat_id(self) -> int:
        """Первый пользователь из списка — получатель напоминаний."""
        return self.allowed_users[0]

    @property
    def exercises_dir(self) -> Path:
        return self.workspace / "exercises-db"

    @property
    def state_dir(self) -> Path:
        return self.workspace / ".bot"


def load_settings() -> Settings:
    load_dotenv()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN не задан (см. .env.example)")

    allowed = _csv_ints(os.environ.get("TELEGRAM_ALLOWED_USERS", ""))
    if not allowed:
        raise SystemExit("TELEGRAM_ALLOWED_USERS пуст — бот был бы открыт всем")

    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")):
        raise SystemExit("Нужен ANTHROPIC_API_KEY или CLAUDE_CODE_OAUTH_TOKEN")

    budget = os.environ.get("CLAUDE_MAX_BUDGET_USD", "").strip()

    return Settings(
        telegram_token=token,
        allowed_users=allowed,
        workspace=Path(os.environ.get("TRAINER_WORKSPACE", "~/trainer")).expanduser().resolve(),
        timezone=os.environ.get("TRAINER_TIMEZONE", "Europe/Moscow"),
        model=os.environ.get("CLAUDE_MODEL") or None,
        max_budget_usd=float(budget) if budget else None,
        allow_bash=os.environ.get("CLAUDE_ALLOW_BASH", "true").lower() == "true",
        morning_reminder=_time_or_none(os.environ.get("MORNING_REMINDER", "08:00")),
        evening_checkin=_time_or_none(os.environ.get("EVENING_CHECKIN", "21:00")),
        render_width=int(os.environ.get("RENDER_WIDTH", "800")),
    )
