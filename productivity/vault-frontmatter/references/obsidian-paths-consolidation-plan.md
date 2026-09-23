# Vault path consolidation — redone (2026-06-13)

**Важно:** 13.06.2026 направление было развёрнуто — `Дневник/` удалён, `Journal/` стал каноничным.

## Canonical paths (актуально)

| Purpose | Canonical path | Notes |
|---|---|---|
| Daily diaries | `Journal/{date}.md` | Единая директория. Дневник/ (рус) — удалён |
| Agent reports | `System/AgentsData/{Agent}/{date}-{topic}.md` | obsidian_save.py пишет сюда с frontmatter |
| Agent data (legacy) | `agents-data/` | DEPRECATED |
| Learning | `Learning/{Lang|Topic}/` | english, ielts-prep, python-road |
| Plans | `Projects/Planning/{date}/` | life-planning |
| Long-term plans | `Projects/Planning/` | canonical path |
| Contacts | `Areas/Contacts/people/` | contacts skill |

## История изменений

**13.06.2026** — Разворот: Дневник/ → Journal/
- Пользователь запросил миграцию обратно: `Journal/` как каноничный путь
- Все 4 файла из `Дневник/` перенесены в `Journal/` (11-е смержен, 12-е и 13-е скопированы)
- `Дневник/` удалён
- 10+ навыков и скриптов обновлены
- Git commit: `migrate: Дневник/ → Journal/, merge files, update all skills refs`

**11.06.2026** — Journal(45) → Дневник/
- Был сделан P1-перенос Journal (45 файлов) в Дневник/
- gitmark индекс перестроен
- Journal оставлен как есть (планировалось удаление, но не выполнено)
