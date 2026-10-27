import json
from pathlib import Path

import pytest

from trainer_bot.agent import SessionStore
from trainer_bot.exercises import ExerciseDb
from trainer_bot.telegram_text import split_message, to_legacy_markdown
from trainer_bot.tools import resolve_inside


@pytest.fixture
def db(tmp_path: Path) -> ExerciseDb:
    (tmp_path / "dist").mkdir()
    (tmp_path / "exercises" / "Pushups").mkdir(parents=True)
    (tmp_path / "exercises" / "Pushups" / "0.jpg").write_bytes(b"jpg")
    items = [
        {"id": "Pushups", "name": "Pushups", "level": "beginner", "equipment": "body only",
         "primaryMuscles": ["chest"], "secondaryMuscles": ["triceps"], "instructions": ["Push."],
         "category": "strength", "images": ["Pushups/0.jpg", "Pushups/1.jpg"]},
        {"id": "Barbell_Squat", "name": "Barbell Squat", "level": "intermediate", "equipment": "barbell",
         "primaryMuscles": ["quadriceps"], "secondaryMuscles": [], "instructions": [], "category": "strength",
         "images": []},
    ]
    (tmp_path / "dist" / "exercises.json").write_text(json.dumps(items))
    return ExerciseDb(tmp_path)


def test_search_by_name_and_filters(db: ExerciseDb):
    assert [e.id for e in db.search("squat")] == ["Barbell_Squat"]
    assert [e.id for e in db.search(muscle="triceps")] == ["Pushups"]
    assert db.search("squat", equipment="body only") == []


def test_image_paths_skip_missing_files(db: ExerciseDb):
    assert [p.name for p in db.image_paths(db.get("Pushups"))] == ["0.jpg"]


def test_missing_db_is_unavailable(tmp_path: Path):
    assert not ExerciseDb(tmp_path / "nope").available


def test_resolve_inside_blocks_escape(tmp_path: Path):
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "a.html").write_text("<p>")
    assert resolve_inside(tmp_path, "out/a.html") == tmp_path / "out" / "a.html"
    with pytest.raises(ValueError):
        resolve_inside(tmp_path, "../../etc/passwd")
    with pytest.raises(FileNotFoundError):
        resolve_inside(tmp_path, "out/missing.png")


def test_markdown_conversion():
    assert to_legacy_markdown("## План\n**3×10**") == "*План*\n*3×10*"


def test_split_message_on_newlines():
    chunks = split_message("a" * 30 + "\n" + "b" * 30, limit=40)
    assert chunks == ["a" * 30, "b" * 30]


def test_session_store_roundtrip(tmp_path: Path):
    store = SessionStore(tmp_path / "s.json")
    store.set(1, "abc")
    assert SessionStore(tmp_path / "s.json").get(1) == "abc"
    store.drop(1)
    assert SessionStore(tmp_path / "s.json").get(1) is None
