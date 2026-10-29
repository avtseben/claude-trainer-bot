# Runbook: бот на VPS под отдельным пользователем

Схема: бот работает от пользователя `trainer` без sudo и без пароля, как systemd-сервис.
Память тренера лежит в `/home/trainer/trainer`, код — в `/home/trainer/claude-trainer-bot`.
Входящие порты не нужны: бот сам опрашивает Telegram (long polling).

```
/home/trainer/
├── claude-trainer-bot/     код (git clone), .venv, .env
├── trainer/                память тренера: CLAUDE.md, plan.md, log.md, out/, inbox/, exercises-db/
├── .claude/                история сессий Claude (нужна для resume)
└── .cache/ms-playwright/   Chromium для рендера
```

Обозначения: `admin$` — ваш пользователь с sudo на VPS, `trainer$` — пользователь бота,
`mac$` — локальная машина.

Требования: Ubuntu 22.04+ или Debian 12+, 1 ГБ RAM минимум (лучше 2 ГБ: Chromium + Claude CLI),
~1 ГБ на диске.

---

## 0. Подготовить на Mac

**Токен Claude.** На сервере нет браузера для входа, поэтому нужен токен. Выберите один:

```bash
mac$ claude setup-token        # токен подписки Pro/Max → CLAUDE_CODE_OAUTH_TOKEN
```

или API-ключ с console.anthropic.com → `ANTHROPIC_API_KEY`.

**Остановить локального бота** (Ctrl+C в терминале, где он запущен). Telegram отдаёт обновления
только одному получателю: если оба бота живы, сервер будет сыпать ошибкой
`Conflict: terminated by other getUpdates request`.

---

## 1. Создать пользователя

```bash
admin$ sudo adduser --disabled-password --gecos "Claude trainer bot" trainer
```

- `--disabled-password` — входа по паролю нет, по SSH под ним тоже не ходим.
- В группу `sudo` **не добавлять**: Claude выполняет shell-команды от имени этого пользователя.
- Работать под ним: `sudo -iu trainer`.

Проверка:

```bash
admin$ id trainer          # groups=... без sudo
admin$ sudo -l -U trainer  # "is not allowed to run sudo"
```

## 2. Системные пакеты

```bash
admin$ sudo apt-get update
admin$ sudo apt-get install -y python3 python3-venv git \
         fonts-noto-core fonts-noto-color-emoji tzdata
admin$ python3 --version   # нужен 3.11+
```

Если RAM 1 ГБ — добавить swap, иначе Chromium может прибить OOM-killer:

```bash
admin$ sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
admin$ sudo mkswap /swapfile && sudo swapon /swapfile
admin$ echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 3. Код и зависимости (от trainer)

```bash
admin$ sudo -iu trainer
trainer$ git clone https://github.com/avtseben/claude-trainer-bot.git
trainer$ cd claude-trainer-bot
trainer$ ./scripts/install.sh
```

Скрипт создаёт `.venv`, ставит пакет, скачивает Chromium в `~/.cache/ms-playwright`,
создаёт `.env` из примера и качает базу упражнений в `~/trainer/exercises-db` (~100 МБ).

## 4. Системные библиотеки Chromium (от admin)

```bash
trainer$ exit
admin$ sudo /home/trainer/claude-trainer-bot/.venv/bin/playwright install-deps chromium
```

## 5. Настроить `.env`

```bash
admin$ sudo -iu trainer
trainer$ nano ~/claude-trainer-bot/.env
trainer$ chmod 600 ~/claude-trainer-bot/.env
```

```ini
TELEGRAM_BOT_TOKEN=<токен @oknebest_bot>
TELEGRAM_ALLOWED_USERS=328812715
CLAUDE_CODE_OAUTH_TOKEN=<из шага 0>      # или ANTHROPIC_API_KEY=...
CLAUDE_MODEL=claude-sonnet-5-5
CLAUDE_MAX_BUDGET_USD=2
CLAUDE_ALLOW_BASH=true
TRAINER_WORKSPACE=~/trainer
TRAINER_TIMEZONE=Asia/Novosibirsk
MORNING_REMINDER=08:00
EVENING_CHECKIN=21:00
```

## 6. Перенести память тренера с Mac

Переносим план, журнал и заметки из локальной репетиции. Базу упражнений не везём —
она уже скачана. Файл сессий `.bot/sessions.json` **не переносим**: id сессий ссылаются на историю
в `~/.claude` на Mac, на сервере её нет, и resume упадёт.

```bash
mac$ cd ~/p/claude-trainer-bot/data/trainer
# --no-xattrs и COPYFILE_DISABLE: без macOS-атрибутов и файлов ._*, иначе GNU tar ругается
# "Ignoring unknown extended header keyword LIBARCHIVE.xattr..." (безвредно, но шумно)
mac$ COPYFILE_DISABLE=1 tar czf /tmp/trainer.tgz --no-xattrs --no-mac-metadata \
       --exclude=exercises-db --exclude=.bot --exclude='*.png' .
mac$ scp /tmp/trainer.tgz admin@<vps>:/tmp/
```

```bash
admin$ sudo -u trainer tar xzf /tmp/trainer.tgz -C /home/trainer/trainer
admin$ rm /tmp/trainer.tgz
admin$ sudo ls -la /home/trainer/trainer     # владелец trainer, есть plan.md, log.md, CLAUDE.md
```

Если начинаете с нуля — шаг пропустить: шаблон разложится сам при первом запуске.

## 7. Пробный запуск руками

```bash
admin$ sudo -iu trainer
trainer$ cd ~/claude-trainer-bot && .venv/bin/trainer-bot
```

В логе должно быть:

```
Загружено упражнений: 876
Бот запущен, рабочая папка /home/trainer/trainer
Run polling for bot @oknebest_bot
```

Предупреждения `ANTHROPIC_API_KEY и CLAUDE_CODE_OAUTH_TOKEN не заданы` быть **не должно**.
Напишите боту «что у меня сегодня?» и дождитесь карточки. Затем Ctrl+C и `exit`.

## 8. systemd

```bash
admin$ sudo cp /home/trainer/claude-trainer-bot/deploy/trainer-bot.service /etc/systemd/system/
admin$ sudo systemctl daemon-reload
admin$ sudo systemctl enable --now trainer-bot
admin$ systemctl status trainer-bot
admin$ journalctl -u trainer-bot -f
```

Юнит запускает бота от `trainer`, перезапускает при падении, запрещает повышение привилегий
и даёт писать только в `/home/trainer` (`ProtectSystem=strict`, `ProtectHome=tmpfs` + `BindPaths`).

## 9. Приёмка

- [ ] `/status` — сессия новая, рабочая папка `/home/trainer/trainer`
- [ ] «Что у меня завтра?» — приходит карточка со схемами
- [ ] Отчёт о тренировке — появляется запись в `~/trainer/log.md`
- [ ] `/new`, затем вопрос про план — бот отвечает по файлам, без старого контекста
- [ ] Фото — бот его видит
- [ ] `sudo systemctl restart trainer-bot`, затем сообщение — беседа продолжается (resume)
- [ ] На следующее утро в 08:00 приходит напоминание

---

## Эксплуатация

| Задача | Команда |
|---|---|
| Логи | `journalctl -u trainer-bot -f` (за сутки: `--since today`) |
| Перезапуск | `sudo systemctl restart trainer-bot` |
| Остановка | `sudo systemctl stop trainer-bot` |
| Посмотреть план | `sudo -u trainer cat /home/trainer/trainer/plan.md` |
| Стоимость | `/status` в боте (с момента запуска процесса) |

### Обновление кода

```bash
admin$ sudo -iu trainer
trainer$ cd ~/claude-trainer-bot && git pull && .venv/bin/pip install -e .
trainer$ exit
admin$ sudo systemctl restart trainer-bot
```

Шаблон тренера копируется в `~/trainer` **только для отсутствующих файлов**: новые шаблоны появятся сами,
а изменения в `CLAUDE.md` и существующих шаблонах — нет. Сверить вручную:

```bash
trainer$ diff ~/claude-trainer-bot/trainer_bot/workspace_template/CLAUDE.md ~/trainer/CLAUDE.md
```

### Откат

```bash
trainer$ cd ~/claude-trainer-bot && git log --oneline -5 && git checkout <commit>
trainer$ .venv/bin/pip install -e .
admin$ sudo systemctl restart trainer-bot
```

### Резервная копия

Ценное — `~/trainer` (кроме `exercises-db`) и история сессий `~/.claude/projects`.
Ежедневный архив через cron пользователя trainer:

```bash
trainer$ mkdir -p ~/backup && crontab -e
```

```cron
30 3 * * * tar czf ~/backup/trainer-$(date +\%F).tgz -C ~ --exclude=trainer/exercises-db trainer .claude/projects && find ~/backup -name 'trainer-*.tgz' -mtime +14 -delete
```

Забрать на Mac: `scp admin@<vps>:/home/trainer/backup/trainer-<дата>.tgz .`
(или сделать `~/trainer` git-репозиторием и пушить в приватный репозиторий).

### Сменить токен

Отредактировать `/home/trainer/claude-trainer-bot/.env` и `sudo systemctl restart trainer-bot`.
Токен Telegram отзывается в @BotFather → `/revoke`, токен подписки — повторным `claude setup-token`.

---

## Неполадки

| Симптом | Причина и что делать |
|---|---|
| `Conflict: terminated by other getUpdates request` | Бот запущен ещё где-то (Mac). Остановить второй экземпляр |
| `Invalid API key` / `401` / просьба залогиниться | Токен Claude не задан или истёк. Шаг 0 и 5 |
| Бот отвечает «Это приватный бот. Твой Telegram id: …» | id не в `TELEGRAM_ALLOWED_USERS` |
| `Executable doesn't exist ... ms-playwright` | Chromium не скачан: `sudo -iu trainer`, `.venv/bin/playwright install chromium` |
| `error while loading shared libraries` в логе рендера | Нет системных библиотек: шаг 4 |
| Квадратики вместо кириллицы или эмодзи на картинках | Нет шрифтов: `apt-get install fonts-noto-core fonts-noto-color-emoji` |
| Процесс убит, в `dmesg` OOM | Мало памяти: swap (шаг 2) или VPS побольше |
| После переноса бот падает на первом сообщении | Перенесли `.bot/sessions.json` с Mac. Удалить его или отправить `/new` |
| `JSON message exceeded maximum buffer size` | Старая версия кода: обновиться (лимит поднят до 32 МБ) |
| `TelegramNetworkError` время от времени | Сетевые обрывы, бот переподключается сам. Тревожно, только если не проходит минутами |
