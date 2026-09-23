---
name: codegraph-cli
description: "Use CodeGraph CLI directly for codebase navigation when MCP tools aren't available. Designed for coding subagents (delegate_task, OpenCode, Kanban workers)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [codegraph, codebase, navigation, mcp-fallback, subagent]
    related_skills: [native-mcp, hermes-agent]
---

# CodeGraph CLI — для кодинг-агентов

CodeGraph строит SQLite граф знаний проекта: функции, вызовы, импорты, наследование через tree-sitter. 19+ языков.

## Когда это нужно

MCP тулы (`mcp_codegraph_*`) регистрируются только при старте агента. Если сессия началась до подключения MCP-сервера — тулы не видны.

**Решение:** использовать CodeGraph CLI напрямую через `terminal()`.

## Быстрая проверка

```bash
# Доступен ли codegraph?
which codegraph

# Есть ли индекс в проекте?
ls .codegraph/

# Статус индекса
codegraph status
```

## Проект, где есть индекс

Индекс CodeGraph уже построен в `/home/hermes/.hermes/skills/` — там живут скиллы Hermes Agent.

Если работаешь в другом проекте — сначала инициализируй:

```bash
cd /path/to/project
codegraph init -i
```

## Все CLI команды

| Команда | Что делает |
|---------|-----------|
| `codegraph status [path]` | Статистика: сколько файлов, нод, связей |
| `codegraph query <символ>` | Быстрый поиск по имени (только расположение) |
| `codegraph context <описание задачи>` | **ГЛАВНАЯ КОМАНДА** — собирает search + node + callers + callees в один вывод с кодом |
| `codegraph callers <символ>` | Кто вызывает функцию/метод |
| `codegraph callees <символ>` | Какие функции вызывает данная |
| `codegraph impact <символ>` | Что сломается если менять символ |
| `codegraph files` | Дерево файлов проекта из индекса |

### codegraph context — самая полезная команда

Пиши естественным языком:

```bash
codegraph context "how does the skill loader work"
codegraph context "agent message handler"
codegraph context "tool executor"
```

Возвращает единый markdown-отчёт: резюме, сигнатуры, код, вызывающие/вызываемые.

## MCP-only тулы (нет CLI-эквивалента)

Через JSON-RPC на stdin:

```bash
# codegraph_node — детали одного символа (локация, сигнатура, docstring, связи)
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"codegraph_node","arguments":{"symbol":"myFunction"}}}' | \
  codegraph serve --mcp --path /path/to/project --no-watch 2>/dev/null

# codegraph_trace — путь вызова между двумя символами
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"codegraph_trace","arguments":{"from":"funcA","to":"funcB"}}}' | \
  codegraph serve --mcp --path /path/to/project --no-watch 2>/dev/null

# codegraph_explore — исходники нескольких связанных символов, сгруппированные по файлам
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"codegraph_explore","arguments":{"query":"symbol1 symbol2"}}}' | \
  codegraph serve --mcp --path /path/to/project --no-watch 2>/dev/null
```

**Важно:** `--no-watch` отключает файловый вотчер (быстрее, не тупит на медленных ФС).

## Pitfalls

### 🚫 Markdown НЕ индексируется
CodeGraph использует tree-sitter — `.md` файлы не парсит. Только код: Python, JS, TS, Go, Rust, Java, YAML и др.
Не пытайся искать по Obsidian-заметкам через CodeGraph — там пусто.

### ⚠️ Multiple instances накапливаются
Каждая Hermes-сессия (CLI, gateway, Kanban worker) запускает свой экземпляр codegraph через MCP (~78MB RSS каждый). При завершении сессии процесс не убивается — он становится orphan под PID 1.
Перед запуском `codegraph serve` или при жалобах на память — проверь сколько уже висит:
```bash
ps aux | grep -E 'codegraph.*serve.*mcp' | grep -v grep
```
Детекшн и cleanup — в навыке `native-mcp` → раздел "Multiple orphaned MCP processes found (memory leak)".

### ⚠️ uninit требует подтверждения
`codegraph uninit` спросит `Continue? (y/N)`. Чтобы не зависло:
```bash
echo "y" | codegraph uninit
```

### 🔄 Синк инкрементальный
`codegraph sync` работает секунды — обновляет граф новыми изменениями без переиндексации.

### 🔁 Если MCP тулы всё-таки видны
Используй их — они удобнее (не надо `cd`, не надо парсить stdout):
- `mcp_codegraph_codegraph_context` — то же что `codegraph context`
- `mcp_codegraph_codegraph_search` — то же что `codegraph query`
и т.д. Имена с двойным `codegraph` из-за конвенции нейминга `mcp_{server}_{tool}`.