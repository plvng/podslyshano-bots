# podslyshano-bots

Telegram-боты для «Подслушано»: предложка («Слушаю тебя») и случайные знакомства.

## Боты

| Бот | Назначение |
|-----|------------|
| **proposal-bot** | Анонимная предложка в канал + связь с админами |
| **chat-bot** | Случайный собеседник (find/stop/relay) |

Оба бота доступны **только подписчикам канала** (`TGK`).

## Стек

- Python 3.12, aiogram 3
- SQLite — пользователи и блокировки
- Redis — очередь знакомств, пары, message map
- Docker Compose

## Быстрый старт (локально / на сервере)

```bash
cp .env.example .env
# заполни PROPOSAL_BOT_TOKEN, CHAT_BOT_TOKEN, TGK, ADMINS

docker compose up -d --build
docker compose logs -f
```

Проверка:

```bash
bash scripts/healthcheck.sh
```

## Миграция со старых хостингов

Скачай `users.json` с amvera и список заблокированных (если есть — `blocked.json`):

```bash
# blocked.json — просто список id: [123, 456]
# или {"blocked": [123, 456]}

docker compose run --rm \
  -v "$(pwd)/users.json:/app/users.json:ro" \
  -v "$(pwd)/blocked.json:/app/blocked.json:ro" \
  proposal-bot \
  python scripts/migrate_legacy.py --users /app/users.json --blocked /app/blocked.json
```

## Конфигурация

- `.env` — секреты и основные переменные
- [`config.yaml`](config.yaml) — keywords, badwords, тексты сообщений, emoji/effects

### Переменные окружения

| Переменная | Описание |
|------------|----------|
| `PROPOSAL_BOT_TOKEN` | Токен бота предложки |
| `CHAT_BOT_TOKEN` | Токен бота знакомств |
| `TGK` | Канал подслушано (`@channel` или `-100...`) |
| `ADMINS` | ID админов через запятую |
| `REDIS_URL` | URL Redis (по умолчанию `redis://redis:6379/0`) |
| `DATABASE_PATH` | Путь к SQLite (по умолчанию `/data/bots.db`) |

## Команды ботов

### Предложка
- Любое сообщение → публикация в канал (если не support/blocked)
- Ключевые слова / reply → админам
- Админ reply на `<code>user_id</code>` → ответ пользователю
- Админ шлёт numeric id → block/unblock

### Знакомства
- `/find` — найти собеседника
- `/stop` — прервать диалог или поиск
- `/online` — сколько в сети
- `/contact` — поделиться контактом
- `/get <id>` — инфо о пользователе (только админ канала)

## Деплой

Сейчас проект готов к деплою на любой VPS с Docker. В планах — Yandex Compute Cloud VM (~600–900 ₽/мес), но это делается отдельно, когда будешь готов.

### systemd (на сервере)

```ini
# /etc/systemd/system/podslyshano-bots.service
[Unit]
Description=Podslyshano Telegram Bots
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/podslyshano-bots
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

## Структура

```
src/
├── common/          # config, subscription, db, middleware
├── proposal_bot/    # предложка
└── chat_bot/        # знакомства
scripts/
├── migrate_legacy.py
└── healthcheck.sh
```

## Лицензия

Private / university project.
