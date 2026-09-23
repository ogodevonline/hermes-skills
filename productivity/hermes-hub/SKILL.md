---
name: hermes-hub
category: productivity
description: Единая сводка задач, целей, сфер и проблем. Команды: `hermes-hub` (CLI), `/hub` (чат).
---
# Hermes Hub

**Команды:** `hermes-hub` (CLI), `/hub` (чат)
**Скрипт:** `~/.local/bin/hermes-hub`

**Источники:** task_display (задачи) → tasks.db (статистика, carry_over) → goals.yaml (цели) → planning.py (сферы) → eternal tasks (5+ переносов)

**Известная проблема:** planning.py отдаёт `sphere_summary` (dict), hub ожидает `sphere_trends` (list) → блок сфер всегда 0. Согласование в шаге 9.