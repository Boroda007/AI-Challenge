# AGENTS.md — Basic AI chat

## Environment
Working dir: project root (where OpenCode runs).
Activate venv: `source venv/bin/activate`

## Running
`python app.py` → http://127.0.0.1:8000

## Tests
`python -m unittest discover -s tests -v`

## Tech Stack
FastAPI + vanilla JS + Pico CSS v2.
Read `docs/ARCHITECTURE.md` when working on UI, adding dependencies, or changing structure.

## Mandatory Workflow

Before coding or answering, follow these steps:

1. Read `TASKS.md`.
2. Pick the highest-priority task from `## To Do`. If none, agree on a new task with the user.
3. Move it to `## In Progress`.
4. Implement, run tests, fix errors. Stay within the current task.
5. Move the task to `## Completed` once verified.
6. Only then report completion to the user.

## Rules for TASKS.md

- **No freelancing:** Do not work on tasks not in `TASKS.md` or not in `In Progress`.
- **Format:** Each task has a short description and unique ID (e.g. `#005`).
- **Blockers:** On error or missing data, stop, log it in `## Blockers and Questions`, and ask the user.
- **Atomicity:** If a task is too large, split it into subtasks in `To Do` immediately.

## Commits
Follow `docs/CONTRIBUTING.md` for commit message conventions.
