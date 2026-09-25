# Architecture — Basic AI Chat

## Overview
Web application for chatting with LLM via OpenAI-compatible API.

## Backend
- **FastAPI** — `app.py` registers `routers/chat.py`, `routers/pages.py`, and `routers/providers.py` with `include_router()`.
- **OpenAI SDK** — `services/llm.py` calls the OpenAI-compatible API for chat requests.
- `routers/chat.py` handles chat and system-prompt requests; `pages.py` serves `templates/index.html`; `providers.py` exposes provider and model operations.
- `services/history.py` stores the single in-memory conversation used by the server. The history is cleared when the process restarts.
- `state.py` owns the active client and selected model, reading and updating `providers.json`; `reasoning.py` loads model capabilities from `models.json`.

### Request Flow
1. `templates/app.js` sends `POST /api/chat` with the current message and constraints.
2. `routers/chat.py` reads the server-side history, appends the current user message for the LLM call, and delegates to `services/llm.py`.
3. After a successful response, the router appends the user and raw assistant messages to `services/history.py`.
4. `app.js` renders the response, usage, parameters, and raw data without maintaining a separate conversation history.

## Frontend
- **Vanilla JavaScript** (`templates/app.js`) — unified client logic for the UI, parameters, API requests, system-prompt submission, and response rendering.
- **HTML5** (`templates/index.html`) — static markup for the application interface.

## Styling
- **Pico CSS v2 (grey theme)** (`templates/pico.grey.min.css`) — provides the base interface styles.
- **Custom styles** (`templates/style.css`) — define the application layout and component-specific appearance on top of Pico.

## Structure
- `app.py` — FastAPI entry point.
- `routers/` — `chat.py`, `pages.py`, and `providers.py` API modules.
- `services/llm.py` — OpenAI-compatible LLM integration.
- `services/history.py` — single in-memory conversation history.
- `templates/` — `index.html`, `app.js`, `style.css`, and Pico CSS.
- `state.py` and `reasoning.py` — runtime state and model capability handling.
- `providers.json` and `models.json` — provider/model configuration sources.
- `tests/test_app.py` — unittest suite.
- `docs/` — architecture, model, and contribution guides.

## When to Read This File
- **UI/styling:** `templates/index.html`, `templates/app.js`, `templates/style.css`.
- **Chat/API behavior:** `routers/chat.py`, `services/llm.py`, `templates/app.js`.
- **Provider/model configuration:** `routers/providers.py`, `state.py`, `reasoning.py`, and the JSON configuration files.
- **Project structure or entry points:** `app.py`, `routers/`, and this file.
