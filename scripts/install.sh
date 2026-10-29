#!/usr/bin/env bash
# Установка бота от имени его пользователя (без sudo): venv, Chromium, база упражнений.
# Системные пакеты ставит администратор — см. docs/DEPLOY.md, шаги 2 и 4.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ "$(id -u)" -eq 0 ]; then
  echo "Не запускайте от root: sudo -iu trainer, затем ./scripts/install.sh" >&2
  exit 1
fi

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .

# Только сам браузер, в ~/.cache/ms-playwright. Системные библиотеки — отдельно от root.
.venv/bin/playwright install chromium

[ -f .env ] || { cp .env.example .env; chmod 600 .env; echo "Создан .env — заполните его."; }

set -a; . ./.env; set +a
./scripts/fetch_exercises.sh

echo
echo "Готово. Дальше (от администратора):"
echo "  sudo $(pwd)/.venv/bin/playwright install-deps chromium"
echo "и шаги из docs/DEPLOY.md."
