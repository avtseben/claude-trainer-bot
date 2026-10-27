#!/usr/bin/env bash
# Установка на VPS (Debian/Ubuntu) без Docker: venv, Chromium для рендера, база упражнений.
# Запускать от пользователя, под которым будет работать бот (не root).
set -euo pipefail

cd "$(dirname "$0")/.."

if [ "$(id -u)" -eq 0 ]; then
  echo "Не запускайте от root: создайте пользователя (sudo adduser trainer) и запустите от него." >&2
  exit 1
fi

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .

# Системные библиотеки Chromium + шрифты с кириллицей и эмодзи (нужен sudo).
sudo .venv/bin/playwright install-deps chromium
sudo apt-get install -y fonts-noto-core fonts-noto-color-emoji git
.venv/bin/playwright install chromium

[ -f .env ] || { cp .env.example .env; echo "Создан .env — заполните его."; }

set -a; . ./.env; set +a
./scripts/fetch_exercises.sh

echo
echo "Дальше:"
echo "  1. Заполните .env"
echo "  2. Проверка:  .venv/bin/trainer-bot"
echo "  3. Автозапуск: см. deploy/trainer-bot.service"
