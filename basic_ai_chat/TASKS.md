# Project Tasks

## To Do

## Completed
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
