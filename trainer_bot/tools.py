"""MCP-инструменты, которые Claude вызывает, чтобы отправить что-то в Telegram."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aiogram import Bot
from aiogram.types import FSInputFile
from aiogram.utils.media_group import MediaGroupBuilder
from claude_agent_sdk import create_sdk_mcp_server, tool

from .exercises import ExerciseDb
from .render import Renderer

log = logging.getLogger(__name__)

SERVER_NAME = "tg"
TOOL_NAMES = ["send_photo", "send_artifact", "send_file", "search_exercises", "send_exercise"]
ALLOWED_TOOL_IDS = [f"mcp__{SERVER_NAME}__{name}" for name in TOOL_NAMES]

CAPTION_LIMIT = 1024


def _ok(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}]}


def _error(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "is_error": True}


def resolve_inside(workspace: Path, path: str) -> Path:
    """Путь относительно рабочей папки; выход за её пределы запрещён."""
    candidate = (workspace / path).resolve()
    if not candidate.is_relative_to(workspace):
        raise ValueError(f"Путь вне рабочей папки: {path}")
    if not candidate.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")
    return candidate


def build_tools(chat_id: int, bot: Bot, workspace: Path, renderer: Renderer, exercises: ExerciseDb):
    """Сервер собирается на каждый чат: инструменты знают, куда слать."""

    @tool(
        "send_photo",
        "Отправить пользователю в Telegram картинку (png/jpg/webp) из рабочей папки.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Путь относительно рабочей папки"},
                "caption": {"type": "string", "description": "Подпись, до 1024 символов"},
            },
            "required": ["path"],
        },
    )
    async def send_photo(args: dict[str, Any]) -> dict[str, Any]:
        try:
            path = resolve_inside(workspace, args["path"])
        except (ValueError, FileNotFoundError) as e:
            return _error(str(e))
        await bot.send_photo(chat_id, FSInputFile(path), caption=args.get("caption", "")[:CAPTION_LIMIT] or None)
        return _ok(f"Фото {args['path']} отправлено")

    @tool(
        "send_artifact",
        "Отрендерить HTML-файл из рабочей папки в PNG и отправить картинкой. "
        "Используй для карточек тренировок, планов на неделю, графиков прогресса.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "HTML-файл относительно рабочей папки, обычно out/*.html"},
                "caption": {"type": "string"},
                "width": {"type": "integer", "description": "Ширина вьюпорта в px, по умолчанию 800"},
                "attach_html": {"type": "boolean", "description": "Дополнительно прислать сам HTML-файл"},
            },
            "required": ["path"],
        },
    )
    async def send_artifact(args: dict[str, Any]) -> dict[str, Any]:
        try:
            html = resolve_inside(workspace, args["path"])
        except (ValueError, FileNotFoundError) as e:
            return _error(str(e))
        if html.suffix.lower() not in {".html", ".htm"}:
            return _error("Ожидается .html файл")

        png, fits_photo = await renderer.render(html, width=args.get("width"))
        caption = args.get("caption", "")[:CAPTION_LIMIT] or None
        if fits_photo:
            await bot.send_photo(chat_id, FSInputFile(png), caption=caption)
        else:
            # Слишком длинная картинка: Telegram сожмёт её до нечитаемости, шлём файлом.
            await bot.send_document(chat_id, FSInputFile(png), caption=caption)
        if args.get("attach_html"):
            await bot.send_document(chat_id, FSInputFile(html))
        rel = png.relative_to(workspace)
        return _ok(f"Артефакт отправлен ({'фото' if fits_photo else 'документ'}), PNG сохранён в {rel}")

    @tool(
        "send_file",
        "Отправить пользователю любой файл из рабочей папки документом (pdf, csv, md, html...).",
        {
            "type": "object",
            "properties": {"path": {"type": "string"}, "caption": {"type": "string"}},
            "required": ["path"],
        },
    )
    async def send_file(args: dict[str, Any]) -> dict[str, Any]:
        try:
            path = resolve_inside(workspace, args["path"])
        except (ValueError, FileNotFoundError) as e:
            return _error(str(e))
        await bot.send_document(chat_id, FSInputFile(path), caption=args.get("caption", "")[:CAPTION_LIMIT] or None)
        return _ok(f"Файл {args['path']} отправлен")

    @tool(
        "search_exercises",
        "Найти упражнения в локальной базе (~870 шт., названия на английском). "
        "Возвращает строки 'id | name | мышцы | инвентарь | уровень'. "
        "Мышцы: abdominals, abductors, adductors, biceps, calves, chest, forearms, glutes, hamstrings, "
        "lats, lower back, middle back, neck, quadriceps, shoulders, traps, triceps. "
        "Инвентарь: body only, dumbbell, barbell, kettlebells, bands, cable, machine, "
        "medicine ball, exercise ball, foam roll, e-z curl bar, other.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Слова из английского названия, напр. 'push up'"},
                "muscle": {"type": "string"},
                "equipment": {"type": "string"},
                "level": {"type": "string", "enum": ["beginner", "intermediate", "expert"]},
                "limit": {"type": "integer"},
            },
        },
    )
    async def search_exercises(args: dict[str, Any]) -> dict[str, Any]:
        if not exercises.available:
            return _error("База упражнений не загружена: запустите scripts/fetch_exercises.sh")
        found = exercises.search(
            query=args.get("query", ""),
            muscle=args.get("muscle", ""),
            equipment=args.get("equipment", ""),
            level=args.get("level", ""),
            limit=min(int(args.get("limit", 15)), 50),
        )
        if not found:
            return _ok("Ничего не найдено, попробуй другие слова или убери фильтры")
        return _ok("\n".join(item.summary() for item in found))

    @tool(
        "send_exercise",
        "Отправить пользователю фотографии техники упражнения из базы (обычно 2 кадра: старт и финиш). "
        "Подпись пиши по-русски: название, подходы×повторы, ключевые подсказки по технике.",
        {
            "type": "object",
            "properties": {
                "exercise_id": {"type": "string", "description": "id из search_exercises"},
                "caption": {"type": "string"},
            },
            "required": ["exercise_id"],
        },
    )
    async def send_exercise(args: dict[str, Any]) -> dict[str, Any]:
        item = exercises.get(args["exercise_id"])
        if item is None:
            return _error(f"Нет упражнения с id {args['exercise_id']}")
        images = exercises.image_paths(item)
        if not images:
            return _error(f"У упражнения {item.id} нет картинок")

        caption = args.get("caption") or item.name
        media = MediaGroupBuilder(caption=caption[:CAPTION_LIMIT])
        for image in images[:10]:
            media.add_photo(media=FSInputFile(image))
        await bot.send_media_group(chat_id, media=media.build())
        instructions = " ".join(item.instructions)
        return _ok(f"Отправлено {len(images)} фото «{item.name}». Инструкция из базы: {instructions}")

    return [send_photo, send_artifact, send_file, search_exercises, send_exercise]


def build_server(*args, **kwargs):
    return create_sdk_mcp_server(name=SERVER_NAME, tools=build_tools(*args, **kwargs))

