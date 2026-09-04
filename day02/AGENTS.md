# AGENTS.md — day02: Формат ответа

## Запуск
```
cd day02 && source venv/bin/activate && python app.py
```
Сервер: http://127.0.0.1:8000

## Переменные окружения (day02/.env)
- `BASE_URL` — эндпоинт LLM API
- `API_KEY` — токен доступа
- `MODEL_NAME` — название модели

## Архитектура
- Бэкенд: FastAPI (`app.py`), OpenAI SDK для запросов к LLM
- Фронтенд: vanilla HTML/JS
  - `templates/index.html` — разметка
  - `templates/style.css` — стили (вынесены из HTML)
  - `templates/app.js` — логика (вынесена из HTML)
- Статика раздаётся через `StaticFiles(directory=templates)`
- Pydantic-схема `ChatRequest`: `message`, `free_history`, `controlled_history`, `constraints`
- История хранится только на фронте (JS-массивы `freeChatHistory` / `controlledChatHistory`)

## API
- `GET /` — отдаёт HTML-страницу
- `POST /api/chat` — принимает JSON (`ChatRequest`), возвращает:
  ```json
  {
    "free_response": { "content": "...", "usage": { "prompt": N, "completion": N, "total": N } },
    "controlled_response": {
      "content": "...",
      "finish_reason": "stop" | null,
      "applied_params": { "Длина": 50, "Температура": 0.7, ... },
      "usage": { "prompt": N, "completion": N, "total": N }
    }
  }
  ```
- Два параллельных вызова к LLM через `asyncio.gather` + `asyncio.to_thread`
- Свободный вызов: стандартные параметры
- Контролируемый вызов: динамическая подстановка `constraints` (max_tokens, temperature, stop, response_format, system_prompt)
- `response_format` маппится: `{ text: 'text', json: 'json_object' }` для валидных значений API

## Важные нюансы
- `.env` загружается явно из директории скрипта, не из CWD
- Импорт типов из `openai.types.chat.ChatCompletionMessageParam` — нужен для type hints в параметрах `messages`
- Две колонки чата: «Без ограничений» (левая) и «С ограничениями» (правая)
- Ширина колонок чата: `3fr 2fr 3fr` (CSS Grid)
- Панель настроек: табличная раскладка через CSS Grid
  - `.settings-headers` — заголовки групп (одинаковая высота)
  - `.settings-body` — параметры (две колонки)
  - `.prompt-layout` — Grid для «Системного промпта» (checkbox слева, textarea справа)
- Чекбоксы включают/выключают связанные control'ы (disabled-логика)
- Чекбокс «Системный промпт» управляет `disabled` textarea через `.prompt-layout`
- Под ответами ИИ выводится количество токенов (`.token-count`, `completion` only)
- В правой колонке под ответом выводятся `.param-badge` бейджи (finish_reason, applied_params)

## Frontend JS — ключевые функции
- `addTurn(userText, freeHtml, controlledHtml, finishReason, appliedParams, freeUsage, controlledUsage)` — рендер строки диалога (3 колонки)
- `collectConstraints()` — сбор данных с панели настроек в объект `constraints`
- `escapeHtml(s)` — XSS-защита
- Логика чекбоксов: `querySelectorAll('.setting-row[data-param]')` + обработчик `change`

## CSS-классы
- `.settings-panel` — Grid-контейнер панели настроек
- `.settings-headers` / `.settings-group-header` — заголовки групп
- `.settings-body` / `.settings-group` — тело параметров
- `.prompt-layout` — Grid для системного промпта
- `.prompt-textarea` — textarea системного промпта
- `.setting-row` — строка параметра (flex, height: 32px)
- `.chats-container` — Grid-контейнер чата (3fr 2fr 3fr)
- `.chat-row` — `display: contents` (обёртка)
- `.chat-ai-left`, `.chat-ai-right`, `.chat-user` — ячейки
- `.message`, `.bubble` — сообщения
- `.params-block`, `.param-badge`, `.param-badge--reason` — бейджи параметров
- `.token-count` — счётчик токенов под ответами

## Правила оформления коммитов

**Формат:**
```
<type>(<scope>): <описание на русском>
```

**Типы (type):**
| Тег | Когда использовать |
|-----|-------------------|
| `feat` | Новая функциональность |
| `fix` | Исправление бага |
| `refactor` | Рефакторинг без изменения поведения |
| `docs` | Только документация |
| `style` | CSS, форматирование, визуальные изменения |
| `test` | Тесты |
| `chore` | Сборка, зависимости, техническая работа |

**Скоуп (scope)** — опционален, кратко на английском: `chat`, `backend`, `frontend`, `types`, `ui`.

**Примеры:**
```
feat(chat): добавить две параллельные колонки чата с панелью настроек
refactor(backend): переработать эндпоинт /api/chat с поддержкой constraints
fix(types): исправить type hints для messages в вызовах OpenAI API
docs: актуализировать AGENTS.md
style(ui): добавить disabled-логику для чекбоксов панели настроек
```
