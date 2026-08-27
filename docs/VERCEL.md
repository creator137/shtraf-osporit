# Деплой в Vercel

Проект состоит из двух Vercel-проектов:

- `admin` — React/Vite админка;
- `backend` — FastAPI API.

Telegram-бот работает через webhook endpoint FastAPI. Это позволяет обрабатывать
обновления Telegram в serverless-функции без постоянно работающего polling
процесса.

## 1. Подготовить PostgreSQL

Для production нужен внешний PostgreSQL с публичным подключением, например
Neon, Supabase или другой PostgreSQL-провайдер.

Не используйте локальный `localhost` в production.

## 2. Создать проект backend

В Vercel импортируйте этот Git-репозиторий и укажите:

- **Root Directory:** `backend`;
- **Framework Preset:** `Other`;
- **Build Command:** оставить пустым;
- **Output Directory:** оставить пустым.

Vercel обнаружит `api/index.py` и опубликует FastAPI-приложение как
serverless function.

Переменные окружения backend:

```text
DATABASE_URL=postgresql+asyncpg://...
BOT_TOKEN=...
ADMIN_ORIGIN=https://<admin-domain>.vercel.app
REDIS_URL=redis://...
TELEGRAM_WEBHOOK_SECRET=...
DOCUMENT_STORAGE=telegram
OCR_PROVIDER=ocrspace
OCR_SPACE_API_KEY=...
OCR_SPACE_LANGUAGE=rus
```

После добавления переменных выполните миграции из окружения, где доступен
production PostgreSQL:

```bash
cd backend
DATABASE_URL='postgresql+asyncpg://...' uv run alembic upgrade head
```

## 3. Создать проект admin

Создайте второй Vercel-проект из того же репозитория:

- **Root Directory:** `admin`;
- **Framework Preset:** `Vite`;
- **Build Command:** `npm run build`;
- **Output Directory:** `dist`;
- **Install Command:** `npm install`.

Добавьте переменную окружения:

```text
VITE_API_URL=https://<backend-domain>.vercel.app
```

После деплоя обновите `ADMIN_ORIGIN` в backend на фактический домен админки и
сделайте redeploy backend.

## 4. Подключить Telegram webhook

После деплоя backend установите webhook на публичный адрес:

```bash
curl -fsS "https://api.telegram.org/bot<bot-token>/setWebhook" \
  --data-urlencode "url=https://<backend-domain>.vercel.app/telegram/webhook" \
  --data-urlencode "secret_token=<webhook-secret>"
```

Для webhook-режима нужны:

```text
DATABASE_URL=postgresql+asyncpg://...
BOT_TOKEN=...
REDIS_URL=redis://...
TELEGRAM_WEBHOOK_SECRET=...
DOCUMENT_STORAGE=telegram
OCR_PROVIDER=ocrspace
OCR_SPACE_API_KEY=...
OCR_SPACE_LANGUAGE=rus
```

## Ограничение документов

В режиме `DOCUMENT_STORAGE=telegram` документы не копируются на локальный диск:
в базе сохраняется Telegram `file_id`, а админка получает файл через Telegram API.
Это позволяет использовать Vercel без постоянного файлового хранилища.

## OCR

Для Stage 2 backend может отправлять загруженный документ в OCR.space:

```text
OCR_PROVIDER=ocrspace
OCR_SPACE_API_KEY=<ключ OCR.space>
OCR_SPACE_LANGUAGE=rus
```

Если `OCR_SPACE_API_KEY` не задан, используется тестовый ключ OCR.space
`helloworld`. Он подходит только для проверки интеграции и может упираться в
лимиты провайдера.

## Проверка после деплоя

1. Открыть `https://<backend-domain>.vercel.app/health`.
2. Открыть `https://<admin-domain>.vercel.app`.
3. Проверить отсутствие CORS-ошибок в браузере.
4. Проверить `POST /telegram/webhook` с корректным секретом.
5. Отправить боту `/start`.
6. Проверить пользователя и дело в админке.
