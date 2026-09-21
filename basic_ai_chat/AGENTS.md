# AGENTS.md — Basic AI chat

## Running
```
cd basic_ai_chat && source venv/bin/activate && python app.py
```
Server: http://127.0.0.1:8000

## Technology Stack

### Backend
- **FastAPI** (`app.py`) — веб-фреймворк на Python для асинхронных запросов к LLM
- **OpenAI SDK** — отправка запросов к OpenAI-compatible API endpoint

### Frontend
- **Vanilla JavaScript** — клиентская логика в отдельном файле `app.js`
- **HTML5 templates** — разметка интерфейса

### Styling
- **Pico CSS v2 (grey theme)** — базовые стили с classless подходом
- **Custom styles** (`style.css`) — кастомные стили, делегированные от Pico

> См. подробную документацию в [README.md](./README.md)


## API
- `GET /` — отдаёт HTML-страницу
- `GET /api/providers` — список всех провайдеров и моделей из `providers.json`
- `GET /api/supported-values` — capabilities активной модели (reasoning_effort, temperature, max_tokens)
- `POST /api/switch-model` — смена провайдера/модели: `{ "provider": "...", "model": "..." }`, пересоздание OpenAI-клиента
- `POST /api/chat` — принимает JSON (`ChatRequest`), возвращает:
  ```json
  {
    "free_response": {
      "raw": { "id": "...", "object": "chat.completion", "model": "...", "choices": [...], "usage": {...} },
      "raw_request": { "model": "...", "messages": [...] },
      "content": "...",
      "raw_content": "...",
      "usage": { "prompt": N, "completion": N, "total": N }
    },
    "controlled_response": {
      "raw": { "id": "...", "object": "chat.completion", "model": "...", "choices": [...], "usage": {...} },
      "raw_request": { "model": "...", "messages": [...], "temperature": 0.7, ... },
      "content": "...",
      "raw_content": "...",
      "finish_reason": "stop" | null,
      "applied_params": { "Длина": 50, "Температура": 0.7, "Reasoning": "high", "⚠ Сброшен": "reasoning_effort", ... },
      "usage": { "prompt": N, "completion": N, "total": N }
    }
  }
  ```
- Два параллельных вызова к LLM через `asyncio.gather` + `asyncio.to_thread`
- Свободный вызов: стандартные параметры, без системного промпта
- Контролируемый вызов: системный промпт из контролируемой истории (роль system), динамическая подстановка `constraints` (max_tokens, temperature, stop, response_format, reasoning_effort)
- Если модель поддерживает `reasoning_effort: "none"` — параметр включён по умолчанию со значением `none` (рассуждения выключены, экономия токенов)
- `reasoning_effort` со значением `low`/`medium`/`high` передаётся только при ручном выборе в UI
- `response_format` маппится: `{ text: 'text', json: 'json_object' }` для валидных значений API
- При ошибке 400 API из-за неподдерживаемого параметра (`reasoning_effort`, `response_format`) — автоматическое удаление и повтор запроса
- Удалённые параметры отображаются в `applied_params` как `"⚠ Сброшен"`

## Important Notes
- `providers.json` загружается из директории скрипта при старте
- `active_provider` / `active_model` определяют текущую конфигурацию
- `POST /api/switch-model` пересоздаёт OpenAI-клиент и обновляет `providers.json`
- Импорт типов из `openai.types.chat.ChatCompletionMessageParam` — нужен для type hints в параметрах `messages`
- Чекбоксы включают/выключают связанные control'ы (disabled-логика)
- Под ответами ИИ выводится количество токенов (`.token-count`, `completion` only)
- В правой колонке под ответом выводятся `.param-badge` бейджи (finish_reason, applied_params)

## Frontend JS — ключевые функции
- `loadConfig()` — загрузка конфига с `GET /api/supported-values`, обновление UI (select, sliders)
- `updateReasoningSelect(values)` — заполнение select для reasoning_effort (скрывает строку если список пуст; если поддерживается `none` — авто-включает чекбокс со значением `none`)
- `updateSlider(id, valueDisplayId, config)` — установка min/max/step/value для range-слайдеров
- `addTurn(...)` — рендер строки диалога
- `addSystemPromptTurn(promptText)` — рендер системного промпта
- `sendMessage()` — отправка сообщения, вызов `POST /api/chat`
- `collectConstraints()` — сбор данных с панели настроек (включая reasoning_effort)

## Commit Message Conventions

**Format:**
```
<type>(<scope>): <description in Russian>
```

**Types (type):**
| Tag | When to use |
|-----|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Refactoring without behavior change |
| `docs` | Documentation only |
| `style` | CSS, formatting, visual |
| `test` | Tests |
| `chore` | Build, dependencies, technical work |

**Scope (scope)** — optional, briefly in English: `chat`, `backend`, `frontend`, `types`, `ui`, `config`.

**Examples:**
```
feat(config): добавить providers.json с провайдерами и моделями
feat(chat): добавить reasoning_effort в панель параметров
refactor(backend): заменить .env на providers.json
fix(backend): убрать хардкод reasoning_effort в call_controlled
docs: актуализировать AGENTS.md
```
