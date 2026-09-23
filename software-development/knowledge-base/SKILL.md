---
name: knowledge-base
description: Design and maintain a project knowledge base (md + README-index + git + search) that both humans and AI agents can navigate. Covers structural patterns, ontology design, FTS5 indexing, curation rules, and Claude/Hermes integration.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [documentation, knowledge-base, search, ontology, markdown]
    related_skills: [kanban-worker, writing-plans, hermes-book]
---

# Knowledge Base — md + README + git + Search

> **A project knowledge base is just `markdown` + a `README` index + `git`. Nothing simpler works better.**
>
> — GitMark Memory Bank (vakovalskii/gitmark-memory-bank)

## When to use this skill

- Setting up or reorganising project documentation (`docs/`)
- You or an AI agent need to find information faster than grep allows
- The KB is growing past ~10 files and starting to rot (orphans, stale docs, broken links)
- Designing how AI agents (Hermes, Claude Code) access project knowledge
- A user says "make docs searchable" or "I keep forgetting where things are"

## Core principle

**Markdown is the source of truth.** Everything derived (search index, HTML overview, link graph) is **regenerated** from md — git stays clean. No service, no database, no embeddings, no vendor.

## Architecture

```
CLAUDE.md / AGENTS.md / AGENT.md    ← entry point for AI agents
README.md                            ← project root index
  /docs
    README.md                        ← master index of all docs
    /services/<svc>/
      README.md                      ← always the folder index
    /reference/
    /ops/
    /decisions/
    /plans/
```

Every folder has a `README.md` that acts as its index — a table of contents with one-line descriptions.

## Light ontology (optional, prevents rot)

Inspired by Palantir Gotham/Foundry — typed objects, properties, and links over documents.

### Object types (`node_type`)

| Type | What it is | Where it lives |
|---|---|---|
| `service` | overview of one service/component | `docs/services/<svc>/README.md` |
| `reference` | cross-cutting spec | `docs/reference/` |
| `runbook` | operational procedure | `docs/ops/` |
| `decision` | architectural decision (ADR) | `docs/decisions/` |
| `plan` | plan before implementation | `docs/plans/` |
| `guide` | how to use something | varies |
| `gotcha` | pitfall + avoidance | `docs/ops/` |
| `index` | folder table of contents | any `README.md` |

### Properties (YAML frontmatter)

```yaml
---
node_type: service          # REQUIRED — from the table above
title: Payment Service      # human-readable name
service: payments           # which component
status: active              # active | draft | deprecated | archived
updated: 2026-06-10
tags: [payments, api]
links:                      # typed links
  depends_on: [../reference/architecture.md]
  documents: [../../src/payments/]
  supersedes: [./old-payments.md]
---
```

### Link types

| Key | Meaning | Direction |
|---|---|---|
| `documents` | describes this code/service | doc → code |
| `depends_on` | read that first | doc → doc |
| `supersedes` | replaces a stale doc | new → old |
| `relates_to` | adjacent topic | doc ↔ doc |
| `implemented_by` | where it lives in code | doc → source |
| `part_of` | belongs to a larger index | doc → index |

### Invariants (lint checks)

1. Every load-bearing doc has frontmatter with valid `node_type`
2. Values are within controlled vocabularies
3. No orphans — each load-bearing doc has ≥1 link in or out
4. No broken links (md link to missing file)
5. Every `docs/**` folder has a `README.md`
6. `supersedes` targets are `deprecated|archived`

## Enforcement: как заставить агентов соблюдать онтологию

Самая частая проблема: KB живёт по правилам, но агенты (Kanban worker, delegate_task child, cron job) пишут файлы **без** frontmatter. Онтология есть, lint проверяет, но нарушения накапливаются быстрее, чем чинятся.

### 4-слойная модель enforcement

```
Слой 1: AGENTS.md (Soft)     — образование, агент прочитал и знает
Слой 2: context injection    — delegate_task-дети получают правила в context
Слой 3: write_file wrapper   — скрипт-валидатор после записи
Слой 4: pre-commit hook      — блокирует коммиты с нарушениями
+
Cron: nightly repair          — чинит найденные нарушения автоматом
```

**Слой 1 — AGENTS.md (Soft)**

Файл `AGENTS.md` в корне KB содержит полную онтологию (типы, поля, статусы, шаблоны) + инструкцию:
> «Перед write_file в KB: прочитай этот файл. Каждый .md обязан иметь frontmatter с node_type.»

Доставка: каждый профиль, который пишет в KB, добавляет в SOUL.md ссылку на AGENTS.md.

**Слой 2 — context injection для delegate_task (Medium)**

При вызове `delegate_task`, если задача пишет в KB, родитель ОБЯЗАН включить в `context`:
```
Vault frontmatter rules: см. <path-to-AGENTS.md>
Каждый .md файл обязан иметь frontmatter с node_type, status, created, updated.
```

Это критично — ребенок в изолированном контексте не знает онтологии.

**Слой 3 — write_file wrapper (скрипт-валидатор)**

Скрипт `gotham-ensure-frontmatter.py`:
- `--mode=add-missing`: если нет frontmatter → вставляет минимальный (угадывает node_type по папке)
- `--mode=validate`: проверяет frontmatter, выдаёт ошибки
- `--all --mode=add-missing`: пробегает по всему vault

Агенты запускают этот скрипт ПОСЛЕ write_file как post-check.

**Слой 4 — pre-commit hook (Hard)**

Git hook (`pre-commit`) в .git/hooks/ KB:
- Проверяет каждый .md в коммите на наличие frontmatter с node_type
- Блокирует коммиты с G01-G07 нарушениями (см. инварианты)
- Единственный слой, который ловит ручные правки человека (через Obsidian)

### Stale status lifecycle

```yaml
Правило: если заметка status=active без обновления > 90 дней → archived
Исполнение: cron раз в неделю
Скрипт: gotham-stale-status.py — находит, предлагает, архивирует
```

### Когда какой слой нужен

| Сценарий | Сработает |
|---|---|
| Hermes-агент пишет через write_file | Слой 1 + 3 |
| delegate_task ребенок пишет в KB | Слой 2 (ручное) + у Слоя 4 fallback |
| Человек через Obsidian | Слой 4 (pre-commit) — единственная защита |
| Новый навык, который не патчили | Слой 4 fallback |
| Cron запускает запись | Слой 1 (SOUL.md профиля) + Слой 4 |

### Реализация в этом проекте

Спецификация Gotham для Obsidian vault (`~/hermes-vault/`) — в файлах:
- `System/Gotham/01-Ontology.md` — 19 node_type, поля, typed links, инварианты
- `System/Gotham/02-Enforcement.md` — детали 4 слоёв
- `System/Gotham/03-Roadmap.md` — фазы внедрения с Kanban-задачами
- `AGENTS.md` (корень vault) — инструкция для агентов

## Search indexing (FTS5)

A pure-stdlib Python CLI (like GitMark's `gitmark.py` at ~760 lines) builds a SQLite FTS5 index:

```
python3 scripts/gitmark.py index                    # build/reindex
python3 scripts/gitmark.py search "payment flow"    # bm25 + trigram + fuzzy
python3 scripts/gitmark.py map -o docs-map.html     # self-contained HTML + graph
python3 scripts/gitmark.py lint                     # check invariants I1–I6
```

**Three search strategies for cheap:**
- **bm25** — exact terms (SQLite FTS5 ranking)
- **trigram** — substrings, non-Latin (tokenize='trigram')
- **fuzzy** — 4-char windows for typos/morphology (≥20% coverage threshold)

The index is derived — add `.gitmark/` to `.gitignore`. Rebuild when docs change.

## AI agent integration

### Entry points

- `CLAUDE.md` / `AGENTS.md` / `AGENT.md` at repo root — the very first thing an AI reads
- Should list key files: `docs/README.md`, `docs/ontology.md`, key service docs
- Agents use this to orient themselves before any search

### Routing rule for agents

```
When you need to find information:
1. Knowledge base search (gitmark search / gms) — structured, ranked results
2. search_files / grep — only if the index is stale or the query is about code, not docs
```

This should be in the agent's system prompt, `AGENTS.md`, or persistent memory.

### Hermes skill integration

Create a `gitmark` skill with commands:
- `gms "<query>"` — search, return `file:line · heading · snippet`
- `gmi` — re-index
- `gmstat` — show index stats

## Curation workflow

**When adding a doc:**
1. Search first — don't duplicate
2. Pick `node_type` → choose folder
3. Add frontmatter (min: `node_type`; recommended: `title`, `service`, `status`, `updated`)
4. Add ≥1 link — no orphans
5. Add line to folder's `README.md` index
6. Run lint, re-index

**When editing:** bump `updated:`; if meaning changed and old doc is stale → `status: deprecated` + `supersedes`

**When moving:** `git mv` preserves history; rewrite every link; update both folder READMEs

## Tools that implement this pattern

| Tool | Description |
|---|---|
| **GitMark** (vakovalskii/gitmark-memory-bank) | Pure stdlib Python CLI (760 LOC). FTS5 search, HTML graph, ontology lint. Claude Code plugin. **Установлен под Hermes** — `~/.hermes/scripts/gitmark.py`, Obsidian vault заиндексирован. |
| **Hermes Agent skills** | ~/.hermes/skills/ with SKILL.md — procedural knowledge base, searchable via `skills_list` + `skill_view` |
| **Obsidian** | For personal KBs — graph view, tags, git sync. Index with GitMark for agent access. |

## Pitfalls

- **No index = blind grep.** Without a search index (FTS5), the agent falls back to `grep` / `search_files` which is slower, doesn't rank, and doesn't handle typos/morphology.
- **No ontology = pile of files.** Without types and links, a growing KB becomes a flat list of unconnected docs. The lint catches this.
- **Breaking links on rename.** `git mv` preserves history, but all cross-references must be updated. The lint catches broken links.
- **Derived artifacts in git.** The index (.gitmark/), HTML map, and any generated overviews should be gitignored. Only the source md is committed.
- **Scratch workspace can't write to KB.** If a Kanban worker needs to modify `docs/` or re-index, use `--workspace dir:` or handle side-effects after the worker completes.

## Related

- `writing-plans` — for writing project plans as docs/plans/ files
- `hermes-book` — for fiction/non-fiction book context management (separate concern)
- `kanban-worker` — pitfalls about filesystem side-effects in scratch workspaces
