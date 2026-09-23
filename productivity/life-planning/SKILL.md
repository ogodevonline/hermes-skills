---
name: life-planning
category: productivity
description: Я сам веду планирование Василия — напоминаю, обратная связь, ревью по всем горизонтам.
requires: [personal-task-tracker, evening-diary-brief, morning-brief-pipeline]
---
# Life Planning

Сам инициирую ревью, не жду команды.

**7 горизонтов:** 10-лет → 5-лет → 3-г → 2-г → год → месяц → неделя

**Данные:** `planning.py --period week` → JSON (дневники, планы, тренды)
**Компакт:** `planning.py --goals-checkin` → текстовая сводка

**Сохранение:** `obsidian_utils.write_file("Projects/Planning/{YYYY-MM-DD}/review.md", ...)` + `obsidian_utils.commit("plan session")`. После записи — показать результат пользователю и подтвердить что запушено.

Структура папок: scripts/planning.py, references/template-detection.md