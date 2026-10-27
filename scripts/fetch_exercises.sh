#!/usr/bin/env bash
# Скачивает free-exercise-db (Unlicense, ~870 упражнений с фото, ~100 МБ) в рабочую папку тренера.
set -euo pipefail

WORKSPACE="${TRAINER_WORKSPACE:-$HOME/trainer}"
WORKSPACE="${WORKSPACE/#\~/$HOME}"
TARGET="$WORKSPACE/exercises-db"

if [ -d "$TARGET/.git" ]; then
  echo "Обновляю $TARGET"
  git -C "$TARGET" pull --ff-only
else
  mkdir -p "$WORKSPACE"
  git clone --depth 1 https://github.com/yuhonas/free-exercise-db.git "$TARGET"
fi

echo "Готово: $(python3 -c "import json;print(len(json.load(open('$TARGET/dist/exercises.json'))))") упражнений"
