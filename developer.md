# Developer guide

Документация для разработки **Dumosbor2**: Telegram-бот + FastAPI + PostgreSQL + Obsidian-плагин.

## Архитектура

```
Telegram ──► bot (aiogram) ──► PostgreSQL
                 │                    ▲
                 ▼                    │
           media_data/  ◄────────── api (FastAPI)
                                      ▲
                                      │ Bearer
                              Obsidian plugin
```

| Компонент | Роль |
|-----------|------|
| **bot** | Принимает апдейты от единственного админа, сохраняет текст/медиа/YouTube в БД и shared volume |
| **api** | Отдаёт несинхронизированные записи плагину, стримит медиа, ACK, cleanup |
| **db** | PostgreSQL + Alembic |
| **obsidian-plugin** | Тянет данные в vault (статьи / daily / youtube.md) |

Локально (docker-compose): три сервиса `db`, `api`, `bot`.  
На Railway: один процесс (`APP_MODE=all`) — API и бот в `runner.py`.

Настройки (`admin_chat_id`, `bearer_token`, `image_path`) хранятся в таблице `settings` (не в `config.json`), чтобы bot и api шарили состояние через БД.

## Структура репозитория

```
api/                 FastAPI: auth, routes, /live, /health
bot/                 aiogram: handlers, middlewares, services
core/                config, models, database, settings_repo
alembic/             миграции
runner.py            точка входа (APP_MODE=all|api|bot)
obsidian-plugin/     TypeScript-плагин (esbuild → main.js)
templates/           daily_note_template.md (копировать в vault)
tests/               pytest
.github/workflows/   CI + BRAT release
```

## Быстрый старт (Docker)

1. Скопируй env:

```bash
cp .env.example .env
# заполни BOT_TOKEN
```

2. Подними стек:

```bash
docker compose up --build
```

- API: `http://localhost:8000`
- Health (БД): `GET /health`
- Liveness (Railway): `GET /live`
- Медиа: `./media_data` ↔ `/app/media_data` в `api` и `bot`

3. В Telegram: `/start` → `/get_token` → вставь токен в настройки плагина.

## Локальная разработка без Docker (API/бот)

Требования: Python **3.11+**, PostgreSQL, Node **20+** (для плагина).

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements-dev.txt
pre-commit install

cp .env.example .env
# DATABASE_URL на локальный Postgres, например:
# postgresql+asyncpg://obsidian:change_me_secret@localhost:5432/tg_obsidian
```

Миграции и запуск:

```bash
alembic upgrade head

# оба процесса (как на Railway)
python -u runner.py

# только API
APP_MODE=api python -u runner.py

# только бот
APP_MODE=bot python -u runner.py
```

`PORT` читается из окружения (Railway задаёт сам; локально по умолчанию `8000`).

### Нормализация `DATABASE_URL`

Railway часто отдаёт `postgres://` / `postgresql://` и `sslmode=...`.  
`core.config.normalize_database_url` приводит URL к `postgresql+asyncpg://` и выкидывает libpq-параметры, которые asyncpg не понимает.

## Переменные окружения

| Переменная | Обязательно | Описание |
|------------|-------------|----------|
| `DATABASE_URL` | да | Postgres URL (asyncpg) |
| `BOT_TOKEN` | да для бота | токен Telegram Bot API |
| `MEDIA_DIR` | нет | каталог медиа, default `/app/media_data` |
| `PORT` | нет | порт API, default `8000` |
| `APP_MODE` | нет | `all` (default) \| `api` \| `bot` |

Compose дополнительно использует `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`.

## Telegram-бот

### Авторизация

- Первый `/start` пишет `admin_chat_id` в `settings`.
- `AdminFilterMiddleware` игнорирует всех остальных.
- До регистрации админа пропускается только `/start`.

### Команды

| Команда / UI | Действие |
|--------------|----------|
| `/start` | регистрация + inline-меню |
| `/set_image_path <path>` | путь для вики-ссылок `![[path/file]]` |
| `/get_token` | `secrets.token_hex(32)` → `bearer_token` в БД |

### Обработка контента

1. `AlbumBufferMiddleware` группирует `media_group_id` с задержкой **1.5 с**.
2. `process_data` → `save_text`:
   - медиа: `{message_id}_{index}.{ext}` в `MEDIA_DIR`;
   - в текст: `![[{image_path}/{file_name}]]`;
   - `short=True`, если «чистый» текст (без вики-ссылок) **&lt; 300** символов.
3. YouTube URL → `asyncio.to_thread(yt_dlp)` → таблица `youtube_links` (unique по `url`).

## FastAPI

Префикс данных: `/api/v1` (все эндпоинты под Bearer, кроме health/live).

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/live` | liveness (без БД) — Railway healthcheck |
| `GET` | `/health` | проверка `SELECT 1` к БД |
| `GET` | `/api/v1/texts` | `synced=false`, пагинация `limit`/`offset` |
| `POST` | `/api/v1/texts/ack` | body: `{ "message_ids": [int, ...] }` |
| `GET` | `/api/v1/media/{file_name}` | стриминг файла из `MEDIA_DIR` |
| `GET` | `/api/v1/youtube` | несинхронизированные ссылки |
| `POST` | `/api/v1/youtube/ack` | body: `{ "ids": ["uuid", ...] }` |
| `DELETE` | `/api/v1/cleanup` | `delete_message` в TG (best-effort), очистка media, `TRUNCATE` texts/images/youtube |

Авторизация: `Authorization: Bearer <token>` ↔ `settings.bearer_token`.

Пример:

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/texts
```

## Схема БД

Миграции: `alembic/versions/`. Новая ревизия:

```bash
alembic revision -m "describe_change"
alembic upgrade head
```

Таблицы:

- **texts** — `id`, `message_id`, `content`, `short`, `created_at`, `synced`
- **images** — `id`, `text_id`, `file_name`, `file_path`
- **youtube_links** — `id`, `url` (unique), `title`, `duration`, `created_at`, `synced`
- **settings** — `key`, `value` (токен, admin, image_path)

`cleanup` **не** трогает `settings`.

## Obsidian-плагин

Код: `obsidian-plugin/`. Подробности установки — `obsidian-plugin/README.md`.

```bash
cd obsidian-plugin
npm ci
npm test
npm run build   # → main.js
```

Логика sync:

1. `GET /texts` + `GET /youtube`
2. скачать картинки в `Image Path`
3. `short=false` → файл в `Articles Dir` (имя = санитайзер первых 20 символов; fallback `article_{message_id}.md`)
4. `short=true` → daily `YYYY-MM-DD.md`, дописать под `#telegram inbox` (шаблон `templates/daily_note_template.md`)
5. YouTube → строка в файл `YouTube File Path`
6. ACK только успешно сохранённых объектов

### BRAT / релиз

Workflow `.github/workflows/release-plugin.yml` по тегу `v*`:

```bash
git tag v1.0.1
git push origin v1.0.1
```

В Release попадают `main.js`, `manifest.json`, `styles.css`.  
В Obsidian: BRAT → Add beta plugin → URL этого репозитория.

## Тесты

```bash
pip install -r requirements-dev.txt

# минимальный env для импорта settings
set DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test   # Windows
export DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test # Unix

pytest --cov --cov-report=term-missing
```

- Порог coverage: **70%** (`pyproject.toml`), фактически держим выше.
- Плагин: `cd obsidian-plugin && npm test` (vitest).
- Тесты API/бота в основном на моках БД (реальный Postgres для unit/CI не нужен).

## Линтинг и pre-commit

Ruff (check + format) настроен в `pyproject.toml`.

```bash
ruff check --fix .
ruff format .
```

Pre-commit (`.pre-commit-config.yaml`):

- `ruff` с `--fix`
- `ruff-format`

```bash
pre-commit install
pre-commit run --all-files
```

## CI

`.github/workflows/ci.yml` на `push`/`pull_request` в `main`/`master`:

1. `ruff check` + `ruff format --check`
2. `pytest --cov`
3. сборка и тесты Obsidian-плагина

## Деплой на Railway

Конфиг: `railway.toml` + `Dockerfile`.

- Build: Docker
- `preDeployCommand`: `alembic upgrade head`
- `startCommand`: `python -u runner.py` (`APP_MODE=all`)
- Healthcheck: **`/live`** (не `/health` — чтобы деплой не падал из‑за кратковременной недоступности БД)

В сервисе приложения:

1. Подключи Postgres plugin → `DATABASE_URL`
2. Задай `BOT_TOKEN`
3. `MEDIA_DIR` (и volume, если нужен персистентный диск для картинок)
4. `PORT` не переопределяй вручную

Логи старта: `>>> RUNNER STARTING <<<`, `>>> API LISTENING ON PORT ... <<<`, `>>> BOT STARTING <<<`.

## Типовой рабочий цикл

1. Ветка от `master`
2. Правки + тесты + `ruff`
3. PR → зелёный CI
4. Merge
5. При релизе плагина — тег `vX.Y.Z`

## Полезные соглашения

- Не коммить `.env`, `node_modules`, `.coverage`
- Ошибки сети/диска — в `try/except` с `logger.exception`
- Контракт ACK texts — **`message_ids`**, youtube — **UUID `ids`**
- Для Railway healthcheck использовать `/live`; `/health` — readiness/DB
