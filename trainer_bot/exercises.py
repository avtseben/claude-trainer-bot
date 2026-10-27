"""Поиск по локальной копии free-exercise-db (https://github.com/yuhonas/free-exercise-db)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Exercise:
    id: str
    name: str
    level: str | None
    equipment: str | None
    category: str | None
    primary_muscles: list[str]
    secondary_muscles: list[str]
    instructions: list[str]
    images: list[str]

    def summary(self) -> str:
        muscles = ", ".join(self.primary_muscles) or "-"
        return f"{self.id} | {self.name} | {muscles} | {self.equipment or '-'} | {self.level or '-'}"


class ExerciseDb:
    def __init__(self, root: Path):
        self.root = root
        self._items: dict[str, Exercise] = {}
        self._load()

    @property
    def available(self) -> bool:
        return bool(self._items)

    def _load(self) -> None:
        index = self.root / "dist" / "exercises.json"
        if not index.exists():
            log.warning("База упражнений не найдена: %s (запустите scripts/fetch_exercises.sh)", index)
            return
        for raw in json.loads(index.read_text(encoding="utf-8")):
            item = Exercise(
                id=raw["id"],
                name=raw["name"],
                level=raw.get("level"),
                equipment=raw.get("equipment"),
                category=raw.get("category"),
                primary_muscles=raw.get("primaryMuscles") or [],
                secondary_muscles=raw.get("secondaryMuscles") or [],
                instructions=raw.get("instructions") or [],
                images=raw.get("images") or [],
            )
            self._items[item.id] = item
        log.info("Загружено упражнений: %d", len(self._items))

    def get(self, exercise_id: str) -> Exercise | None:
        return self._items.get(exercise_id)

    def image_paths(self, exercise: Exercise) -> list[Path]:
        paths = [self.root / "exercises" / image for image in exercise.images]
        return [p for p in paths if p.exists()]

    def search(
        self,
        query: str = "",
        muscle: str = "",
        equipment: str = "",
        level: str = "",
        limit: int = 15,
    ) -> list[Exercise]:
        tokens = query.lower().split()
        muscle = muscle.lower()
        equipment = equipment.lower()
        level = level.lower()

        found = []
        for item in self._items.values():
            name = item.name.lower()
            if not all(token in name for token in tokens):
                continue
            if muscle and not any(muscle in m for m in item.primary_muscles + item.secondary_muscles):
                continue
            if equipment and equipment not in (item.equipment or ""):
                continue
            if level and level != (item.level or ""):
                continue
            found.append(item)
            if len(found) >= limit:
                break
        return found
