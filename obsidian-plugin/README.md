# TG → Obsidian Sync

Плагин синхронизирует тексты, картинки и YouTube-ссылки с FastAPI-бэкенда в vault.

## Установка

1. `cd obsidian-plugin && npm install && npm run build`
2. Скопируй `main.js`, `manifest.json` в  
   `<Vault>/.obsidian/plugins/tg-obsidian-sync/`
3. Включи плагин в Community plugins
4. Скопируй `../templates/daily_note_template.md` в vault: `templates/daily_note_template.md`

## Настройки

- **Server URL** — например `http://localhost:8000` или Railway URL
- **Bearer Token** — из команды бота `/get_token`
- **Image Path / Articles Dir / Daily Note Dir / YouTube File Path**
- **Fetch on startup**

## Команды

- **Синхронизировать** — тянет `/api/v1/texts` + `/api/v1/youtube`, качает медиа, пишет заметки, шлёт ACK
- **Очистить сервер** — подтверждение → `DELETE /api/v1/cleanup`
