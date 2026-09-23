---
name: orchestrator-routing
description: Правила роутинга — какой профиль для какого типа задач. Загружается автоматически из основного SOUL.md.
tags: [orchestrator, routing, profiles]
---

# Orchestrator Routing

Загружается автоматически. Определяет как оркестратор выбирает профиль для задачи.

## Роутинг

- **Исследование, поиск, цены, факты** → researcher (Kanban)
- **Код, фикс, баг** → coder / debugger (Kanban)
- **Архитектура, spec** → architect (Kanban)
- **Ревью кода** → reviewer (Kanban)
- **Навык сломан / анализ навыка** → skill-improver (Kanban)
- **Сессия пошла не так / разбор** → self-improver (Kanban)
- **Рутина: t list, t done, Obsidian** → worker (Kanban / delegate_task)
- **Быстрые эксперименты, «найди и проверь»** → explorer (delegate_task, read-only)
- **Мониторинг, парсинг, diff-анализ** → scout (Kanban или cron)
- **Недвижимость Узбекистан** → realtor (Kanban)
- **Консультация, вопрос про подход/инструмент** → ask (delegate_task)
- **Рефакторинг, код-стайл, SOLID** → refactoring-guru (Kanban, только план → OK → исполнение)
- **Создание/обновление навыков** → skill-writer (Kanban)
- **Оптимизация промптов (SOUL.md, SKILL.md)** → prompt-engineer (Kanban, только план)
- **English lessons (english-lesson)** → main agent (сам) — *профиль TBD, пока оркестратор не делегирует*
- **Python road (python-road)** → main agent (сам) — *профиль TBD, пока оркестратор не делегирует*
- **Образовательный контент, генерация уроков (english-lesson, python-road)** → main agent (сам) — *профиль TBD*
- **Быстрый факт (файл, путь, время)** → сам, 1-2 tool calls

## Профили (модели)

| Профиль | Модель | Роль |
|---------|--------|------|
| researcher | deepseek | Поиск, crawl, данные |
| coder | deepseek | Написание кода |
| debugger | deepseek | Root cause |
| architect | deepseek | Spec, архитектура |
| reviewer | deepseek | Ревью кода |
| worker | deepseek | Рутина, скрипты, t-команды |
| explorer | deepseek (max_turns=10, reasoning_effort=low) | Быстрые read-only эксперименты |
| skill-improver | deepseek | Анализ навыков, только план |
| self-improver | deepseek | Анализ неудач, только план |
| scout | deepseek | OSINT-мониторинг, diff-анализ |
| realtor | deepseek | Недвижимость Узбекистан |
| ask | deepseek | Консультации по подходам |
| refactoring-guru | deepseek | Рефакторинг кода |
| skill-writer | deepseek | Создание SKILL.md |
| prompt-engineer | deepseek | Оптимизация промптов |

### Поиск — приоритет: hms → gms → search_files

**Жёсткий порядок для ЛЮБОГО поиска (код, vault, конфиги):**
1. `hms "запрос"` — FTS5 по ~/.hermes/ (кодовая база hermes-agent, навыки, конфиги, скрипты) — ~6700 файлов
2. `gms "запрос"` — FTS5 по ~/hermes-vault (заметки, дневники, контакты, планирование)
3. `search_files` / grep — ТОЛЬКО если оба вернули пустой результат

hms индексирует всю ~/.hermes/ включая hermes-agent код, поэтому он быстрее grep/search_files для поиска по коду.

Установлены:
- `~/.local/bin/gms` — CLI для vault (скрипт, вызывает upstream из gitmark-memory-bank)
- `hms` — FTS5 для ~/.hermes
- `gmi` / `gmstat` — алиасы

Обновление индексов:
- vault: `gmi` (или `python3 /home/hermes/gitmark-memory-bank/skills/kb-search/gitmark.py --root ~/hermes-vault index --force`)
- hms: `hms index --force`

**Этот порядок передаётся суб-агентам через context при delegate_task + зашит в навык sub-agents-orchestrator для Worker и Explorer.**

## Kanban max_turns

- Дефолт: 20
- Для задач coder/researcher/reviewer с большими файлами: увеличить до 100
- Self-improver: 50

## Researcher task splitting rule

**⚠️ НИКОГДА не объединять несколько исследовательских тем в одну Kanban задачу.**
Каждая независимая исследовательская тема — отдельная задача.

Правильно:
- Задача 1: «Анализ районов Нукуса» → researcher
- Задача 2: «Рынок цен на 1-к квартиры» → researcher
- Задача 3: «Проверка физ лиц онлайн Узбекистан» → researcher

Неправильно:
- ❌ Одна задача: «Исследовать Нукус (районы+цены+проверка)» → researcher (долго, поверхностно, плохой результат)

Причина: researcher профиль обрабатывает задачи последовательно в рамках одной сессии. Чем больше разных тем в одной задаче, тем хуже coverage каждой. Параллельные задачи дают лучший результат быстрее.

## delegate_task vs Kanban

| Ситуация | Что использовать |
|----------|----------------|
| Быстрый факт (путь, время, файл) | Сам, 1-2 tool calls |
| Рассуждение/поиск без side-эффектов | delegate_task на Explorer (read-only, max_turns=10, reasoning_effort=low) |
| Формальная задача с кодом/файлами | Kanban (нужен approval, есть артефакты) |
| Параллельные независимые подзадачи | delegate_task с tasks[] (до 3 параллельно) |
| Долгая задача (часы+) | Kanban (живёт вне сессии, есть уведомления) |

Explorer профиль: read-only, file+terminal+session_search, max_turns=10, reasoning_effort=low. Для быстрых исследовательских задач.
