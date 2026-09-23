# Kilo Code Subagent Architecture (справка для orchestration-rules)

## Базовые саб-агенты Kilo

| Саб-агент | Описание | Инструменты |
|-----------|----------|-------------|
| **explore** | Read-only, быстрый | read, grep, glob — НЕ edit/bash |
| **general** | Полный доступ | Все инструменты |

## Как работает делегирование

1. Primary agent (Code/Plan/Debug) решает что нужен саб-агент
2. Вызывает `task` tool с указанием subagent'а и goal
3. Subagent запускается в изолированной сессии
4. Возвращает результат строкой в `task` tool
5. Primary agent продолжает

**Параллельность:** до 3 subagent'ов одновременно.

## Сравнение с нашим подходом

| Сценарий | Kilo | Hermes |
|----------|------|--------|
| Быстрый поиск по коду | `@explore` | `delegate_task` + codegraph-cli |
| Исследование | `@general` | Kanban → researcher |
| Многошаговая задача | `task` → несколько subagent'ов | Kanban → coder/architect |
| Параллельные запросы | Несколько `task` вызовов | `delegate_task(tasks=[...])` |

**Вывод:** у нас уже есть все инструменты. Kilo — легче (inline), мы — надёжнее (Kanban с SQLite и переживанием перезапусков). Там где Каnban — оверхед, используй `delegate_task`.

## Кастомные суб-агенты (Kilo)

Kilo позволяет создавать кастомные суб-агенты двумя способами:
- **JSON** в `kilo.jsonc`: `agent.code-reviewer = { mode: "subagent", description, prompt, permission: { edit: "deny", bash: "deny" } }`
- **Markdown** файлы в `~/.config/kilo/agents/` или `.kilo/agents/`: filename.md → YAML frontmatter + body = system prompt

### Permissions (гранулярные)
```
permission:
  edit: allow|ask|deny        # редактирование файлов
  bash:                       # shell-команды
    "*": deny                 # всё запрещено
    "git diff": allow         # но git diff разрешён
    "git log*": allow         # git log разрешён
  task:                       # какие суб-агенты можно вызывать
    "*": deny
    "code-reviewer": allow
```

### Встроенные суб-агенты
- **explore** — read-only, быстрый, без edit/bash. Только glob + grep + чтение файлов
- **general** — полный доступ, многошаговые задачи

### Инвокация
- **Автоматическая** — primary agent решает что нужен суб-агент и вызывает `task` tool
- **Ручная** — `@agent-name` в сообщении (например `@code-reviewer проверь auth`)

### Параллельность
До 3 суб-агентов одновременно. Возвращают результат строкой через `task` tool.

### GCD (Global Context/Communication)
В Kilo нет отдельного GCD-канала. Результат передаётся как return value `task` tool — строка-резюме от суб-агента к родителю. Это легковеснее нашего Kanban (SQLite + файлы), но и менее надёжно (не переживает перезапуск).

## Что мы взяли из Kilo в этой сессии
1. **explorer профиль** — настроен как read-only (file+terminal+session_search, max_turns=10, reasoning_effort=low). Аналог Kilo explore.
2. **Более лёгкий spawn** — delegate_task для быстрых задач вместо Kanban. Kanban только для формальных многошаговых.
3. **Разделение** — researcher = интернет, explorer = код.

Подробнее: `sub-agents-orchestrator/references/kilocode-subagent-architecture.md`
