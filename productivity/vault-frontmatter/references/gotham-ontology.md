# Gotham Ontology — краткий справочник

## 19 node_type

**Контентные (12):** journal, note, plan, book, profile, log, summary, task, person, reflection, system-note, agent-memory
**Мета (7):** index, area, project, system, learning, reference, archive

## 5 статусов

draft → active → done / cancelled → archived

## Stale-правило

`status: active` без `updated` > 90 дней → archived.

## Инварианты (G-коды)

| Код | Уровень | Суть |
|-----|---------|------|
| G01 | ERR | Нет frontmatter с node_type |
| G02 | ERR | node_type не из словаря |
| G03 | WARN | status не из словаря |
| G04 | WARN | active > 90d без обновления |
| G05 | ERR | created/updated не ISO дата |
| G06 | ERR | links.* ссылается на несуществующий файл |
| G07 | WARN | plan без done/cancelled > 60d |

## Pre-commit hook блокирует

ERR-нарушения (G01, G02, G05, G06) → commit отклонён.
WARN (G03, G04, G07) → commit проходит.
