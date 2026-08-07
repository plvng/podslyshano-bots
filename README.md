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
2. Перейди по ссылке `http://<VM_IP>:8080/auth?token=...`
3. В панели: dashboard, публикации, обращения, чаты, пользователи, блокировки

## Быстрый старт

```bash
cp .env.example .env
# заполни токены, TGK, ADMINS, ADMIN_WEB_URL=http://<IP>:8080

docker compose up -d --build
bash scripts/healthcheck.sh
```

## Yandex Cloud

1. VM: Ubuntu 22.04, 2 vCPU / 2 GB, 15 GB SSD, `ru-central1-a`
2. Security Group: порты **22**, **8080** (8080 лучше ограничить IP админов)
3. На VM:

```bash
bash deploy/yandex-setup.sh
cp .env.example .env && nano .env
docker compose up -d --build
sudo systemctl start podslyshano-bots
```

## Миграция

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
| `ADMIN_WEB_URL` | `http://<VM_IP>:8080` |
| `REDIS_URL` | Redis URL |
| `DATABASE_PATH` | `/data/bots.db` |

## Структура

```
src/
├── common/       # config, db, keyboards, subscription cache
├── proposal_bot/
├── chat_bot/
└── admin_web/    # FastAPI + Jinja2 panel
```
