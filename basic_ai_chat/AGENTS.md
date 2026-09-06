# AGENTS.md — Basic AI chat

## Запуск
```
cd basic_ai_chat && source venv/bin/activate && python app.py
```
Сервер: http://127.0.0.1:8000

## Конфигурация (providers.json)
Единый источник конфигурации — `providers.json` в корне проекта.
- Содержит список провайдеров, моделей и их capabilities
- Содержит API-ключи (файл добавлен в `.gitignore`)
- `active_provider` / `active_model` — текущий выбор
- `.env` больше не используется

## Архитектура
- Бэкенд: FastAPI (`app.py`), OpenAI SDK для запросов к LLM
- Фронтенд: vanilla HTML/JS
  - `templates/index.html` — разметка
  - `templates/pico.grey.min.css` — Pico CSS v2 (grey theme, classless)
  - `templates/style.css` — кастомные стили (базовые стили delegated Pico)
  - `templates/app.js` — логика (вынесена из HTML)
- Статика раздаётся через `StaticFiles(directory=templates)`
- Pydantic-схема `ChatRequest`: `message`, `free_history`, `controlled_history`, `constraints`
- История хранится только на фронте (JS-массивы `freeChatHistory` / `controlledChatHistory`)
- Мессенджер-отображение: сообщения пользователя справа, ответы ИИ слева
- Два варианта отображения ответов: два ответа рядом (свободный + контролируемый) или один ответ на всю ширину (только контролируемый)
- Sidebar (260px): инженерные параметры (Формат, Длина, Стоп-символ, Температура, Reasoning)
- Bottom panel: системный промпт (checkbox + textarea) + переключатель свободного чата + поле ввода сообщения

## providers.json — структура
```json
{
  "active_provider": "ollama",
  "active_model": "qwen2.5:3b",
  "providers": {
    "ollama": {
      "name": "Ollama (localhost)",
      "base_url": "http://localhost:11434/v1",
      "api_key": "",
      "models": [
        {
          "id": "qwen2.5:3b",
          "name": "Qwen 2.5 3B",
          "reasoning_effort": [],
          "temperature": { "min": 0, "max": 2, "step": 0.1, "default": 0.7 },
          "max_tokens": { "min": 5, "max": 4096, "default": 150 }
        }
      ]
    }
  }
}
```

### Поля модели
| Поле | Описание |
|------|----------|
| `id` | Идентификатор модели для API |
| `name` | Человекочитаемое название |
| `reasoning_effort` | Список поддерживаемых значений (пустой = параметр не поддерживается) |
| `temperature` | `{ min, max, step, default }` — диапазон и значения по умолчанию |
| `max_tokens` | `{ min, max, default }` — диапазон и значение по умолчанию |

## API
- `GET /` — отдаёт HTML-страницу
- `GET /api/providers` — список всех провайдеров и моделей из `providers.json`
- `GET /api/supported-values` — capabilities активной модели (reasoning_effort, temperature, max_tokens)
- `POST /api/switch-model` — смена провайдера/модели: `{ "provider": "...", "model": "..." }`, пересоздание OpenAI-клиента
- `POST /api/system-prompt` — принимает `{ "prompt": "..." }`, сохраняет системный промпт на сервере
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
- Контролируемый вызов: системный промпт из серверного хранилища, динамическая подстановка `constraints` (max_tokens, temperature, stop, response_format, reasoning_effort)
- Если модель поддерживает `reasoning_effort: "none"` — параметр включён по умолчанию со значением `none` (рассуждения выключены, экономия токенов)
- `reasoning_effort` со значением `low`/`medium`/`high` передаётся только при ручном выборе в UI
- `response_format` маппится: `{ text: 'text', json: 'json_object' }` для валидных значений API
- При ошибке 400 API из-за неподдерживаемого параметра (`reasoning_effort`, `response_format`) — автоматическое удаление и повтор запроса
- Удалённые параметры отображаются в `applied_params` как `"⚠ Сброшен"`

## Важные нюансы
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
- `addSystemPromptTurn(promptText, rawRequest)` — рендер системного промпта
- `sendMessage()` — отправка сообщения, вызов `POST /api/chat`
- `collectConstraints()` — сбор данных с панели настроек (включая reasoning_effort)
- `escapeHtml(s)` — XSS-защита
- `freeChatEnabled` — флаг свободного чата (по умолчанию `false`)
- Логика чекбоксов: `querySelectorAll('.setting-row[data-param]')` + обработчик `change`

## CSS-классы
- `.app-layout` — Grid-контейнер основной раскладки (sidebar + main)
- `.sidebar` — левая панель (260px, параметры)
- `.sidebar-header` — заголовок sidebar
- `.main-area` — правая область (flex-column)
- `.bottom-area` — фиксированная обёртка нижней панели
- `.bottom-panel` — визуальная панель (промпт + ввод)
- `.setting-row` — строка параметра (flex-wrap, label сверху, checkbox+control снизу)
- `.chats-container` — flex-column контейнер чата
- `.chat-row` — flex-column обёртка строки диалога
- `.chat-row.row-user` — выравнивание вправо
- `.chat-row.row-ai` — выравнивание влево
- `.msg-label` — лейбл автора сообщения
- `.message`, `.bubble` — сообщения
- `.ai-responses` — flex-контейнер для двух ответов ИИ
- `.ai-response-col` — колонка с одним ответом ИИ внутри `.ai-responses`
- `.ai-responses--single` — один ответ на всю ширину
- `.params-block`, `.param-badge`, `.param-badge--reason` — бейджи параметров
- `.params-row` — flex-контейнер для бейджей и счётчика токенов под ответом
- `.token-count` — счётчик токенов
- `.free-chat-toggle` — чекбокс свободного чата
- `.raw-json-toggle` — accordion для JSON

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

**Скоуп (scope)** — опционален, кратко на английском: `chat`, `backend`, `frontend`, `types`, `ui`, `config`.

**Примеры:**
```
feat(config): добавить providers.json с провайдерами и моделями
feat(chat): добавить reasoning_effort в панель параметров
refactor(backend): заменить .env на providers.json
fix(backend): убрать хардкод reasoning_effort в call_controlled
docs: актуализировать AGENTS.md
```
