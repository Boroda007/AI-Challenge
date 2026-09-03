# AGENTS.md — day01: ИИ-чат

## Запуск
```
cd day01 && source venv/bin/activate && python app.py
```
Сервер: http://127.0.0.1:8000

## Переменные окружения (day01/.env)
- `BASE_URL` — эндпоинт LLM API
- `API_KEY` — токен доступа
- `MODEL_NAME` — название модели

## Архитектура
- Бэкенд: FastAPI (app.py), OpenAI SDK для запросов к LLM
- Фронтенд: vanilla HTML/JS (templates/index.html)
- Markdown: библиотека `markdown` → `HTMLResponse` (не строка — FastAPI JSON-кодирует строки, экранируя `\n`)

## Важные нюансы
- `.env` загружается явно из директории скрипта, не из CWD
- Ответ ИИ отдаётся через `HTMLResponse`, иначе `\n` отображаются буквально
- CSS: сообщения пользователя — справа с серым фоном, ответы ИИ — на всю ширину
- Чат растягивается на всю высоту экрана (`flex: 1`)
