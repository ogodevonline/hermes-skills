---
name: vault-frontmatter
description: Обязательные правила frontmatter для файлов vault. Загрузить перед любым write_file в /home/hermes/hermes-vault/.
tags: [gotham, vault, frontmatter, compliance]
---

# Vault Frontmatter Rules

> Загрузи этот навык, если твоя задача пишет в `/home/hermes/hermes-vault/`.

**Структура vault (куда писать):** см. таблицу в разделе «Угадывание node_type по папке» ниже.

Справочник по онтологии (node_type + таблица угадывания + пути скриптов) — см. `references/gotham-ontology.md`.

## Шаг 1 — Прочитай AGENTS.md

Перед любым write_file в vault:

```bash
cat /home/hermes/hermes-vault/AGENTS.md
```

Это единый источник правил: 19 node_type, 5 статусов, обязательные поля.

## Шаг 2 — Используй правильный шаблон frontmatter

Каждый `.md` файл ОБЯЗАН иметь YAML frontmatter:

```yaml
---
node_type: journal       # из словаря (обязательно)
status: draft            # draft/active/done/cancelled/archived
created: 2026-06-11      # ISO дата YYYY-MM-DD
updated: 2026-06-11      # ISO дата YYYY-MM-DD
---
```

### Угадывание node_type по папке

Если не знаешь какой node_type — используй таблицу:

| Папка в vault | node_type |
|---------------|-----------|
| Journal/ | journal |
| Inbox/ | note |
| Projects/Planning/ | plan |
| Areas/Contacts/people/ | person |
| Areas/Profile/ | profile |
| Areas/Habits/ | note |
| Learning/English/ | note |
| Learning/*/ | learning |
| System/* | system-note |
| System/AgentsData/* | agent-memory |
| Archive/ | archive |
| */README.md | index |
| * (остальное) | note (safe default) |

### Полный словарь node_type (19 типов)

**Контентные:** journal, note, plan, book, profile, log, summary, task, person, reflection, system-note, agent-memory
**Мета:** index, area, project, system, learning, reference, archive

### Полный словарь статусов

draft, active, done, cancelled, archived

## Шаг 3 — После write_file запусти валидацию

```bash
python3 /home/hermes/scripts/gotham-ensure-frontmatter.py --path <file> --mode=validate
```

Если validate вернул ERROR — исправь frontmatter вручную и повтори валидацию.

## Шаг 4 — Если файл не твой (редактируешь существующий)

Не перезаписывай frontmatter — только добавь недостающие поля.
Используй `--mode=add-missing` вместо `--mode=validate`:

```bash
python3 /home/hermes/scripts/gotham-ensure-frontmatter.py --path <file> --mode=add-missing
```

## Шаг 5 — Если ты делегируешь запись через delegate_task

Передай в context строку:
```
Vault frontmatter rules: см. /home/hermes/hermes-vault/AGENTS.md. Загрузи навык vault-frontmatter.
```

## Ошибки и fallback

- **Питфолл (27.09, weekly-finance cron):** pre-commit хук = `gitmark.py lint --strict` по ВСЕМУ vault — три Journal-файла без frontmatter (созданные ритуалами) блокировали коммит моего дайджеста. Фикс: `--mode=add-missing` по каждому ERR-файлу (контент не трогает), затем `git commit -m ... -- <мой/путь>` (pathspec = только мой файл, чужие staged не утаскивать). `--no-verify` НЕ использовать.

- Если скрипт gotham-ensure-frontmatter.py не найден → добавь frontmatter вручную по шаблону выше
- Если не можешь угадать node_type → ставь `note` (безопасный дефолт)
- Если validate ERROR → НЕ блокируй задачу, исправь и продолжай
- После исправления запусти `kanban_complete` с gotham_error в metadata если были проблемы

### Pitfall: файл с frontmatter но без node_type

`--mode=add-missing` НЕ трогает файлы у которых уже есть YAML frontmatter, даже если в нём нет `node_type`. Если скрипт выдал `ERROR: Frontmatter exists but node_type is missing` — нужно исправить вручную через patch:

```
patch(
    path=".../file.md",
    old_string="---\n<существующие поля>",
    new_string="---\nnode_type: <тип>\n<существующие поля>"
)
```

Тип угадывается по папке (см. таблицу выше). Пример: файлы в `Areas/Contacts/people/*` → `person`, файлы в `System/AgentsData/Worker/*` → `agent-memory`.

Без этой ручной правки файл останется с ERR G01 и pre-commit hook заблокирует коммит.

## Где лежат скрипты

Скрипты разбросаны по двум директориям — см. `references/gotham-scripts.md` для точных путей.
