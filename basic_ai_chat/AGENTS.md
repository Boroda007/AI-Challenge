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
  - `templates/index.html` — разметка (3 вкладки: Системный промпт / Чат / Агент)
  - `templates/pico.grey.min.css` — Pico CSS v2 (grey theme, classless)
  - `templates/style.css` — кастомные стили (базовые стили delegated Pico)
  - `templates/app.js` — логика чата и системного промпта
  - `templates/agent.js` — логика агента (история, отправка, рендер шагов как диалога)
- Агент: `agent.py` — схемы, промпт, tools, `execute_tool`, `agent_loop` (реализован)
- Статика раздаётся через `StaticFiles(directory=templates)`
- Pydantic-схема `ChatRequest`: `message`, `free_history`, `controlled_history`, `constraints`
- История чата хранится только на фронте (JS-массивы `freeChatHistory` / `controlledChatHistory`); история агента — массив `agentHistory` (роли user/assistant)
- Мессенджер-отображение: сообщения пользователя справа, ответы/шаги ИИ слева
- Два варианта отображения ответов чата: два ответа рядом (свободный + контролируемый) или один ответ на всю ширину (только контролируемый)
- Ответы агента рендерятся как **диалог**: реплика клиента, затем каждый проход — реплика «Агент · Шаг N» с человекочитаемым текстом, финальный ответ — последняя реплика
- Для `compare_responses` внутри шага рисуется «граф»: dispatch (агент → N субагентов) и ответы субагентов
- Sidebar (260px): инженерные параметры (Формат, Длина, Стоп-символ, Температура, Reasoning)
- Bottom panel: системный промпт (textarea) + переключатель свободного чата + поле ввода сообщения (по активной вкладке)

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
- Ядро LLM-вызовов — `call_llm(message, history, constraints, system_prompt)` — общая функция для всех режимов
- Свободный вызов: `call_free()` — обёртка без системного промпта и constraints
- Контролируемый вызов: `call_controlled()` — обёртка с системным промптом и constraints
- В `call_llm` включён дефолт: если модель поддерживает `reasoning_effort: "none"`, а параметр не задан в `constraints` — подставляется `"none"` (рассуждения выключены, экономия токенов). Работает для чата, агента и субагентов `compare_responses` (иначе рассуждающие модели тратят лимит `max_tokens` на reasoning и возвращают пустой `content`)
- `reasoning_effort` со значением `low`/`medium`/`high` передаётся только при ручном выборе в UI
- `response_format` маппится: `{ text: 'text', json: 'json_object' }` для валидных значений API
- При ошибке 400 API из-за неподдерживаемого параметра (`reasoning_effort`, `response_format`) — автоматическое удаление и повтор запроса
- Удалённые параметры отображаются в `applied_params` как `"⚠ Сброшен"`
- `POST /api/agent` — агентский режим: принимает `{ "message": "...", "history": [...] }`, возвращает ответ агента с шагами и результатами

### Агент: контракт `/api/agent`
- `AgentRequest`: `message` (str), `history` (list ролей user/assistant из `agentHistory`)
- `AgentResponse`:
  ```json
  {
    "type": "answer" | "clarification",
    "content": "...",
    "steps": [
      {
        "type": "tool_call" | "tool_result" | "answer",
        "content": "...",
        "tool_name": "...",
        "tool_args": { ... },
        "tool_result": { ... },
        "raw_request": { ... },
        "raw_response": { ... },
        "usage": { ... }
      }
    ],
    "results": [ ... ] | null,
    "raw_request": { ... },
    "raw_response": { ... },
    "usage": { ... }
  }
  ```
- `steps` формируются парами `tool_call` (сырой ответ модели с JSON-вызовом) → `tool_result`; в конце присутствует шаг `answer` (зеркалит финальный `content`). Для `compare_responses` также заполняется `results` (массив ответов субагентов)
- `raw_request`/`raw_response`/`usage` верхнего уровня — параметры **последнего** вызова LLM хода (тот, что привёл к финальному ответу). Под сообщением клиента фронт показывает **первый** запрос хода (см. `renderClientRequest`)
- Агент работает через JSON-текст (без нативных `tool_calls`): модель в ответе пишет `{"tool": "...", "params": {...}}`, сервер исполняет тул и возвращает результат в диалог
- Цикл `agent_loop`: максимум `MAX_AGENT_STEPS = 3` итераций; при `ask_user` сразу возвращается `clarification`
- Tools: `compare_responses` (параллельные вызовы N субагентов через `asyncio.to_thread` + `asyncio.gather`), `get_model_info`, `ask_user`; диспетчер — `execute_tool`
- `_extract_json` устойчив: умеет вытаскивать JSON-объект из текста с преамбулой/хвостом, из JSON-массива (`["...", {"tool": ...}]`) и из markdown-обрамления `` ```json ... ``` ``
- `agent_loop` собирает историю через `pending`-механику: порядок ролей всегда корректный `system → user(клиент) → assistant(JSON тула) → user(«Результат инструмента…»)`, без дублирования первого сообщения

## Важные нюансы
- `providers.json` загружается из директории скрипта при старте
- `active_provider` / `active_model` определяют текущую конфигурацию
- `POST /api/switch-model` пересоздаёт OpenAI-клиент и обновляет `providers.json`
- Импорт типов из `openai.types.chat.ChatCompletionMessageParam` — нужен для type hints в параметрах `messages`
- Чекбоксы включают/выключают связанные control'ы (disabled-логика)
- Под ответами ИИ выводится количество токенов (`.token-count`, `completion` only)
- В правой колонке под ответом выводятся `.param-badge` бейджи (finish_reason, applied_params)
- Аккордеон `JSON-запрос` под сообщением клиента показывает **первый** запрос хода (`system + [история] + user`) — без внутренних `assistant(JSON тула)` и `user(«Результат инструмента…»)`; ширина аккордеона подгоняется под ширину пузыря (`fitJsonWidthToBubble`)
- Под финальной репликой «Агент · Шаг N» выводятся аккордеоны `JSON-запрос` (последний запрос хода, где виден вызов тула как `assistant`) и `JSON-ответ`
- Аккордеоны умещаются в свою колонку даже при длинном JSON: `overflow-wrap: anywhere`, `min-width: 0`

## Frontend JS — ключевые функции
- `loadConfig()` — загрузка конфига с `GET /api/supported-values`, обновление UI (select, sliders)
- `updateReasoningSelect(values)` — заполнение select для reasoning_effort (скрывает строку если список пуст; если поддерживается `none` — авто-включает чекбокс со значением `none`)
- `updateSlider(id, valueDisplayId, config)` — установка min/max/step/value для range-слайдеров
- `addTurn(...)` — рендер строки диалога
- `addSystemPromptTurn(promptText, rawRequest)` — рендер системного промпта
- `sendMessage()` — отправка сообщения, вызов `POST /api/chat`
- `collectConstraints()` — сбор данных с панели настроек (включая reasoning_effort)
- `escapeHtml(s)` — XSS-защита
- `renderBadges(finishReason, appliedParams, usage)` — рендер бейджей параметров и счётчика токенов (внутри `.params-row`)
- `renderRawJson(label, data)` — рендер JSON-аккордеона (summary = Pico outline-secondary кнопка)
- `fitJsonWidthToBubble(userRow)` — подгон ширины аккордеона под сообщение клиента
- `freeChatEnabled` — флаг свободного чата (по умолчанию `false`)
- Логика чекбоксов: `querySelectorAll('.setting-row[data-param]')` + обработчик `change`
- `sendAgentTask()` — отправка задачи агенту, вызов `POST /api/agent`
- `renderAgentResponse(userText, data)` — рендер ответа агента как диалога (реплики «Агент · Шаг N»)
- `renderClientRequest(data)` — первый запрос хода для аккордеона под клиентом
- `agentStepText(step)` — человекочитаемый текст реплики по типу/тулу шага
- `renderCompareGraph(toolArgs, toolResult)` — «граф» сравнения: dispatch (агент → N субагентов) и ответы субагентов (колонки, чипы параметров, JSON каждого субагента)
- `renderConstraintChips(constraints)` — параметры варианта как `.param-badge`-чипы
- `renderAgentMessageRow(stepNum, bubbleText, innerHtml)` — реплика шага агента
- `renderAgentAnswerRow(data, stepNum)` — финальная реплика агента (JSON-запрос последнего вызова + JSON-ответ)
- `buildToolCallExtras(step)` / `toolResultPre(step)` — аккордеоны/токены шага и `pre` результата
- `appendAgentErrorRow(message)` — строка ошибки рендера (без дублирования сообщения клиента)

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
- `.msg-label` — лейбл автора сообщения; `.chat-row.row-ai > .msg-label` и `.ai-response-col .msg-label` — отступ слева 12px (единая линия контента)
- `.message`, `.bubble` — сообщения
- `.ai-responses` — flex-контейнер для двух ответов ИИ
- `.ai-response-col` — колонка с одним ответом ИИ внутри `.ai-responses`
- `.ai-responses--single` — один ответ на всю ширину
- `.ai-responses--graph` — ряды «графа» сравнения (колонки не растягиваются на высоту соседа); внутри `.params-block` не растягивается по вертикали и имеет отступ 12px
- `.params-block`, `.param-badge`, `.param-badge--reason` — бейджи параметров
- `.params-row` — flex-контейнер для бейджей и счётчика токенов под ответом
- `.token-count` — счётчик токенов (внутри `.params-row`, справа от бейджей)
- `.free-chat-toggle` — чекбокс свободного чата
- `.raw-json-toggle` — accordion для JSON (summary = Pico outline-secondary кнопка); `pre` с `overflow-wrap: anywhere`
- `.tool-result` — результат выполнения инструмента (серый фон, скролл, не шире колонки)
- Legacy-классы шагов (`.agent-steps-toggle`, `.agent-steps`, `.agent-step*`, `.agent-step-row`) остались в CSS, но в рендере шагов агента больше не используются (шаги — реплики-сообщения)

## Roadmap: Агентский режим

### Фаза 1: Рефакторинг
- [x] Шаг 1. Извлечь `call_llm()` как ядро в `app.py`
- [x] Шаг 2. Извлечь общие функции рендера в `app.js` (`renderBadges`, `renderRawJson`)
- [x] Шаг 2.5. Исправить позицию счётчика токенов (перенести внутрь `.params-row`)

### Фаза 2: Бэкенд агента
- [x] Шаг 3. Создать `agent.py` — схемы + промпт
- [x] Шаг 4. Добавить tools в `agent.py`
- [x] Шаг 5. Добавить agent loop в `agent.py`
- [x] Шаг 6. Добавить эндпоинт `POST /api/agent` в `app.py`

### Фаза 3: Фронтенд агента
- [x] Шаг 7. Добавить HTML для агента в `index.html`
- [x] Шаг 8. Создать `agent.js` — базовая логика + рендер результатов
- [x] Шаг 9. Добавить рендер результатов агента в `agent.js`
- [x] Шаг 10. Добавить стили для агента в `style.css`

### Полировка агента (дополнительно)
- [x] Граф `compare_responses`: dispatch (агент → N субагентов) + ответы субагентов с JSON-запросами/ответами каждого
- [x] Шаги рендерятся как диалог — реплики «Агент · Шаг N» с человекочитаемым текстом (без сырого JSON в бабле)
- [x] Корректный порядок ролей в запросах агента (`pending`-механика, без дублей первого сообщения)
- [x] Устойчивый `_extract_json` (преамбула, JSON-массив, markdown-обёртка)
- [x] `reasoning_effort: "none"` по умолчанию в `call_llm` (фикс пустых ответов субагентов)
- [x] Аккордеоны: под клиентом — первый запрос хода, ширина = ширине пузыря; под финальной репликой — запрос последнего вызова + ответ; контент не выходит за колонку
- [x] Единая левая линия контента (12px) для лейблов, текста и бейджей

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
