# GCCD Framework — Goal, Context, Constraints, Done When

> Source: OpenAI Codex Best Practices
> https://developers.openai.com/codex/learn/best-practices

## Core concept

GCCD is a prompt template from OpenAI Codex — four mandatory sections:

| Component | What it is |
|-----------|------------|
| **Goal** | What are you trying to change or build? |
| **Context** | Which files, folders, docs, examples, or errors matter for this task? You can @mention files |
| **Constraints** | What standards, architecture, safety requirements, or conventions should the agent follow? |
| **Done when** | What should be true before the task is complete? (tests passing, behavior changed, bug gone) |

## Verbatum from OpenAI docs

> A good default is to include four things in your prompt:
>
> **Goal**: What are you trying to change or build?
> **Context**: Which files, folders, docs, examples, or errors matter for this task? You can @ mention certain files as context.
> **Constraints**: What standards, architecture, safety requirements, or conventions should Codex follow?
> **Done when**: What should be true before the task is complete, such as tests passing, behavior changing, or a bug no longer reproducing?
>
> This helps Codex stay scoped, make fewer assumptions, and produce work that's easier to review.

## When to trim

GCCD is a starting point, not dogma:

- **Short familiar tasks** — Goal + Done when is enough
- **Complex multi-step** — all 4 sections + examples
- **Researcher** — Goal + Context only (researcher has its own pipeline in SOUL.md)
- **Debugger** — all 4, especially Context (logs, traces) and Done when (what counts as fixed)
- **Coder** — all 4 mandatory
- **Architect** — Goal + Constraints most important, Context optional
- **Reviewer** — Goal (what to review) + Constraints (what to check) + Done when (pass criteria)

## Practical examples per profile

### Coder task
```
**Goal:** Добавить эндпоинт GET /api/health
**Context:** src/main.py (строки 45-120), схема ответа в docs/api.md
**Constraints:** FastAPI, без новых зависимостей, code-style как в проекте (black, isort)
**Done when:** curl localhost:8000/api/health → 200 {"status":"ok"}; pytest tests/test_health.py -v → PASS
```

### Debugger task
```
**Goal:** Найти причину таймаутов при параллельных запросах к /api/search
**Context:** Логи: /var/log/app/error.log (строки 200-350), код src/api/search.py, настройки connection pool в src/db/pool.py
**Constraints:** Не менять API-контракт, не добавлять новые зависимости
**Done when:** Воспроизведён сценарий с 10 concurrent запросами — все отвечают <500ms; в логах нет timeout-ошибок
```

### Architect task
```
**Goal:** Спроектировать модуль аутентификации для микросервиса
**Context:** Существующая схема БД в docs/db-schema.md, API-спецификация в docs/api-spec.yaml
**Constraints:** JWT-токены, refresh token rotation, rate limiting на /auth/*, без внешних SSO-провайдеров
**Done when:** spec содержит: endpoints, DB-schema, middleware flow, error handling, sequence diagram
```

### Reviewer task
```
**Goal:** Проверить PR #42 — модуль авторизации
**Context:** PR diff, spec docs/auth-spec.md (паренты T_spec)
**Constraints:** Безопасность (SQL injection, CSRF, XSS), code-style (black, isort), покрытие тестами >80%
**Done when:** Все acceptance criteria из spec выполнены; найденные issues прокомментированы с severity
```

### Researcher task (Goal + Context only)
```
**Goal:** Сравнить цены перелётов Москва → Нукус на август 2026
**Context:** Нужны точные цены на прямые рейсы + с 1 пересадкой, авиакомпании, даты вылета
```
