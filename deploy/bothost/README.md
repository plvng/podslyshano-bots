# Bothost Pro — деплой podslyshano-bots

All-in-one контейнер: Redis + proposal-bot + chat-bot + admin-web.

## Перед созданием бота

1. Тариф **Pro** (или Базовый+) активен
2. [Профиль](https://bothost.ru/profile.php) → **«Зарубежный IP для API и нейросетей»** → **ВКЛ**
3. Старые инстансы ботов с теми же токенами **остановлены** (amvera, bothost, Yandex)

## Создание бота

1. [bothost.ru/create-bot.php](https://bothost.ru/create-bot.php)
2. **Git URL:** `https://github.com/plvng/podslyshano-bots`
3. **Ветка:** `main`
4. **Собственный Dockerfile:** включить (корневой `Dockerfile`)
5. **Веб-интерфейс / домен:** включить (админ-панель)
6. **Bot Token:** можно указать proposal-токен (оба токена задаются в env ниже)

## Переменные окружения

| Key | Value |
|-----|-------|
| `PROPOSAL_BOT_TOKEN` | токен бота предложки |
| `CHAT_BOT_TOKEN` | токен бота анонки |
| `TGK` | `@anonmgutu` |
| `ADMINS` | `1189297534,998304636` |
| `DATABASE_PATH` | `/app/data/bots.db` |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` |
| `ADMIN_WEB_URL` | `https://<ваш-домен>.bothost.tech` (опционально — подставится из `DOMAIN`) |

Bothost автоматически задаёт `DOMAIN` и `PORT`. `ADMIN_WEB_URL` можно не указывать — возьмётся из `DOMAIN`.

## После деплоя

1. `https://<домен>/health` → `{"status":"ok"}`
2. Proposal bot: `/start`, публикация, `/panel`
3. Chat bot: «Начать диалог» / «Закончить диалог»
4. Админка: перейти по ссылке из `/panel`

## Обновление

Push в `main` → в панели Bothost «Обновить из Git» (или webhook, если настроен).

## Локальная проверка образа

```bash
docker build -t podslyshano-bothost .
docker run --rm -p 8080:8080 --env-file .env podslyshano-bothost
```

## VPS (альтернатива)

Docker Compose использует `Dockerfile.vps` — см. корневой [README.md](../../README.md).
