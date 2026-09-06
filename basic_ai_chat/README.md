# Программа: Basic AI chat

Минималистичный ИИ-чат с веб-интерфейсом.

## Возможности

- **Два ответа на одно сообщение**: параллельные вызовы LLM — свободный (без ограничений) и контролируемый (с системным промптом и параметрами генерации)
- **Гибкое отображение**: оба ответа рядом или один контролируемый на всю ширину
- **Системный промпт**: задаётся в нижней панели и применяется к контролируемому ответу
- **Панель параметров**: Формат, Длина (токены), Стоп-символ, Температура, Reasoning — для контролируемого ответа
- **Чекбокс «Свободный чат»**: включает/выключает свободный (неограниченный) ответ
- **Бейджи у ответов**: применённые ограничения и причина остановки генерации
- **Счётчик токенов**: под каждым ответом ИИ
- **Сырые данные**: раскрывающийся JSON-блок с запросом и ответом OpenAI API под каждым сообщением

## Структура проекта
```text
basic_ai_chat/
├── AGENTS.md            # Инструкции для AI-агентов
├── app.py               # Бэкенд-сервер на FastAPI и точка входа Python
├── providers.json       # Конфигурация провайдеров/моделей (скрыт от Git)
├── requirements.txt     # Список зависимостей
├── README.md            # Документация
└── templates/
    ├── index.html       # Разметка страницы
    ├── pico.grey.min.css # Pico CSS v2 (grey theme)
    ├── style.css        # Кастомные стили
    └── app.js           # Логика клиента
```

> `.gitignore` находится в корне репозитория и исключает `providers.json` из Git.

## Зависимости
Основные пакеты, зафиксированные в `requirements.txt`:
- `fastapi` — веб-фреймворк.
- `uvicorn` — ASGI-сервер для запуска приложения.
- `openai` — SDK для отправки запросов к OpenAI-совместимым API.
- `python-multipart` — обработка данных из HTML-форм чата.
- `markdown` — преобразование текста с разметкой Markdown в формат HTML.

## Конфигурация (providers.json)

Все настройки хранятся в едином файле **`providers.json`** в папке `basic_ai_chat` (добавлен в `.gitignore`, так как содержит API-ключи).

### Пример `providers.json`
```json
{
  "active_provider": "ollama",
  "active_model": "qwen2.5:3b",
  "providers": {
    "ollama": {
      "name": "Ollama",
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

Ключи верхнего уровня `active_provider` и `active_model` определяют текущую модель. Их можно менять через API (`POST /api/switch-model`) — сервер пересоздаст OpenAI-клиент и обновит файл.

## Как развернуть и запустить

### 1. Подготовка окружения (в папке `basic_ai_chat`)
```bash
# Создание виртуального окружения
python3 -m venv venv

# Активация виртуального окружения
source venv/bin/activate  # Для Linux / macOS
# venv\Scripts\activate  # Для Windows

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Настройка `providers.json`

Создайте файл `providers.json` в папке `basic_ai_chat` по образцу из раздела «Конфигурация» выше: укажите своего провайдера, модели, `base_url` и при необходимости `api_key`. Затем задайте активные `active_provider` / `active_model`.

### 3. Запуск приложения
```bash
python app.py
```

После запуска откройте в браузере адрес: **`http://127.0.0.1:8000`**.

## API

### `GET /`
Отдаёт HTML-страницу чата.

### `GET /api/providers`
Возвращает список всех провайдеров и моделей из `providers.json` + активный выбор:
```json
{
  "providers": {
    "ollama": {
      "name": "Ollama",
      "base_url": "http://localhost:11434/v1",
      "models": [{ "id": "qwen2.5:3b", "name": "Qwen 2.5 3B" }]
    }
  },
  "active_provider": "ollama",
  "active_model": "qwen2.5:3b"
}
```

### `GET /api/supported-values`
Возвращает capabilities активной модели (reasoning_effort, temperature, max_tokens) для настройки UI:
```json
{
  "reasoning_effort": [],
  "temperature": { "min": 0, "max": 2, "step": 0.1, "default": 0.7 },
  "max_tokens": { "min": 5, "max": 4096, "default": 150 }
}
```

### `POST /api/switch-model`
Смена провайдера/модели без перезапуска. Принимает `{ "provider": "...", "model": "..." }`, пересоздаёт OpenAI-клиент и обновляет `providers.json`. В ответе — новые supported_values.

### `POST /api/system-prompt`
Принимает `{ "prompt": "..." }`, сохраняет системный промпт на сервере, возвращает OpenAI API объект:
```json
{
  "model": "model-name",
  "messages": [{ "role": "system", "content": "..." }]
}
```

### `POST /api/chat`
Принимает JSON и возвращает ответы от двух параллельных вызовов LLM.

**Запрос:**
```json
{
  "message": "Привет!",
  "free_history": [...],
  "controlled_history": [...],
  "constraints": {
    "max_tokens": 50,
    "temperature": 0.7
  }
}
```

**Ответ:**
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
    "applied_params": { "Длина": 50, "Температура": 0.7, ... },
    "usage": { "prompt": N, "completion": N, "total": N }
  }
}
```

**Поля `constraints`:**
| Поле | Описание |
|------|----------|
| `max_tokens` | Максимальная длина ответа в токенах |
| `temperature` | Температура генерации (0–2) |
| `stop` | Стоп-символ |
| `response_format` | `{ "type": "text" }` или `{ "type": "json_object" }` |
| `reasoning_effort` | Уровень рассуждений (`"none"`, `"low"`, `"medium"`, `"high"`) — если поддерживается моделью; по умолчанию `"none"` |

> **Примечания:**
> - Системный промпт устанавливается отдельно через `POST /api/system-prompt` и не входит в `constraints`.
> - `reasoning_effort` попадает в API из `constraints`. Для моделей, поддерживающих `"none"`, в UI галка Reasoning включена по умолчанию со значением `none` (рассуждения выключены, экономия токенов); значения `low`/`medium`/`high` задаются вручную.
> - Если API возвращает 400 из-за неподдерживаемого параметра (`reasoning_effort`, `response_format`), сервер автоматически удаляет его и повторяет запрос.
