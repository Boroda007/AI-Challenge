# Реестр моделей (Models Registry)

Документация по использованию реестра для управления специфическими параметрами моделей (reasoning, thinking, effort и другие провайдер-зависимые настройки).

---

## 📖 Содержание

1. [Зачем это нужно](#зачем-это-нужно)
2. [Структура проекта](#структура-проекта)
3. [Формат `models.json`](#формат-modelsjson)
4. [Поля реестра](#поля-реестра)
5. [Как использовать в коде](#как-использовать-в-коде)
6. [Добавление новой модели](#добавление-новой-модели)
7. [Правила валидации](#правила-валидации)
8. [Примеры для разных провайдеров](#примеры-для-разных-провайдеров)
9. [FAQ](#faq)

---

## Зачем это нужно

Разные провайдеры (OpenAI, Qwen, DeepSeek, Anthropic, Mistral) используют **разные параметры** для включения рассуждений и управления их глубиной:

| Провайдер | Как включает thinking | Как задаёт глубину |
|-----------|----------------------|-------------------|
| Qwen | `extra_body.enable_thinking` | `extra_body.reasoning_effort` |
| DeepSeek | `extra_body.thinking.type` | `reasoning_effort` (top-level) |
| OpenAI GPT-5.x | не нужен (toggle через effort) | `reasoning_effort` (top-level) |
| Anthropic (Bedrock) | `output_config.thinking.type` | `output_config.effort` |
| Mistral | `extra_body.reasoning_effort` | — |

Реестр решает эту проблему: **знание о моделях хранится в одном JSON-файле**, а код чата остаётся чистым.

---

## Структура проекта

```
myapp/
├── models.json              # Реестр моделей (данные)
├── registry.py              # Логика резолва и сборки kwargs
├── reasoning.py             # Хелпер для вклинивания в существующий код
├── chat.py                  # Ваш код чата
└── tests/
    └── test_registry.py     # Тесты реестра
```

**Принцип разделения:**

- `models.json` — **данные**. Обновляется без правки кода.
- `registry.py` — **логика**. Читает JSON и собирает kwargs.
- `reasoning.py` — **интеграция**. Позволяет вклинить реестр в существующие вызовы.

---

## Формат `models.json`

Реестр — это JSON-файл с тремя корневыми полями.

```json
{
  "version": "1.0",
  "updated_at": "2026-09-22",
  "models": {
    "<имя-модели-или-glob-паттерн>": { ...описание... }
  }
}
```

### Корневые поля

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `version` | string | да | Версия формата реестра (SemVer). |
| `updated_at` | string (ISO date) | да | Дата последнего обновления. |
| `models` | object | да | Словарь моделей. Ключ — имя или glob-паттерн. |

### Ключи в `models`

Ключом может быть:

- **Точное имя модели**: `"qwen3.8-max"`, `"gpt-5.1"`, `"deepseek-flash"`.
- **Glob-паттерн**: `"claude-opus-4-*"`, `"gpt-5.*"`.

При резолве сначала проверяется **точное совпадение**, потом — **glob**. Это позволяет задавать общие правила для целого семейства моделей.

---

## Поля реестра

### Описание модели

```json
{
  "provider": "qwen",
  "transport": "native",
  "reasoning": { ... },
  "verified_at": "2026-09-22",
  "source": "https://..."
}
```

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `provider` | string | да | Провайдер: `openai`, `qwen`, `deepseek`, `anthropic`, `mistral`, `google`. |
| `transport` | string | нет | Транспорт: `native` (по умолчанию), `bedrock`, `vertex`, `openrouter`. |
| `reasoning` | object | нет | Настройки рассуждений. Если нет — модель не поддерживает reasoning. |
| `verified_at` | string (ISO date) | да | Когда проверяли актуальность записи. |
| `source` | string (URL) | да | Ссылка на документацию провайдера. |

### Секция `reasoning`

```json
{
  "mode": "toggle",
  "enable": { ... },
  "effort": { ... }
}
```

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `mode` | string | да | `toggle`, `always_on`, `unsupported`. |
| `enable` | object | для `toggle` | Как включать/выключать reasoning. |
| `effort` | object | нет | Уровень усилия рассуждений. |

### Режимы (`mode`)

| Значение | Смысл | Флаг включения |
|----------|-------|----------------|
| `toggle` | Можно включить/выключить явно | Нужен |
| `always_on` | Модель всегда думает | Не нужен |
| `unsupported` | Модель не умеет reasoning | Не нужен |

### Секция `enable`

Описывает, **как передать флаг включения**.

```json
{
  "location": "extra_body",
  "key": "enable_thinking",
  "on": true,
  "off": false
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `location` | string | Куда положить: `top_level`, `extra_body`, `output_config`, `none`. |
| `key` | string | Имя ключа. Вложенность через точку: `thinking.type`. |
| `on` | any | Значение при `enable=True`. |
| `off` | any | Значение при `enable=False`. |

**Значение `location`:**

- `top_level` — параметр идёт как обычный kwarg в `create()`.
- `extra_body` — кладётся внутрь `extra_body`.
- `output_config` — кладётся внутрь `output_config` (Anthropic Bedrock).
- `none` — флаг не нужен (используется для `always_on`).

### Секция `effort`

Описывает, **как передать уровень усилия**.

```json
{
  "param": "reasoning_effort",
  "location": "top_level",
  "levels": ["low", "medium", "high"],
  "default": "medium"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `param` | string | Имя параметра: `reasoning_effort`, `effort`. |
| `location` | string | Куда положить: `top_level`, `extra_body`, `output_config`. |
| `levels` | array | Допустимые значения в порядке возрастания силы. |
| `default` | string | Что использовать, если пользователь не указал. |

---

## Как использовать в коде

### Базовое использование

```python
from registry import ModelRegistry

registry = ModelRegistry("models.json")

profile = registry.resolve("qwen3.8-max")
kwargs = profile.build_reasoning_kwargs(enable=True, effort="high")
# → {"extra_body": {"enable_thinking": True, "reasoning_effort": "high"}}

response = client.chat.completions.create(
    model="qwen3.8-max",
    messages=messages,
    **kwargs,
)
```

### Встраивание в существующий код

Если у вас уже есть вызовы `create()` и не хочется их переписывать — используйте хелпер.

```python
from reasoning import reasoning_kwargs

response = client.chat.completions.create(
    model=model,
    messages=messages,
    temperature=0.7,
    **reasoning_kwargs(model, enable=True, effort="high"),
)
```

### Параметры `build_reasoning_kwargs`

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `enable` | bool \| None | `None` | `True` — включить, `False` — выключить, `None` — не трогать. |
| `effort` | str \| None | `None` | Уровень усилия. Если `None` — берётся `default`. |

### Возвращаемое значение

Функция возвращает **dict**, готовый к распаковке в `create()` через `**`. Если модель не найдена или не поддерживает reasoning — возвращается **пустой dict** `{}`.

---

## Добавление новой модели

### Шаг 1. Изучите документацию

Найдите в документации провайдера, **как именно** передаются параметры reasoning. Обратите внимание на:

- Имя параметра включения (если есть).
- Где он находится: top-level или внутри `extra_body` / `output_config`.
- Допустимые уровни усилия.
- Значение по умолчанию.

### Шаг 2. Добавьте запись в `models.json`

Пример для новой модели:

```json
{
  "my-new-model-v1": {
    "provider": "myvendor",
    "reasoning": {
      "mode": "toggle",
      "enable": {
        "location": "extra_body",
        "key": "enable_reasoning",
        "on": true,
        "off": false
      },
      "effort": {
        "param": "reasoning_effort",
        "location": "extra_body",
        "levels": ["low", "medium", "high"],
        "default": "medium"
      }
    },
    "verified_at": "2026-09-22",
    "source": "https://docs.myvendor.example/reasoning"
  }
}
```

### Шаг 3. Обновите `updated_at`

Не забудьте поменять дату в корне файла.

### Шаг 4. Добавьте тест

```python
def test_my_new_model():
    p = registry.resolve("my-new-model-v1")
    kw = p.build_reasoning_kwargs(enable=True, effort="high")
    assert kw == {
        "extra_body": {
            "enable_reasoning": True,
            "reasoning_effort": "high",
        }
    }
```

### Шаг 5. Проверьте вручную

Запустите реальный запрос к API и убедитесь, что параметры принимаются без ошибок.

---

## Правила валидации

### Что делает реестр

1. **Резолв модели** — точное совпадение → glob → fallback (пустой профиль).
2. **Проверка `mode`** — если `unsupported`, возвращается `{}`.
3. **Валидация `effort`** — если запрошенное значение не входит в `levels`, применяется **clamp** к ближайшему поддерживаемому.
4. **Учёт `enable=False`** — если reasoning явно выключен, `effort` не передаётся.

### Что НЕ делает реестр

- **Не проверяет API** — реестр не дёргает реальные запросы.
- **Не знает про стандартные параметры** — `temperature`, `max_tokens`, `tools` идут напрямую, минуя реестр.
- **Не валидирует JSON-схему на старте** — предполагается, что данные корректны (можно добавить Pydantic позже).

### Стратегия clamp

Если пользователь указал `effort="xhigh"`, а модель поддерживает только `low`/`medium`/`high`, то:

- Порядок уровней: `none < low < medium < high < xhigh < max`.
- Если запрошенное **больше максимума** — берётся максимальный поддерживаемый.
- Если запрошенное **меньше минимума** — берётся минимальный поддерживаемый.
- Если запрошенное **неизвестно** — берётся `default`.

### Fallback для неизвестных моделей

Если модель не найдена в реестре:

- `build_reasoning_kwargs()` возвращает `{}`.
- Никаких исключений не бросается.
- Запрос уходит «как есть», провайдер сам решает, что делать.

Это важно: реестр **не должен ломать** работу с новыми моделями, которых он ещё не знает.

---

## Примеры для разных провайдеров

### Qwen (toggle + effort в extra_body)

```json
{
  "qwen3.8-max": {
    "provider": "qwen",
    "reasoning": {
      "mode": "toggle",
      "enable": {
        "location": "extra_body",
        "key": "enable_thinking",
        "on": true,
        "off": false
      },
      "effort": {
        "param": "reasoning_effort",
        "location": "extra_body",
        "levels": ["low", "medium", "high"],
        "default": "medium"
      }
    },
    "verified_at": "2026-09-22",
    "source": "https://docs.qwen.example/reasoning"
  }
}
```

**Результат:**

| Вызов | kwargs |
|-------|--------|
| `enable=True, effort="high"` | `{"extra_body": {"enable_thinking": True, "reasoning_effort": "high"}}` |
| `enable=False` | `{"extra_body": {"enable_thinking": False}}` |
| `enable=None` | `{"extra_body": {"reasoning_effort": "medium"}}` |

### DeepSeek (always_on + effort на top-level)

```json
{
  "deepseek-flash": {
    "provider": "deepseek",
    "reasoning": {
      "mode": "always_on",
      "enable": {
        "location": "extra_body",
        "key": "thinking.type",
        "on": "enabled",
        "off": "disabled"
      },
      "effort": {
        "param": "reasoning_effort",
        "location": "top_level",
        "levels": ["low", "high", "max"],
        "default": "high"
      }
    },
    "verified_at": "2026-09-22",
    "source": "https://api-docs.deepseek.example/reasoning"
  }
}
```

**Результат:**

| Вызов | kwargs |
|-------|--------|
| `enable=True, effort="max"` | `{"reasoning_effort": "max"}` |
| `enable=None, effort="low"` | `{"reasoning_effort": "low"}` |

### OpenAI GPT-5.1 (toggle через effort, без флага)

```json
{
  "gpt-5.1": {
    "provider": "openai",
    "reasoning": {
      "mode": "toggle",
      "enable": {
        "location": "none"
      },
      "effort": {
        "param": "reasoning_effort",
        "location": "top_level",
        "levels": ["none", "low", "medium", "high"],
        "default": "medium"
      }
    },
    "verified_at": "2026-09-22",
    "source": "https://platform.openai.com/docs/..."
  }
}
```

**Результат:**

| Вызов | kwargs |
|-------|--------|
| `enable=True, effort="high"` | `{"reasoning_effort": "high"}` |
| `enable=False` | `{}` |

> **Нюанс:** у GPT-5.1 «выключить» reasoning можно через `effort="none"`, но флага включения нет. Реестр это не описывает — если нужно, добавьте отдельную логику.

### Anthropic Claude через Bedrock (output_config)

```json
{
  "claude-opus-4-*": {
    "provider": "anthropic",
    "transport": "bedrock",
    "reasoning": {
      "mode": "toggle",
      "enable": {
        "location": "output_config",
        "key": "thinking.type",
        "on": "enabled",
        "off": "disabled"
      },
      "effort": {
        "param": "effort",
        "location": "output_config",
        "levels": ["low", "medium", "high", "max"],
        "default": "high"
      }
    },
    "verified_at": "2026-09-22",
    "source": "https://docs.aws.amazon.com/bedrock/..."
  }
}
```

**Результат:**

| Вызов | kwargs |
|-------|--------|
| `enable=True, effort="medium"` | `{"output_config": {"thinking": {"type": "enabled"}, "effort": "medium"}}` |
| `enable=False` | `{"output_config": {"thinking": {"type": "disabled"}}}` |

---

## FAQ

### Что произойдёт, если модель не найдена в реестре?

Вернётся пустой dict `{}`. Запрос уйдёт без reasoning-параметров. Провайдер использует свои значения по умолчанию.

### Можно ли передавать стандартные параметры (temperature, tools) через реестр?

Нет. Реестр — только для **специфических** параметров, которые различаются между провайдерами. Всё стандартное передавайте напрямую в `create()`.

### Что если пользователь укажет неподдерживаемый effort?

Реестр применит **clamp** к ближайшему поддерживаемому. Например, `xhigh` → `high`, если `xhigh` не в списке.

### Как обновлять реестр при выходе новых версий моделей?

1. Проверьте документацию провайдера.
2. Обновите соответствующую запись в `models.json`.
3. Обновите `verified_at` и `updated_at`.
4. Запустите тесты.
5. Проверьте вручную одним реальным запросом.

### Можно ли использовать реестр с моделями, которых нет в нём?

Да. Реестр — **опциональный** слой. Если модель не найдена — всё работает как обычно, без reasoning-параметров.

### Что делать, если у модели несколько транспортов (native + bedrock)?

Заведите **отдельные записи** с разными ключами:

```json
{
  "claude-opus-4-5": { "transport": "native", ... },
  "claude-opus-4-5@bedrock": { "transport": "bedrock", ... }
}
```

Или используйте `transport` как часть ключа резолва.

### Как добавить новую секцию (не reasoning)?

1. Добавьте секцию в JSON, например `"prompt_cache": {...}`.
2. Добавьте метод в `ModelProfile`, например `build_prompt_cache_kwargs()`.
3. Вклините вызов этого метода в свой код.

Реестр расширяется **органично** — старые записи не ломаются.

### Нужно ли валидировать JSON на старте?

Для небольших реестров — необязательно. Для продакшена рекомендуется добавить Pydantic-схему, которая проверит структуру при загрузке.

### Как тестировать реестр?

Минимум — юнит-тесты, которые проверяют, что `build_reasoning_kwargs()` для каждой модели возвращает ожидаемый dict. Это **контрактные тесты**: они ловят опечатки и регрессии.

Дополнительно можно добавить **ночной CI**, который дёргает реальные API и проверяет, что параметры принимаются.

---

## Итог

Реестр — это **тонкий слой данных**, который:

- Хранит знание о специфических параметрах моделей.
- Не ломает работу с неизвестными моделями.
- Легко расширяется.
- Тестируется контрактными тестами.
- Используется через одну функцию `build_reasoning_kwargs()`.

Код чата остаётся чистым: вы просто добавляете `**reasoning_kwargs(...)` в существующие вызовы `create()`.
