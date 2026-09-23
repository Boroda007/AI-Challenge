# Список задач проекта

## 📦 Packaged
- [x] #005 Refactoring: move endpoints from app.py to routers/ (steps #005.4–#005.8)

## 🎯 In Progress

## ✅ Выполнено (Done)
- [x] #005.1 Шаг 1 — создать state.py (глобалы + load/save/resolve)
- [x] Доработка: state.py не соответствует app.py (путь config/providers.json не существует, другие сигнатуры) — исправлено в #005.2.1
- [x] #005.2 Шаг 2 — обновить app.py (импорты из state, удалить дубли)
- [x] #005.2.1 Переписать state.py: точный порт логики app.py:15–87 (current_dir = Path, путь providers.json, сигнатуры без backend_url, удалить _get_model_id)
- [x] #005.2.2 app.py: import state; удалить строки 15–87; заменить использования на state.*; убрать global в switch-model
- [x] #005.2.3 Мини-фикс routers/providers.py: from state import вместо from app import (иначе сломается /api/providers)
- [x] #005.2.4 Проверка: import app OK + curl /, /api/providers, /api/supported-values — всё работает
- [x] #005.3 Шаг 3 — обновить routers/providers.py (прямой import state, перенести /api/supported-values)
- [x] #005.4 Step 4 — перенести `/api/switch-model` в `routers/providers.py`
- [x] #005.5 Step 5 — создать `services/llm.py` (`call_free`, `call_controlled`, `render_markdown`)
- [x] #005.6 Step 6 — create routers/chat.py (POST /api/chat)
- [x] #005.6.1 Устранить дублирование switch-model: удалить routers/models.py
- [x] #005.7 Step 7 — create routers/pages.py (GET /)
- [x] #005.8 Step 8 — final check of all endpoints
- [x] #006 reasoning_effort из models.json вместо providers.json

## ⚠️ Блокеры и вопросы (Blockers)
- 🚫 Нельзя устанавливать пакеты в системное Python-окружение.
- ✅ Все команды Python, установка зависимостей и проверки выполняются только из `basic_ai_chat/venv`.
- Перед запуском выполнить:
  ```bash
  cd basic_ai_chat
  source venv/bin/activate
  ```
- Если зависимость отсутствует в `venv`, не устанавливать её глобально: сообщить пользователю и остановить работу.
