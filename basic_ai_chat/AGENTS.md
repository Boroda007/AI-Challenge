# AGENTS.md — Basic AI chat

## Running
```
cd basic_ai_chat && source venv/bin/activate && python app.py
```
Server: http://127.0.0.1:8000

## Tech Stack

### Backend
- **FastAPI** (`app.py`) – Python web framework for async LLM requests
- **OpenAI SDK** – sending requests to OpenAI-compatible API endpoint

### Frontend  
- **Vanilla JavaScript** – client logic in a separate file `app.js`
- **HTML5 templates** – interface markup

### Styling
- **Pico CSS v2 (grey theme)** – base styles with classless approach
- **Custom styles** (`style.css`) – delegated from Pico (custom CSS)

## 🔄 Mandatory Workflow

Before writing a single line of code or answering a user request, you MUST follow these steps:

1. **Context analysis:** Read the current state of `TASKS.md`.
2. **Task selection:** 
    - Find the highest-priority task in the `## ⏳ To Do` section.
    - If there is no such task or the context has changed, agree with the user on creating a new task.
3. **Start work:** Update `TASKS.md` — move the selected task to the `## 🎯 In Progress` section.
4. **Implementation:** Write the code, run tests, fix errors. Your actions must strictly match the current task.
5. **Record the result:** As soon as the task is solved and verified, move it to the `## ✅ Done` section. 
6. **Report:** Only after updating `TASKS.md`, inform the user that the stage is complete.


## 📝 Rules for Maintaining TASKS.md

- **No freelancing:** It is forbidden to perform tasks that are not in `TASKS.md` or not moved to `In Progress`.
- **Task format:** Each task must have a brief description and a unique ID (e.g., `#005`).
- **Recording issues:** If a blocker occurs during work (an error, missing data), stop immediately, record the problem in the `## ⚠️ Blockers and Questions` section, and contact the user.
- **Atomicity:** If a task turns out to be too large, split it into subtasks in the `To Do` list right away.


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
