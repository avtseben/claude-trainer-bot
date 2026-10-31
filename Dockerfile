FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright \
    TRAINER_WORKSPACE=/home/app/trainer

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates fonts-noto-core fonts-noto-color-emoji tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node:22-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN node /usr/local/lib/node_modules/npm/bin/npm-cli.js install -g @openai/codex@0.166.0

WORKDIR /app
COPY pyproject.toml README.md ./
COPY trainer_bot ./trainer_bot
COPY scripts ./scripts
RUN pip install . \
    && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 app
USER app

# trainer/ — память тренера (план, журнал, база упражнений), .claude/ — история сессий Claude.
VOLUME ["/home/app/trainer", "/home/app/.claude", "/home/app/.codex"]

CMD ["sh", "-c", "[ -d \"$TRAINER_WORKSPACE/exercises-db\" ] || ./scripts/fetch_exercises.sh; exec trainer-bot"]
