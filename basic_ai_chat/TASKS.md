# Список задач проекта

## 📦 Packaged
- [ ] #005 Refactoring: move endpoints from app.py to routers/ (steps #005.4–#005.8)

## 🔬 Lab Work
- [ ] #005.5 Step 5 — create services/llm.py (call_free, call_controlled, render_markdown)
- [ ] #005.6 Step 6 — create routers/chat.py (POST /api/chat)
- [ ] #005.7 Step 7 — create routers/pages.py (GET /)
- [ ] #005.8 Step 8 — final check of all endpoints
- [ ] #005.8 Step 8 — final check of all endpoints

## ✅ Выполнено (Done)
- [x] #005.1 Шаг 1 — создать state.py (глобалы + load/save/resolve)
- [x] Доработка: state.py не соответствует app.py (путь config/providers.json не существует, другие сигнатуры) — исправлено в #005.2.1
- [x] #005.2 Шаг 2 — обновить app.py (импорты из state, удалить дубли)
- [x] #005.2.1 Переписать state.py: точный порт логики app.py:15–87 (current_dir = Path, путь providers.json, сигнатуры без backend_url, удалить _get_model_id)
- [x] #005.2.2 app.py: import state; удалить строки 15–87; заменить использования на state.*; убрать global в switch-model
- [x] #005.2.3 Мини-фикс routers/providers.py: from state import вместо from app import (иначе сломается /api/providers)
- [x] #005.2.4 Проверка: import app OK + curl /, /api/providers, /api/supported-values — всё работает
- [x] #005.3 Шаг 3 — обновить routers/providers.py (прямой import state, перенести /api/supported-values)
- [x] #005.4 Step 4 — create routers/models.py (POST /api/switch-model)
- [x] #006 reasoning_effort из models.json вместо providers.json

## ⚠️ Блокеры и вопросы (Blockers)
- 🚫 ЗАПРЕЩЕНО устанавливать pip-пакеты в систему (в т.ч. --break-system-packages). Если зависимости не установлены — сообщить пользователю и остановиться.
- 🚫 ЗАПРЕЩЕНО использовать глобальный python. Запуск и проверки только через `source venv/bin/activate`.
- ⚠️ Ранее ошибочно установлены глобальные pip-пакеты в `~/.local/lib/python3.12/site-packages` (до запрета). Удалить их или оставить?
