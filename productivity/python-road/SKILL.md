---
name: python-road
category: productivity
description: Изучение Python и Software Engineering через параллельные треки знаний. LeetCode CLI интеграция, генерация сессий, сохранение в Obsidian.
---

# Python Road

Система обучения Python + Software Engineering с параллельными треками и отслеживанием прогресса. Аналог english-lesson, но для технических навыков.

**Ключевое отличие от english-lesson:** не линейная книга, а **мультитрековая система** — можно в любой день выбрать, что учить.

## Архитектура

**Vault:** `~/hermes-vault/Python/` (там же, где и английский)

### Структура в Obsidian

```
Python/
├── state.yaml
├── roadmap.md                          ← авто-генерируемая визуализация прогресса
├── Track-01-python-basics/
│   ├── track.yaml                      ← мета-описание трека
│   ├── session-01-variables-types/
│   │   ├── notes.md                    ← теория
│   │   ├── practice.md                 ← твои решения
│   │   ├── review.md                   ← вопросы для повторения
│   │   └── session.yaml               ← краткая выжимка (для prepare)
│   └── ...
├── Track-02-algorithms/
│   ├── track.yaml
│   ├── session-01-two-pointers/
│   │   ├── notes.md
│   │   ├── practice.md
│   │   ├── review.md
│   │   └── session.yaml
│   └── ...
├── Track-03-data-structures/
├── Track-04-databases/
├── Track-05-patterns/
├── Track-06-architecture/
└── Track-07-tooling/
```

### state.yaml

```yaml
level: beginner          # beginner / intermediate / advanced
active_track: python-basics   # какой трек сейчас активен
tracks:
  python-basics:
    label: "🐍 Python Basics"
    level: intermediate
    current_session: session-02-functions
    completed: [session-01-variables-types]
    last_topic: functions
    last_summary: "Разобрали типы данных: int, float, str, bool, None. Приведение типов, динамическая типизация."
    last_concepts: [int, float, str, type-casting, dynamic-typing]
  algorithms:
    label: "⚡ Algorithms"
    level: beginner
    current_session: session-01-two-pointers
    completed: []
    last_topic: null
    last_summary: null
    last_concepts: []
  # ... остальные треки
```

### session.yaml (внутри папки сессии)

```yaml
topic: "Two Pointers Technique"
summary: "Разобрали базовый паттерн two pointers на задаче Two Sum II. Суть: два указателя с разных концов отсортированного массива."
concepts: [two-pointers, sorted-array, O(n)]
leetcode_solved: [167]
```

## Треки и последовательность тем

Темы — нежёсткий порядок, как "сюжет" в english-lesson. Можно скипнуть, перегенерить, повторить.

### 01 — Python Basics
`variables` → `types` → `strings` → `control-flow` → `lists` → `dicts-sets` → `functions` → `scope-closures` → `comprehensions` → `classes` → `inheritance` → `magic-methods` → `exceptions` → `iterators` → `generators` → `decorators` → `context-managers` → `async-basics` → `async-await` → `typing`

### 02 — Algorithms
`two-pointers` → `sliding-window` → `binary-search` → `merge-sort` → `quick-sort` → `dfs` → `bfs` → `backtracking` → `dp-basics` → `dp-intermediate` → `greedy` → `intervals` → `graphs-basics` → `topological-sort`

### 03 — Data Structures
`arrays` → `linked-lists` → `stacks` → `queues` → `hash-tables` → `hash-sets` → `binary-trees` → `bst` → `heaps` → `graphs` → `tries` → `union-find`

### 04 — Databases
`select-where` → `joins` → `group-by` → `having` → `subqueries` → `window-functions` → `cte` → `indexes` → `normalization` → `transactions` → `explain-analyze`

### 05 — Patterns
`strategy` → `observer` → `factory` → `singleton` → `decorator` → `adapter` → `facade` → `command` → `state` → `template-method` → `mvc` → `repository`

### 06 — Architecture
`solid` → `clean-architecture` → `dependency-injection` → `rest-design` → `repository-unitofwork` → `event-sourcing` → `cqs` → `microservices` → `cqrs`

### 07 — Tooling
`git-basics` → `git-branching` → `pytest-basics` → `pytest-fixtures` → `mocking` → `docker-basics` → `docker-compose` → `ruff-flake8` → `mypy` → `pre-commit` → `github-actions`

## Формат сессии

Каждая сессия включает:

1. **📝 Theory (notes.md)** — концепция, примеры кода, best practices, анти-паттерны
2. **💻 Practice (practice.md)** — задания, твои решения, код
3. **❓ Review (review.md)** — 3-5 вопросов для закрепления (с ответами, которые ты дописываешь)

> **🌐 ВАЖНО: Перевод на русский**
> Весь контент для Python Road генерируется **на русском языке** — теория, примеры, практика, review.
> Пользователь (Василий) учит Python, а не английский. Английские термины и названия функций/методов
> можно оставлять в оригинале (с переводом/пояснением), но объяснения — только по-русски.

## Отправка в Telegram

При отправке результата сессии в Telegram:
- **Разбивать на чанки** — каждое сообщение не больше **3500 символов**
- Использовать последовательную отправку через `send_message` (несколько сообщений)
- **Не обрезать текст** — лучше 5 сообщений, чем обрезанный материал
- Структура разбивки:
  1. **Заголовок** — `🐍 {Track} — {Тема} (уровень: {level})`
  2. **📝 Theory** — может быть 2-3 чанка
  3. **💻 Practice** — задания с кодом
  4. **❓ Review** — вопросы для закрепления
  5. **LeetCode** — если решена задача
  6. **Прогресс** — `статус трека: 45%`
- В каждом чанке в начале указывать эмодзи-маркер раздела, чтобы было понятно
- Ссылки не сокращать

Пример:
```
🐍 **Python Basics — Функции (intermediate)**

📝 **Теория: Функции**

Функции в Python — это объекты первого класса. Их можно:
• Присваивать переменным
• Передавать как аргументы
• Возвращать из других функций

def greet(name: str) -> str:
    return f"Привет, {name}!"

...
```

```
📝 **Теория (продолжение): Области видимости**

LEGB Rule:
• **L**ocal — локальная область функции
• **E**nclosing — объемлющая (внешняя функция)
• **G**lobal — глобальная
• **B**uilt-in — встроенная

...
```

```
💻 **Практика:**

1. Напиши функцию, которая принимает список чисел и возвращает...
2. Используя lambda и map, преобразуй...
3. ...

_Решение сохранится в Obsidian после выполнения_
```

## Для Algorithms / Data Structures / Databases — дополнительно:
- LeetCode задача через `leetcode-cli`
- Файл с шаблоном генерируется через `leetcode pick --lang python3`
- Решение сохраняется в practice.md

## Триггеры

Напоминания — через крон, **общие с english-lesson** (4 раза в день MSK: 09:00, 14:00, 18:00, 20:00):

```
⏰ Study time!

🇬🇧 /english — урок английского
🐍 /python — Python (или /python algorithms, /python databases)
⏭️ /python skip — пропустить
```

Крон-задачи загружают оба навыка (`english-lesson` + `python-road`), но **только отправляют напоминание** — генерация урока происходит по команде пользователя в диалоге.

## Команды пользователя

| Команда | Действие |
|---------|----------|
| `/python` | Начать/продолжить сессию (активный трек) |
| `/python <track>` | Выбрать трек (например: `/python algorithms`) |
| `/python skip` | Пропустить тему |
| `/python redo` | Перегенерировать текущую тему |
| `/python harder` | Повысить уровень (beginner → intermediate) |
| `/python easier` | Понизить уровень |
| `/python progress` | Показать прогресс по всем трекам |

## CLI скрипт

Скрипт: `~/.hermes/skills/productivity/python-road/scripts/python_road.py`

Vault path: `~/hermes-vault/Python/`

### prepare — получить контекст для генерации

```bash
python3 python_road.py prepare --track algorithms
```

Возвращает JSON:
- track (название трека)
- level (уровень)
- current_session (текущая сессия или null)
- completed (список завершённых)
- last_topic (последняя тема)
- last_summary (краткое саммари последней сессии)
- last_concepts (ключевые понятия)
- available_topics (следующие темы из последовательности)
- all_progress (краткий прогресс по всем трекам)

### save — сохранить сессию

```bash
# Строками
python3 python_road.py save \
  --track algorithms \
  --topic "Two Pointers Technique" \
  --summary "Разобрали..." \
  --concepts "two-pointers,sorted-array" \
  --leetcode "167" \
  --notes /tmp/notes.md \
  --practice /tmp/practice.md \
  --review /tmp/review.md

# Или файлами (пути, начинающиеся с /)
python3 python_road.py save \
  --track algorithms \
  --topic "Two Pointers" \
  --summary "..." \
  --notes /tmp/notes.md \
  --practice /tmp/practice.md \
  --review /tmp/review.md
```

### status — показать прогресс

```bash
python3 python_road.py status
```

Выводит roadmap-панель:
```
🐍 Python Basics    ███████░░░  70%  topic: decorators
⚡ Algorithms       ████░░░░░░  40%  topic: two pointers
...
```

## ⚠️ Pitfalls

### prepare: контекст должен быть компактным
Никогда не читать полные notes.md/practice.md прошлых сессий. Только session.yaml (summary + concepts). Иначе контекстное окно разрастётся.

### save: всегда сохранять session.yaml
session.yaml — единственное, что prepare будет читать из прошлых сессий. Если его не создать, prepare не сможет дать контекст.

### state.yaml: не редактировать руками (кроме экстренных случаев)
Поле `last_summary` должно обновляться автоматически при save. Если нужно сбросить трек — используй команду.

### LeetCode CLI: нужна авторизация
Перед первым использованием: `leetcode login` (cookie-based, через браузер).

### track.yaml: создаётся один раз при первом prepare
Если трек не существует в vault — скрипт создаёт Track-NN-slug/track.yaml с мета-данными.

## Установка LeetCode CLI

```bash
npm install -g @night-slayer18/leetcode-cli
leetcode login  # через OAuth/браузер
```
