# Kilo Code Subagent Architecture — Сравнение с Hermes

> Результат исследования 05.06.2026. Kilo (ранее KiloCode) — open source AI coding agent.

## Как устроены саб-агенты в Kilo

### Встроенные саб-агенты

| Саб-агент | Описание | Инструменты |
|-----------|----------|-------------|
| **explore** | Read-only, быстрый. Только поиск по коду. | read, grep, glob (НЕ edit, НЕ bash) |
| **general** | Полный доступ. Для многошаговых задач. | Все инструменты (кроме todo) |

### Пользовательские саб-агенты

Определяются через `kilo.jsonc` или `.md` файлы в `~/.config/kilo/agents/`:

```json
{
  "agent": {
    "code-reviewer": {
      "description": "Reviews code for best practices",
      "mode": "subagent",
      "model": "anthropic/claude-sonnet-4-20250514",
      "permission": { "edit": "deny", "bash": "deny" }
    }
  }
}
```

### Режимы (mode)

| Режим | Описание |
|-------|----------|
| primary | Основной агент, с которым работает пользователь |
| subagent | Только через `@name` или `task` tool |
| all | И то, и другое (дефолт для кастомных) |

### Запуск

1. **Автоматический** — primary agent сам решает запустить subagent через `task` tool
2. **Ручной** — `@code-reviewer проверь auth module`

### Параллельность

Агенты могут запускать несколько subagent'ов **конкурентно** (до 3). Это встроено в модель.

### Permissions (гранулярные)

```json
{
  "permission": {
    "edit": "deny",
    "bash": {
      "*": "ask",
      "git diff": "allow",
      "git log*": "allow"
    },
    "task": {
      "*": "deny",
      "code-reviewer": "allow"
    }
  }
}
```

## Сравнение с Hermes

| Аспект | Kilo | Hermes |
|--------|------|--------|
| **Запуск** | `task` tool — inline spawn, та же сессия | Kanban (SQLite + профиль) или `delegate_task` |
| **Канал** | Результат возвращается строкой в `task` tool | Через summary Kanban или return delegate_task |
| **Explorer** | Встроенный, read-only | Нет встроенного — researcher через Kanban |
| **Кастомные** | `.md` или `jsonc` файлы | Kanban-профили с SOUL.md |
| **Permissions** | Гранулярные (edit/bash/task allow/ask/deny) | Только toolsets у профиля |
| **Параллельность** | До 3, встроено | `delegate_task(tasks=[...])` до 3 |
| **Режимы** | primary/subagent/all | Разделение на Kanban-профили |
| **Изоляция** | Отдельная сессия, без общего стейта | Kanban: отдельный процесс. delegate_task: отд. сессия |

## Что можно взять к нам

1. **Более лёгкий spawn** — вместо Kanban для быстрых задач использовать `delegate_task` (уже можем)
2. **Встроенный explore** — можно применить: когда нужно быстро узнать что-то по коду → delegate_task с codegraph-cli
3. **Параллельные задачи** — `delegate_task(tasks=[...])` уже есть, до 3
4. **Read-only режим** — идея для review/explore: запретить edit, дать только read

**Основное отличие:** Kilo легче (inline spawn), но Hermes надёжнее (SQLite, профили, переживает перезапуски). Kanban — для формальных задач, delegate_task — для быстрых.
