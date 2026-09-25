# Project Tasks

## To Do

- None.

## In Progress
- None.

## Completed
- [x] #028 Форматирование ответа в реальном времени
  - [x] `templates/marked.min.js` + подключение в `index.html`
  - [x] `app.js`: `handle.raw`, троттлинг рендера, незакрытый ```, экранирование
  - [x] Тесты (12) + `ruff check .` + проверка в браузере

- [x] #027 Стриминг ответов ИИ через SSE
  - [x] `llm.py`: `stream_controlled()` поверх хелперов из #026
  - [x] `routers/chat.py`: `/api/chat` → `StreamingResponse`, `append_turn` после потока
  - [x] `app.js`: `getReader()`, `appendDelta()`, markdown в конце
  - [x] Тесты (12) + `ruff check .` + проверка в браузере
  - [x] Обновить Request Flow в `docs/ARCHITECTURE.md`

- [x] #026 Выделить переиспользуемые части в `llm.py` и разделить `addTurn` в `app.js`
  - [x] `llm.py`: вынесены `_build_api_params()`, `_create_with_retry()`, `_applied_params()`,
    `_usage_dict()`, константы `PARAM_MAPPING` / `RETRY_PARAMS`; `call_controlled` стал оркестратором.
  - [x] `app.js`: `addTurn` разделён на `createTurn()` (возвращает `{aiCol, aiBubble, paramsRow}`)
    и `finalizeTurn()`; DOM-структура не изменилась.
  - [x] 11 тестов OK, `ruff check .` — All checks passed.
- [x] #025 Разделить корень проекта и путь к конфигу
  - [x] Step 1. DONE. `get_config_path()` удалён, добавлен `get_project_dir()`;
    `_path()` = `self._config_path or self.get_project_dir() / "providers.json"`.
  - [x] Step 2. DONE. app.py монтирует `state.get_project_dir() / "templates"`.
  - [x] Step 3. DONE. routers/pages.py использует `state.get_project_dir()`.
  - [x] Step 4. DONE. Symlink `templates` в setUp тестов удалён.
  - [x] Step 5. DONE. 11 тестов OK, `ruff check .` — All checks passed.
- [x] #024 Убрать оставшуюся дублирующую сущность в `state.py`
  - [x] Step 1. DONE. Убран атрибут `_providers_config`; добавлен приватный
    `_providers()` -> `ProvidersConfig`, читающий `_raw_config["providers"]`.
  - [x] Step 2. DONE. Удалена модульная `get_current_dir()`; путь по умолчанию
    вычисляется в `_path()`; добавлен публичный `get_config_path() -> Path`.
    Обновлены app.py и routers/pages.py; в setUp тестов в tmp-директорию
    добавлена ссылка на `templates`.
  - [x] Step 3. DONE. `_select_model` + `_build_client` схлопнуты в
    `_model_and_client(provider, model) -> tuple[ModelConfig, OpenAI]`.
  - [x] Step 4. DONE. Убран неиспользуемый `step` из `ParameterRange`.
  - [x] Step 5. DONE. 11 тестов проходят, `ruff check .` — All checks passed.
    state.py: 172 → 167 строк.
- [x] #023 Инкапсулировать состояние в класс `State`
  - [x] Step 1. DONE. `class State` с 6 атрибутами в `__init__` (включая `_config_path`),
    приватные методы `_path`/`_load`/`_save`/`_select_model`/`_build_client`/`_resolve`;
    все 4 `global` убраны.
  - [x] Step 2. DONE. Публичные методы перенесены в класс с прежними именами,
    синглтон `state = State()`; `get_current_dir()` осталась функцией модуля.
  - [x] Step 3. DONE. `init(config_path: Path | None = None)` — единственная точка внедрения пути.
  - [x] Step 4. DONE. `setUp` в tests/test_app.py: временный providers.json + `state.init(config_path)`;
    удалены `patch.object(state, "get_current_dir")` и симлинк `templates`.
  - [x] Step 5. DONE. Побочно заменены импорты `import state` → `from state import state`
    в app.py, routers/pages.py, routers/providers.py, services/llm.py, tests/test_app.py.
    11 tests passed, ruff clean. state.py: 182 → 172 строки.
- [x] #022 Make `_active_model_config` Optional (`dict[Any, Any]` incompatible with `ModelConfig`)
  - [x] Step 1. DONE. Global typed as `ModelConfig | None = None`.
  - [x] Step 2. DONE. `None` handled in `_save_providers_config` (`(_active_model_config or {}).get("id", "")`),
    `get_active_model` (`_active_model_config["id"] if _active_model_config else ""`) and
    `get_active_model_config` (RuntimeError "❌ Модель не инициализирована", same style as `get_client`).
  - [x] Step 3. DONE. 11 tests passed, ruff clean.
- [x] #021 Make `name`/`base_url` required in `ProviderConfig` (`provider_cfg["base_url"]` flagged by type checker)
  - [x] Step 1. DONE. Added `ProviderConfigBase` TypedDict with required `name`/`base_url`;
    `ProviderConfig` now inherits it (`total=False` for `api_key`/`models`).
  - [x] Step 2. DONE. Removed the dead `isinstance(provider["models"], dict)` branch in
    `routers/providers.py`; now uses `provider["name"]`/`provider["base_url"]` directly.
  - [x] Step 3. DONE. 11 tests passed, ruff clean.
- [x] #020 Fix required-key typing for ModelConfig (`m["id"]` flagged by type checker)
  - [x] Step 1. DONE. Added `ModelConfigBase` TypedDict with required `id`/`name`,
    `ModelConfig` now inherits it (`total=False` for the optional keys).
  - [x] Step 2. DONE. Added `step: int | float` to `ParameterRange` and `name: str`
    to `ProviderConfig` to match the real providers.json.
  - [x] Step 3. DONE. 11 tests passed, ruff clean.
- [x] #019 Add precise type annotations to the public API of state.py
  - [x] Step 1. DONE. Added `TypedDict` definitions for the config structures
    (`ParameterRange`, `ModelConfig`, `ProviderConfig`) plus the `ProvidersConfig`
    / `RawConfig` aliases, imported from `typing` (no new dependencies).
  - [x] Step 2. DONE. Replaced bare `dict` annotations with the precise types in
    the globals (`_providers_config`, `_active_model_config`, `_raw_config`),
    `_select_model()` and the public getters. Tests: 11 passed, ruff clean.
  - [x] Step 3. DONE. Added docstrings to the undocumented public getters
    (`get_providers_config`, `get_active_provider`, `get_active_model`,
    `get_active_model_config`, `get_client`).
  - [x] Step 4. DONE. `python -m unittest discover -s tests -v` → 11 tests passed;
    `ruff check .` → all checks passed.
- [x] #018 Remove duplicated entities in state.py
  - [x] Step 1. DONE. Drop the `_active_model` global; derive the model name from
    `_active_model_config.get("id", "")` in both `get_active_model()` and
    `_save_providers_config()`. Use a local variable during model lookup.
  - [x] Step 2. DONE. Unified `get_model_name()` with `get_active_model()`; deleted
    `get_model_name()` and `_get_model_name()`. Updated `services/llm.py:24`
    (`state.get_active_model()`) and `tests/test_app.py:169` patch target.
    11 tests pass, ruff clean.
  - [x] Step 3. DONE. Deleted `_get_client()`; `get_client()` now performs the
    `RuntimeError("❌ OpenAI-клиент не инициализирован")` check inline.
    `_get_model_name()` was already removed in Step 2. 11 tests pass, ruff clean.
  - [x] Step 4. DONE. Extracted `_select_model(provider, model) -> dict`
    (provider lookup, base_url check, model-by-id lookup, three ValueErrors
    all with the `❌ ` prefix) and `_build_client(provider) -> OpenAI`.
    `_resolve_active_model()` and `switch_model()` both use them. 133 lines
    (was 148). 11 tests pass, ruff clean.
  - [x] Step 5. DONE. Removed the `current_dir` module global; `get_current_dir()`
    now returns `Path(__file__).resolve().parent` inline. 130 lines.
    11 tests pass, ruff clean.
  - [x] Step 6. DONE. `switch_model()` returns `None`;
    `routers/providers.py` `/api/switch-model` builds its response from
    `state.get_active_provider()` / `get_active_model()` /
    `get_active_model_config()` (temperature/max_tokens from a local
    `model_config`). 124 lines. 11 tests pass, ruff clean.
  - [x] Step 7. DONE. `python -m unittest discover -s tests -v` → 11 passed;
    `ruff check .` clean. Grep for `get_model_name` / `_active_model` /
    `_get_client` / `current_dir` leftovers is clean; README.md and docs/
    do not reference the removed names, so no doc changes were needed.
    state.py: 162 → 124 lines. Public API: `get_current_dir`,
    `get_providers_config`, `get_active_provider`, `get_active_model`,
    `get_active_model_config`, `get_client`, `init`, `switch_model`.
- [x] #017 Encapsulate state.py behind a public API
  - Step 1. Add read-only public getters to state.py
    (`get_current_dir`, `get_providers_config`, `get_active_provider`,
    `get_active_model`, `get_active_model_config`, `get_client`, `get_model_name`).
    Behaviour unchanged; privates stay private. No caller changes yet.
    DONE.
  - Step 2. Update callers to the new getters: routers/pages.py,
    services/llm.py, routers/providers.py, app.py. Remove `from state import current_dir`
    and all `state._*` reads. Add `init()` (load + resolve) and use it in app.py.
    Tests still pass (test setUp keeps working on privates for now).
    DONE.
  - Step 3. Move model-switch logic into `state.switch_model(provider, model)`:
    validation, state mutation, client creation, providers.json save; raises ValueError.
    DONE.
  - Step 4. Slim routers/providers.py `/api/switch-model` down to a call + ValueError -> 400.
    Drop the `openai.OpenAI` import there.
    DONE.
  - Step 5. Rework tests/test_app.py setUp: temp providers.json in a
    TemporaryDirectory + `patch("state.get_current_dir")` + real `state.init()`,
    instead of mutating private variables. Remove the `missing` provider test's
    dependency on private state.
    DONE.
  - Step 6. Remove the old `_`-prefixed functions/aliases left unused in state.py;
    verify no `state._` references remain anywhere (grep).
    DONE — all `_`-prefixed helpers are still used internally; no `state._` references remain.
  - Step 7. Run `python -m unittest discover -s tests -v` and lint; update
    README/docs/ARCHITECTURE.md if they mention the private state API.
    DONE — 11 tests pass, ruff clean, docs needed no changes.
- [x] #016 Add server-side in-memory chat history
  - Add the in-memory history service and unit tests.
  - Use server history in `/api/chat` and append successful turns.
  - Add the system-prompt endpoint and API tests.
  - Remove client-owned history from the chat request and state.
  - Update README and architecture documentation.
  - Run the complete test suite and inspect the final diff.
- [x] #015 Remove parallel free/controlled chat flows
  - Use one controlled invocation, one API response, and one client history.
  - Remove free-mode fields, response, service function, and UI toggle.
  - Preserve the separate system-prompt action.
  - Update tests and documentation for the new contract.
- [x] #026 Remove emojis from TASKS.md
- [x] #025 Translate TASKS.md to English
- [x] #024 Update and clean up the task list
- [x] #007 Add automated tests
- [x] #006 Load reasoning capabilities from `models.json`
- [x] #005 Move backend logic from `app.py` to `routers/` and `services/`

## Blockers and Questions
- None.
