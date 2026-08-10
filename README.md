# Dumosbor2 — Telegram → Obsidian

Личный пайплайн: сообщения из Telegram сохраняются на сервере и по команде синхронизируются в vault Obsidian.

```
Telegram  →  Bot + API  →  PostgreSQL / media
                              ↓
                     Obsidian-плагин (sync)
```

## Что умеет

- **Текст и альбомы** — группировка медиа-групп, вики-ссылки на файлы
- **Любые вложения** — фото, видео, PDF и другие документы, аудио, voice
- **Короткие / длинные заметки** — short → daily note, длинные → отдельные статьи
- **YouTube** — метаданные ссылок (yt-dlp) в отдельный лог-файл
- **Single-user** — отвечает только админу после `/start`
- **Bearer-токен** — безопасный доступ плагина к API

## Стек

| Часть | Технологии |
|-------|------------|
| Бот | Python, aiogram 3 |
| API | FastAPI, SQLAlchemy, Alembic |
| БД | PostgreSQL |
| Плагин | TypeScript, Obsidian API |
| Инфра | Docker Compose / Railway |

## Быстрый старт

### 1. Сервер (Docker)

```bash
cp .env.example .env
# укажи BOT_TOKEN от @BotFather

docker compose up --build
```

API: `http://localhost:8000`  
Сервисы: `db`, `api`, `bot`; медиа в `./media_data`.

### 2. Telegram

1. Напиши боту `/start` (ты становишься админом)
2. `/get_token` — скопируй Bearer-токен
3. По желанию: `/set_image_path attachments` — папка для вики-ссылок

### 3. Obsidian-плагин

**Через BRAT** (рекомендуется):

1. Установи [BRAT](https://github.com/TfTHacker/obsidian42-brat)
2. Add beta plugin → репозиторий `matveyadamey/Dumosbor2`
3. Включи **TG → Obsidian Sync**

**Вручную:** см. [obsidian-plugin/README.md](obsidian-plugin/README.md)

В настройках плагина:

| Параметр | Пример |
|----------|--------|
| Server URL | `http://localhost:8000` или `https://….up.railway.app` |
| Bearer Token | из `/get_token` |
| Image Path | куда класть файлы (в т.ч. PDF) |
| Articles Dir | длинные заметки |
| Daily Note Dir | короткие (`YYYY-MM-DD.md`) |
| YouTube File Path | лог ссылок |

Команды палитры: **Синхронизировать**, **Очистить сервер**.

Скопируй шаблон daily note в vault:

`templates/daily_note_template.md` → `templates/daily_note_template.md` в корне vault.

## Как устроена синхронизация

1. Пишешь боту в Telegram (текст, картинки, PDF, ссылки на YouTube…)
2. Бот сохраняет запись в БД и файлы в shared volume
3. В Obsidian: **Синхронизировать**
   - тянет несинхронизированные тексты и YouTube
   - скачивает файлы через `/api/v1/media/{file_name}`
   - пишет заметки в vault
   - подтверждает получение (ACK)

## Деплой

Поддерживается **Railway** (`railway.toml`, Docker).  
Healthcheck: `/live` (процесс жив), проверка БД: `/health`.

Подробности окружения, API и CI — в [developer.md](developer.md).

## Релиз плагина

```bash
git tag v1.0.1
git push origin v1.0.1
```

GitHub Actions соберёт плагин и опубликует Release (`main.js`, `manifest.json`, `styles.css`) для BRAT.

## Разработка

```bash
pip install -r requirements-dev.txt
pre-commit install
pytest --cov
cd obsidian-plugin && npm ci && npm test && npm run build
```

Полный гайд: **[developer.md](developer.md)**.

## Структура репозитория

```
api/                 FastAPI
bot/                 Telegram-бот
core/                модели, конфиг, БД
obsidian-plugin/     плагин Obsidian
alembic/             миграции
templates/           шаблон daily note
tests/               автотесты
```

## Лицензия

MIT (если не указано иное в репозитории).
