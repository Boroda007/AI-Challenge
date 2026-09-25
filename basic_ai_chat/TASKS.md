# Project Tasks

## To Do
- [ ] #016 Add server-side chat history storage
  - Choose JSONL or SQLite and define the conversation format.
  - Implement saving and loading history through the API.
  - Connect history loading and synchronization to the UI.
  - Add tests for saving, loading, and error handling.

## Completed
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
