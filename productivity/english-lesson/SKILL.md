---
name: english-lesson
category: productivity
description: Изучение английского через интерактивные уроки-истории с сохранением в Obsidian. Уроки генерируются по запросу пользователя, крон только напоминает.
---

# English Lesson System

Изучение английского (A2) через генерацию интерактивных уроков с сюжетной линией.  
Уроки **по запросу пользователя** — крон-задачи только отправляют напоминания в Telegram.

## Архитектура

**Vault:** `~/hermes-vault` (github.com/ogodevonline/hermes-vault)

**Структура в Obsidian:**
```
Английский/
├── state.yaml                          ← уровень, текущая книга, сессия
└── Книга-NNN-slug/
    ├── book.yaml                       ← мета: название, жанр, персонажи, сеттинг, сюжетная база
    ├── session-001/
    │   ├── grammar.md                  ← грамматическая тема
    │   ├── text.md                     ← текст/история урока
    │   └── vocabulary.md              ← словарь к уроку
    ├── session-002/
    │   ├── grammar.md
    │   ├── text.md
    │   └── vocabulary.md
    └── ...
```

### state.yaml
```yaml
level: A2
book: Книга-001-slug        # null если книги нет
session: 5                   # номер текущей сессии (инкрементится при save)
total_sessions: 5
sessions_today: 2           # сбрасывается при смене дня
last_session_date: '2026-04-29'
```

### book.yaml
```yaml
title: Название книги
genre: fantasy / sci-fi / cultivation / ...
level: A2
setting: Краткое описание мира
summary: Краткий сюжет (обновляется)
characters:
  - name: Имя
    role: главный герой / наставник / ...
    traits: [черта1, черта2]
    arc: кратко о развитии персонажа
themes: [тема1, тема2]
plot_threads:  # активные сюжетные линии
  - description: что происходит
    status: active / resolved
```

## Триггеры (крон)

4 напоминалки в день (MSK): 09:00, 14:00, 18:00, 20:00

Каждая отправляет в Telegram короткое напоминание:
> "⏰ English time! Напиши **start** чтобы начать урок, **skip** чтобы пропустить, **newbook** чтобы сменить книгу."

Генерация урока происходит **только по команде пользователя** в диалоге.

## Формат урока

Каждая сессия включает:

1. **Vocabulary** — 5-7 новых слов с переводом + пример употребления в IT/жизнь-контексте
2. **Story** — 300-400 слов, захватывающий сюжет (экшн, эмоции, повороты)
3. **Grammar & Usage** — одна конструкция из текста с разбором: структура, примеры, таблица
4. **Check** — 1 вопрос по тексту на английском

После завершения урока — сохранить в Obsidian:
- `session-NNN/grammar.md`
- `session-NNN/text.md`
- `session-NNN/vocabulary.md`
- Обновить `state.yaml` (session +1)
- Обновить `book.yaml` (summary, plot_threads)
- **Git:** скрипт `save` сам делает `git commit`, поэтому отдельный git add/commit не нужен. Проверить успешность: `git log --oneline -1` — будет коммит вида `english: session NNN — Книга...`. Если коммита нет — сделать `git add -A && git commit -m "english lesson session N" && git push` вручную.
- 🧠 Если `git status` показывает "nothing to commit" — это нормально, save уже закоммитил. Проверь `git log --oneline -1` чтобы убедиться.

## Выбор новой книги

Когда пользователь хочет новую книгу (команда `newbook`):

1. Спросить про жанр/настроение (fantasy, sci-fi, mystery, adventure, slice of life)
2. Предложить 2-3 варианта с завязкой
3. После выбора:
   - Создать `Книга-NNN-slug/` с `book.yaml`
   - Обновить `state.yaml`
4. Для новой книги можно использовать `new-book` команду скрипта, либо создать руками

## Отправка в Telegram

При отправке результата урока в Telegram (после генерации):
- **Разбивать на чанки** — каждое сообщение не больше **3500 символов** (запас под Markdown)
- Использовать `split_to_chunks()` из `~/.hermes/scripts/telegram_splitter.py` или вручную разбивать
- Отправлять **несколько сообщений** последовательно, а не одной портянкой
- Структура разбивки:
  1. **Заголовок** — `📖 English — Книга X, Сессия N`
  2. **Vocabulary** — слова с переводом (можно в заголовок)
  3. **Story** — текст истории (может быть 2-3 чанка)
  4. **Grammar** — грамматический разбор
  5. **Check** — вопрос по тексту
  6. **Links** — ссылка на Obsidian и подсказка `harder/easier/skip`
- Если что-то из этого маленькое — можно объединять, главное не превышать лимит
- **Не обрезать текст** — если история 1500 слов, пусть будет хоть 5 сообщений, но полностью
- Ссылки не сокращать (в отличие от брифа, тут это не нужно)

Пример:
```
📖 **English — Приключения в Мидгарде, Сессия 14**

🗣 **Vocabulary**
• **wound** (n) — рана
  > He received a wound that would not heal.
...
```

```
📖 **Story**

Грета стояла на краю ущелья, ветер трепал её рыжие волосы...
... (полный текст, без обрезания)
```

```
📖 **Grammar — Present Perfect vs Past Simple**

**Структура:**
have/has + V3 (ed/неправ.)
...
```

```
📖 **Check**

What did Greta see at the bottom of the ravine?
→ Отвечай на русском!
```

## Команды пользователя

| Команда | Действие |
|---------|----------|
| `/english` | Начать урок (генерация следующей сессии) |
| `/english skip` | Пропустить урок |
| `/english newbook` | Выбрать новую книгу |
| `/english harder` | Повысить уровень (A2 → B1) |
| `/english easier` | Понизить уровень |
| `/english progress` | Показать текущий прогресс |

## CLI скрипт

Скрипт: `~/.hermes/skills/brief/english_lesson.py`

### prepare — получить контекст
```bash
python3 ~/.hermes/skills/brief/english_lesson.py prepare
```
Выводит JSON с полями:
- level, book, book_title, session, total_sessions
- characters, setting, themes, plot_threads (из book.yaml)
- summary (обновлённый сюжет из book.yaml)
- last_session_text (текст последней сессии для связности)
- last_vocab (последние 10 уникальных слов из 3 последних сессий)

### save — сохранить сессию
Поддерживает как строки, так и файлы (пути, начинающиеся с `/`).
```bash
# Строки напрямую
python3 ~/.hermes/skills/brief/english_lesson.py save \
  --text "Story content here" \
  --grammar "## Grammar topic\n\nExplanation..." \
  --vocab "**word** (n) — перевод\n> example" \
  --summary "Краткий сюжет для book.yaml (опционально)"

# Или файлы (надёжнее для длинного контента)
python3 ~/.hermes/skills/brief/english_lesson.py save \
  --text /tmp/text.md \
  --grammar /tmp/grammar.md \
  --vocab /tmp/vocab.md \
  --summary /tmp/summary.txt
```

⚠️ `--summary` обновляет `book.yaml` → summary, что важно для связности сюжета между сессиями.

### new-book — создать новую книгу
```bash
python3 ~/.hermes/skills/brief/english_lesson.py new-book \
  --title "Название" \
  --genre "fantasy" \
  --characters "YAML" \
  --setting "Описание мира" \
  --level A2
```

### status — текущий статус
```bash
python3 ~/.hermes/skills/brief/english_lesson.py status
```

## ⚠️ Pitfalls

### new-book: --characters должен быть валидным YAML
`--characters` парсится через `yaml.safe_load()`. Нужны правильные отступы (2 пробела). В CLI это неудобно — проще создать book.yaml вручную или через write_file.

### save: обновление book.yaml
`--summary` обновляет поле summary в book.yaml. Это **критично** для связности сюжета — prepare использует его как контекст для следующей сессии. Не пропускай этот параметр.

### save: git commit может таймаутиться (10s) — это нормально
При `save` скрипт делает `git commit`. Иногда он таймаутится с ошибкой `Command '['git', ... 'commit' ...]' timed out after 10 seconds`. Это **не фатально** — коммит на самом деле проходит успешно. Проверить: `git log --oneline -1`. Если коммита нет — сделать `git add -A && git commit -m "..." && git push` вручную. В любом случае проверить `git push` — можно не заметить, что изменения не запушились.

### prepare падает с ImportError: cannot import name 'get_vault_path'
`english_lesson.py` импортирует `get_vault_path` из `obsidian_utils`, но в `obsidian_utils.py` этой функции изначально нет. Она нужна в 4 скриптах (english_lesson, brief_evening, brief_evening_fsm). Исправление: добавить `from pathlib import Path` в импорты и функцию `get_vault_path()` → `return Path(VAULT_PATH)`.

⚠ **Процесс:** не патчить молча. Сначала предупредить пользователя о проблеме, предложить план исправления, дождаться одобрения — и только потом фиксить.

### state.yaml: поле session (не chapter)
Скрипт использует `session`, не `chapter`. При ручном редактировании state.yaml не перепутай.
