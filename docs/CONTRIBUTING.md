# Contributing — Basic AI Chat

## Commit Message Conventions

Format:
```
<type>(<scope>): <description in Russian>
```

Types:
- `feat` — new feature
- `fix` — bug fix
- `refactor` — refactoring without behavior change
- `docs` — documentation only
- `style` — CSS, formatting, visual
- `test` — tests
- `chore` — build, dependencies, technical work

Scope (optional, briefly in English):
`chat`, `backend`, `frontend`, `types`, `ui`, `config`.

Examples:
```
feat(config): добавить providers.json с провайдерами и моделями
feat(chat): добавить reasoning_effort в панель параметров
refactor(backend): заменить .env на providers.json
fix(backend): убрать хардкод reasoning_effort в call_controlled
docs: актуализировать AGENTS.md
```

## Rules

- One logical change per commit.
- Description in Russian, imperative mood ("добавить", "убрать", "заменить").
- No mixed commits: do not combine refactor and feat in one commit.
- Run tests before committing: `python -m unittest discover -s tests -v`.

## When to Read This File

- Before making a commit.
- When preparing a commit message.
- When unsure about type or scope.
