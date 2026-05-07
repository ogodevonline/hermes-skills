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
2. **Story** — 400-600 слов, захватывающий сюжет (экшн, эмоции, повороты). Пользователь предпочитает длинные развёрнутые истории.
3. **Grammar & Usage** — одна конструкция из текста с разбором: структура, примеры, таблица
4. **Check** — 1 вопрос по тексту на английском

## Vocabulary Quiz (follow-up)

Если пользователь после урока просит «научить словам» или хочет закрепить вокабуляр — провести **3-раундовую викторину** по новым словам из урока (и/или словам, которые пользователь сам отметил как незнакомые):

**Раунд 1 — Match:** сопоставить слово с переводом/определением
```
1. suspicion → a) подозрение
2. blinked  → b) мерцать
```
Пользователь пишет: `1→a, 2→b`

**Раунд 2 — Fill the gap:** вставить слово в предложение
```
The cat's eyes ________ in the dark. (blinked)
```

**Раунд 3 — Translate:** перевести предложения с русского на английский
```
Он посмотрел на меня с подозрением.
→ He looked at me with suspicion.
```

**Формат разбора слов:**
Каждое слово, которое пользователь отметил как новое, разобрать подробно:
- Перевод, транскрипция (IPA)
- Пример из текста урока
- Словосочетания и идиомы с этим словом
- Разница с похожими словами (например, stair vs staircase vs ladder)
- Распространённые ошибки

После каждого раунда — обратная связь: ✅/❌ с пояснением ошибок.
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
3. После выбора — создать книгу **вручную** (CLI-команда `new-book` неудобна, см. pitfalls):

```bash
mkdir -p "Английский/Книга-NNN-slug/session-001"
```
4. Написать `book.yaml` (см. шаблон выше). **Важно:** поля `setting` и `summary` оборачивать в двойные кавычки, если содержат `:` или `—`.
5. Обновить `state.yaml`:
   - `book: Книга-NNN-slug`
   - `session: 0`
   - `total_sessions: 0`
   - `sessions_today: 0`
6. Закоммитить: `git add -A && git commit -m "english: new book — Название" && git push`

## Отправка в Telegram

При отправке результата урока в Telegram (после генерации):
- **Предпочтительный способ:** `python3 english_lesson.py save ... --send` — скрипт сам сохраняет и отправляет  
- **Скрипт отправки:** `~/.hermes/scripts/telegram_send_lesson.py` — разбивает контент на чанки (3500 символов) и отправляет с `parse_mode=Markdown`  
- **Важно:** `parse_mode=Markdown` обязателен, иначе разметка (жирный, код, списки) не отображается  
- **Разбивать на чанки** — каждое сообщение не больше **3500 символов** (запас под Markdown)
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

### save — сохранить сессию (и опционально отправить в Telegram)
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

# С отправкой в Telegram (после сохранения)
python3 ~/.hermes/skills/brief/english_lesson.py save \
  --text /tmp/text.md \
  --grammar /tmp/grammar.md \
  --vocab /tmp/vocab.md \
  --summary /tmp/summary.txt \
  --send
```

⚠️ `--summary` обновляет `book.yaml` → summary, что критично для связности сюжета между сессиями.
⚠️ `--send` отправляет урок в Telegram через `~/.hermes/scripts/telegram_send_lesson.py` с `parse_mode=Markdown`.

### new-book — создать новую книгу (⚠️ ограничен)
```bash
python3 ~/.hermes/skills/brief/english_lesson.py new-book \
  --title "Название" \
  --characters "YAML" \
  --setting "Описание мира" \
  --level A2
```

**⚠️ CLI не поддерживает:**
- `--genre` (флага нет — игнорируется)
- Пробелы/слеши в значениях (аргументы с `/`, кавычки внутри ломают argparse)
- Сложный YAML в `--characters` (правильные отступы в CLI не передать)

**Рекомендация:** создавать книгу вручную (см. раздел «Выбор новой книги»).

### status — текущий статус
```bash
python3 ~/.hermes/skills/brief/english_lesson.py status
```

## 🔴 КРИТИЧЕСКОЕ ПРАВИЛО: книги БЕСКОНЕЧНЫ

English-книги рассчитаны на **бесконечное продолжение**. Пользователь ожидает сериал, который можно продолжать вечно.

## 🔴 КРИТИЧЕСКОЕ ПРАВИЛО: книги БЕСКОНЕЧНЫ

English-книги рассчитаны на **бесконечное продолжение**. Каждая сессия — эпизод сериала, который не заканчивается.

### Что НЕЛЬЗЯ делать

- ❌ **Никогда не писать "The End", "Конец книги", финальную сцену**
- ❌ **Никогда не переводить ВСЕ plot_threads в "resolved"** — всегда оставлять активные. Старые разрешились → открывай новые
- ❌ **Не завершать арки всех персонажей сразу**
- ❌ **Не ставить точку — ставь многоточие**

### Что делать

- ✅ Каждая сессия заканчивается **открытым финалом / клиффхэнгером**
- ✅ В конце текста: `**To be continued...**`
- ✅ В `book.yaml`: всегда ≥1 active plot_thread. Если старый закрыт — сразу добавь новый
- ✅ В `summary`: формулировки "это только начало", "впереди новая тайна", "герои сталкиваются с..."

### Аварийный протокол (если случайно завершил книгу)

1. Откатить `book.yaml`: вернуть plot_threads в `active`, убрать "завершено" из summary
2. Переписать `session-NNN/text.md`: вырезать "The End", заменить на открытый конец
3. Добавить новый plot_thread
4. Закоммитить: `english: fix — removed book ending, story is ongoing`

## ⚠️ Pitfalls

### book.yaml: поля с `:` и специальными символами ломают YAML
Если `setting` или `summary` содержат двоеточие с пробелом (`: `), em-dash (`—`), или знак равенства (`=`), YAML-парсер падает с `mapping values are not allowed here`. **Всегда** оборачивать такие поля в двойные кавычки:

```yaml
# ❌ ломается
summary: Его соседи по камере: маг стихий...

# ✅ работает
summary: "Его соседи по камере: маг стихий..."
```

### book.yaml: после создания проверять YAML-валидность
После создания/редактирования book.yaml вручную — проверить, что YAML парсится:
```bash
python3 -c "import yaml; yaml.safe_load(open('Английский/Книга-NNN-slug/book.yaml')); print('OK')"
```
Если ошибка — скорее всего незакавыченное `:` или спецсимволы в `setting`/`summary`.

### save: обновление book.yaml
`--summary` обновляет поле summary в book.yaml. Это **критично** для связности сюжета — prepare использует его как контекст для следующей сессии. Не пропускай этот параметр.

### save: git commit может таймаутиться (10s) — это нормально
При `save` скрипт делает `git commit`. Иногда он таймаутится с ошибкой `Command '['git', ... 'commit' ...]' timed out after 10 seconds`. Это **не фатально** — коммит на самом деле проходит успешно. Проверить: `git log --oneline -1`. Если коммита нет — сделать `git add -A && git commit -m "..." && git push` вручную. В любом случае проверить `git push` — можно не заметить, что изменения не запушились.

### prepare падает с ImportError: cannot import name 'get_vault_path'
`english_lesson.py` импортирует `get_vault_path` из `obsidian_utils`, но в `obsidian_utils.py` этой функции изначально нет. Она нужна в 4 скриптах (english_lesson, brief_evening, brief_evening_fsm). Исправление: добавить `from pathlib import Path` в импорты и функцию `get_vault_path()` → `return Path(VAULT_PATH)`.

⚠ **Процесс:** не патчить молча. Сначала предупредить пользователя о проблеме, предложить план исправления, дождаться одобрения — и только потом фиксить.

### state.yaml: поле session (не chapter)
Скрипт использует `session`, не `chapter`. При ручном редактировании state.yaml не перепутай.
