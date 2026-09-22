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
