---
name: hermes-book
category: productivity
description: Universal book context loader + updater. Fiction book.yaml / diary meta.yaml. Tiered compression.
---
# hermes-book

**Скрипт:** `~/.hermes/scripts/hermes_book.py`

**Команды:**
- `context <path> [--compress] [--count N] [--json]` — загрузить контекст с tiered compression
- `status <path>` — статус книги
- `update <path> summary/chars/threads --text/--file`

**Tiered compression:** Consolidation (последние 2) → Summarization (3-5) → Distillation (6+)

Типы книг: fiction (book.yaml, character_sheets) / diary (meta.yaml, без персонажей)