# TG → Obsidian Sync

Плагин синхронизирует тексты, картинки и YouTube-ссылки с FastAPI-бэкенда в vault.

## Установка через BRAT

1. Установи плагин [BRAT](https://github.com/TfTHacker/obsidian42-brat) в Obsidian
2. BRAT → **Add beta plugin** → укажи GitHub-репозиторий этого проекта
3. BRAT подтянет последний GitHub Release (`main.js`, `manifest.json`, `styles.css`)

Релизы публикуются workflow `Release Obsidian plugin (BRAT)` по тегу `v*`  
(например `git tag v1.0.1 && git push origin v1.0.1`).

## Ручная установка / разработка

1. `cd obsidian-plugin && npm install && npm run build`
2. Скопируй `main.js`, `manifest.json`, `styles.css` в  
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
