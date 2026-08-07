# podslyshano-bots v2

Telegram-боты «Подслушано»: предложка, анонимный чат и **веб-панель админов**.

## Боты

| Сервис | Назначение |
|--------|------------|
| **proposal-bot** | Два режима: публикация в канал / переписка с админами |
| **chat-bot** | Анонимный чат: кнопки «Начать / Закончить диалог» |
| **admin-web** | Веб-панель для 2 админов (статистика, deanonymized данные) |

Оба бота доступны только подписчикам канала `TGK`.

## UX подписчика

### Предложка
- Любое сообщение в режиме **«Опубликовать в канал»** → анонимно в канал
- Кнопка **«Написать админам»** → переписка с админами (не в канал)

### Анонка
- **«Начать диалог»** — поиск собеседника
- **«Закончить диалог»** — stop
- Relay, reply, reactions как в обычном чате

## Админка

1. Напиши боту предложки: `/panel`
2. Перейди по ссылке `https://<домен>/auth?token=...` (Bothost) или `http://<IP>:8080/auth?token=...` (VPS)
3. В панели: dashboard, публикации, обращения, чаты, пользователи, блокировки

## Bothost Pro (рекомендуется)

Один контейнер: Redis + оба бота + админка. Подробно: [deploy/bothost/README.md](deploy/bothost/README.md)

```text
Git: https://github.com/plvng/podslyshano-bots
Dockerfile: корневой Dockerfile (bothost)
Foreign IP: включить в профиле Bothost
```

## VPS / Docker Compose

```bash
cp .env.example .env
# заполни токены, TGK, ADMINS, ADMIN_WEB_URL

docker compose up -d --build
bash scripts/healthcheck.sh
```

Используется `Dockerfile.vps` (отдельные контейнеры + Redis).

## Yandex Cloud / другой VPS

1. VM: Ubuntu 24.04, 2 vCPU / 2 GB
2. Порты **22**, **8080**
3. `bash deploy/yandex-setup.sh` → `.env` → `docker compose up -d --build`

> Telegram Bot API с российских облаков (Yandex, Selectel) часто заблокирован. Bothost с foreign IP или VPS за рубежом надёжнее.

## Миграция legacy

```bash
docker compose run --rm \
  -v "$(pwd)/users.json:/app/users.json:ro" \
  -v "$(pwd)/blocked.json:/app/blocked.json:ro" \
  proposal-bot \
  python scripts/migrate_legacy.py --users /app/users.json --blocked /app/blocked.json
```

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `PROPOSAL_BOT_TOKEN` | Токен бота предложки |
| `CHAT_BOT_TOKEN` | Токен бота анонки |
| `TGK` | Канал (`@channel` или `-100...`) |
| `ADMINS` | 2 admin user id через запятую |
| `ADMIN_WEB_URL` | URL админки (Bothost: auto из `DOMAIN`) |
| `REDIS_URL` | Redis URL |
| `DATABASE_PATH` | Путь к SQLite (`/app/data/bots.db` на Bothost) |

## Структура

```
src/
├── common/       # config, db, keyboards, subscription cache
├── proposal_bot/
├── chat_bot/
└── admin_web/    # FastAPI + Jinja2 panel
deploy/
└── bothost/      # all-in-one для Bothost Pro
```
