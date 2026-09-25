# Project Tasks

## To Do
- [ ] #016 Add server-side chat history storage
  - Choose JSONL or SQLite and define the conversation format.
  - Implement saving and loading history through the API.
  - Connect history loading and synchronization to the UI.
  - Add tests for saving, loading, and error handling.

## In Progress
- [ ] #015 Remove parallel free/controlled chat flows
  - Keep a single `call_controlled()` invocation and one API response.
  - Remove `include_free`, free history, the free response, and `call_free()`.
  - Unify frontend history and update the UI to display one response.
  - Preserve the separate system-prompt action.
  - Update tests and documentation for the new contract.

## Completed
- [x] #026 Remove emojis from TASKS.md
- [x] #025 Translate TASKS.md to English
- [x] #024 Update and clean up the task list
- [x] #007 Add automated tests
- [x] #006 Load reasoning capabilities from `models.json`
- [x] #005 Move backend logic from `app.py` to `routers/` and `services/`

## Blockers and Questions
- None.
