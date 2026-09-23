---
name: english
category: productivity
description: "English lessons from YouTube cultivation/manhua videos. /english — continue. /english <url> — start new video."
requires: []
---

# English — Lessons from YouTube (Cultivation / Manhua)

Василий учит английский по реальным YouTube пересказам manhua/cultivation.

## Команды

- `/english` — показать прогресс, предложить продолжить
- `/english <youtube-url>` — начать новый урок из YouTube видео

## Прогресс

Хранится в `~/hermes-vault/Learning/English/<slug>/progress.yaml`.

При `/english` без аргументов:
1. `ls ~/hermes-vault/Learning/English/*/progress.yaml`
2. Найти первый источник с pending сегментом
3. Показать: slug + сегмент N/M
4. Если всё завершено — спросить ссылку

## Зависимости

Скрипты используют `youtube-transcript-api` и `pyyaml`. Установлены в `~/.venv/`:

```bash
uv pip install youtube-transcript-api pyyaml --python ~/.venv/bin/python
```

Все скрипты запускать через `~/.venv/bin/python` (не системный `python3`).

## Получение контента

### YouTube — разбить на сегменты
```bash
~/.venv/bin/python ~/.hermes/scripts/english-segment.py "<url>"
```
Разбивает видео на сегменты по 500-700 слов.
Сегменты сохраняются как `segments/segment-XXX.txt`.

### Взять следующий сегмент
```bash
~/.venv/bin/python ~/.hermes/scripts/english-next-chunk.py <slug>
```
Печатает сырой текст сегмента, помечает in_progress.

### Отметить завершённым
```bash
~/.venv/bin/python ~/.hermes/scripts/english-complete-chunk.py <slug> [N]
```

## Конфигурация

Навык читает `~/hermes-vault/Learning/English/english-config.yaml`.  
Если файла нет — используются значения по умолчанию.

| Параметр | По умолч. | Описание |
|----------|-----------|----------|
| `level` | `a2` | Уровень: a1 / a2 / b1 / b2 |
| `story` | `simplified` | `raw` — оригинал; `annotated` — с подсказками; `simplified` — упрощён до уровня |
| `annotate_all_hard` | `false` | Аннотировать все сложные слова |
| `max_new_words` | `6` | Макс. слов в словаре за урок |
| `vocabulary_source` | `auto` | `auto` — из текста; `manual` — пользователь выбирает |
| `vocabulary_mode` | `mixed` | `english` / `russian` / `mixed` (def + перевод) |
| `lesson_language` | `mixed` | `english` / `russian` / `mixed` |
| `segments_per_lesson` | `2` | Сколько сегментов на урок |
| `vocabulary_first` | `true` | `true` — словарь перед текстом (pre-teaching) |
| `target_words_per_story` | `800` | Целевой объём в словах |

⚠️ **Объём — от `target_words_per_story` слов.** Комбинировать `segments_per_lesson` сегментов для одного урока.

---

## Формат урока — ДВЕ ФАЗЫ

Весь урок делится на **фазу генерации** (один LLM-вызов) и **фазу интерактива** (из файлов, без LLM).

---

## Подготовка: зачистка зависших сегментов

Перед началом урока — проверить `progress.yaml` на сегменты со статусом `in_progress`.
Если такие есть И для них нет папки `lesson-NNN/` — сбросить их в `pending`:

```bash
# Через python-скрипт: прочитать progress.yaml, найти in_progress без lesson, перезаписать
~/.venv/bin/python -c "
import yaml, os
slug = 'youtube-6HE6CQFKIkU'  # заменить на актуальный
path = os.path.expanduser(f'~/hermes-vault/Learning/English/{slug}/progress.yaml')
d = yaml.safe_load(open(path))
for k,v in d['segments'].items():
    if v['status'] == 'in_progress':
        v['status'] = 'pending'
with open(path,'w') as f:
    yaml.dump(d, f, default_flow_style=False, allow_unicode=True)

Если `in_progress`-сегментов нет — пропустить этот шаг.

## Получение сегментов

Взять `segments_per_lesson` (из конфига) сегментов. Вызвать `english-next-chunk.py` **по одному разу на каждый сегмент**:

```bash
~/.venv/bin/python ~/.hermes/scripts/english-next-chunk.py <slug>   # 1-й сегмент
~/.venv/bin/python ~/.hermes/scripts/english-next-chunk.py <slug>   # 2-й сегмент
```

Каждый вызов забирает следующий `pending` сегмент, помечает его `in_progress`, печатает текст.
Собрать весь текст в переменную для генерации.

## Определение номера урока

```bash
ls ~/hermes-vault/Learning/English/<slug>/lesson-*/  | wc -l
```
Если существующих lesson-XXX папок 2 — новый урок будет lesson-003. Итого: `max + 1`, с ведущими нулями (003).

## Проверка повторов слов

Перед генерацией — прочитать `vocabulary.md` всех предыдущих `lesson-NNN/`:
```
cat ~/hermes-vault/Learning/English/<slug>/lesson-*/vocabulary.md
```
Составить список уже выученных слов. Не включать их в новый урок.

### Фаза 1: Генерация (один вызов LLM → сразу сохранение)

После получения текста сегментов — **генерирую ВЕСЬ контент урока одним блоком**:

1. **Vocabulary** — `max_new_words` слов. Для каждого: слово, перевод, English definition + перевод, точная цитата из текста + перевод
2. **Story** — `segments_per_lesson` сегментов. Режим `story: simplified` / `annotated` / `raw` как в конфиге
3. **Quiz** — по каждому слову из vocabulary (3 варианта, правильный отмечен)
4. **Grammar** — одна конструкция из текста: правило + пример + упражнение
5. **Comprehension** — 2 вопроса по сюжету (3 варианта, правильный отмечен)
6. **Translate** — 3 предложения (русская фраза → английский оригинал)

**Сразу сохраняю в lesson-NNN/:**

```
~/hermes-vault/Learning/English/<slug>/lesson-NNN/
  story.md        — полный текст (simplified + original excerpts)
  vocabulary.md   — все слова с переводом, def, примером
  grammar.md      — грамматическая конструкция
  questions.md    — quiz + comprehension + translate (с пометками правильных ответов)
```

**Формат vocabulary.md** (хранит все данные для интерактива):
```markdown
# Lesson NNN — Vocabulary

1. **bounty** — награда, вознаграждение (обычно за поимку/убийство)
   📖 A reward given for capturing or killing someone — награда, выдаваемая за поимку или убийство
   📍 *"There was a bounty on the wolf: 40 gold coins."* — *На волка была назначена награда: 40 золотых монет.*

2. **gratitude** — благодарность
   📖 A feeling of being thankful — чувство благодарности
   📍 *"Hector was full of gratitude."* — *Гектор был полон благодарности.*
   ...
```

**Формат questions.md** (хранит quiz, comp, translate + правильные ответы):
```markdown
# Lesson NNN — Questions & Translations

## Quiz
1. **bounty**
   A) наказание, штраф
   B) награда, вознаграждение ✅
   C) долг, обязанность

2. ...

## Grammar Exercise
(опционально — ответ на упражнение)

## Comprehension
1. **Why did Hector give Jyn the werewolf hide?**
   A) He wanted Jyn to sell it and keep the money
   B) He wanted Jyn to take it to Pioneer Village ✅
   C) He wanted Jyn to wear it as a coat

2. ...

## Translations
1. *Они содрали шкуру альфа-оборотня.* → They carved up the alpha's corpse.
2. ...
3. ...
```

**После сохранения — отмечаю сегменты завершёнными:**
```bash
~/.venv/bin/python ~/.hermes/scripts/english-complete-chunk.py <slug> <N>
~/.venv/bin/python ~/.hermes/scripts/english-complete-chunk.py <slug> <N+1>
```

**Сообщение пользователю:**
> *Урок N сгенерирован и сохранён. Начинаем!*
>
> **1/{max_new_words} {word}**
> 📎 ...

---

### Фаза 2: Интерактив (из файлов, без LLM-генерации)

Все шаги читаются из `lesson-NNN/`. Никаких LLM-вызовов между шагами — только чтение файлов и показ.

**Порядок шагов:**
- `vocabulary_first: true` → **Vocab (по одному) → Story → Quiz → Grammar → Comp → Translate**
- `vocabulary_first: false` → **Story → Vocab → Quiz → Grammar → Comp → Translate**

#### Шаг 1 — Vocabulary (`vocabulary_first: true`)

Читаю `vocabulary.md`. Показываю по одному слову за раз. Одно сообщение = одно слово:

**{N}/{max_new_words} {word}**
📎 *{русский перевод}*
📖 *{English definition}* — *{русский перевод определения}*
📍 *"{точная цитата из текста}"* — *{русский перевод примера}*

После ответа пользователя — следующее слово (2/6, 3/6...).

**Закончить после последнего слова:** `All words done. Now read the story. Say 'ready' when done.`

#### Шаг 2 — Story

Читаю `story.md`. Показываю текст.

**⚠️ Story может быть длинной (1500+ слов). Разбивать на несколько сообщений по ~3500 символов.**
По одной части за сообщение. После каждой части — краткий разделитель (например, `— Часть 1/2 —`). Не ждать ответа между частями — отправить все части подряд.

- **`story: raw`**: RAW текст из транскрипта — ни слова не менять.
- **`story: annotated`**: оригинальный текст со сложными словами **жирным** + перевод в скобках.
- **`story: simplified`**: переписан простыми словами + 3-5 оригинальных предложений для сравнения.

**Закончить:** `Read the story. Say 'ready' when done.`

#### Шаг 3 — Vocabulary Quiz

Читаю `questions.md` → секция `## Quiz`. По каждому слову — один вопрос.

**ВАЖНО: При показе вопроса — НЕ показывать ✅. Убирать все пометки правильного ответа. Варианты выглядят одинаково.**

Формат:
**🎯 {word}**
*Choose the correct definition:*
A) {вариант 1}
B) {вариант 2}
C) {вариант 3}

После ответа пользователя:
- Если правильно: `✅ Correct!` + сразу следующий
- Если неправильно: `❌ Not quite — the answer is B: {English definition}.` + сразу следующий

#### Шаг 4 — Grammar

Читаю `grammar.md`. Одна конструкция:

**📌 Grammar Point — {topic}**
*Rule (1-2 sentences)*

From the story:
- *"{example from text}"*

**Your turn:** {exercise}

#### Шаг 5 — Comprehension

Читаю `questions.md` → секция `## Comprehension`. Два вопроса по одному.

**📖 Comprehension — Question {N}**
*{Question in English}*
A) {option}
B) {option}
C) {option}

После ответа: `✅ Correct!` или explanation с отсылкой к тексту. Сразу следующий.

#### Шаг 6 — Translate

Читаю `questions.md` → секция `## Translations`. Три предложения по одному.

**📖 Translate — Sentence {N}**
*{Russian phrase}*

После ответа: `✅ Correct!` или коррекция.

---

### Финал

После Translate-3:
> 🎉 **Lesson NNN complete!**
>
> | Пункт | Результат |
> |-------|-----------|
> | ✅ Словарь | N слов — все усвоены |
> | ✅ Story | Упрощённый текст + оригинал |
> | ✅ Quiz | N/N |
> | ✅ Grammar | {topic} |
> | ✅ Comprehension | N/2 |
> | ✅ Translate | N/3 |
>
> **Прогресс:** X/Y сегментов ✅
>
> Следующий раз — `/english` продолжим.

---

## Структура lesson-NNN/

```
~/hermes-vault/Learning/English/<slug>/lesson-NNN/
  story.md        — полный текст урока
  vocabulary.md   — слова с def + примером (для интерактива vocab + quiz)
  grammar.md      — грамматическая конструкция
  questions.md    — quiz + comprehension + translate (с ответами)
```

Все файлы с YAML frontmatter (node_type: note, status: active, tags: [english, lesson]).

---

## Проверки

1. **Объём:** от `target_words_per_story` слов — проверить через `wc -w`
2. **Повторы слов:** выполнена на этапе подготовки (см. выше)
3. **Факты из текста:** каждый вопрос/перевод — точная опора в тексте
4. **Цитаты точные:** примеры — точные цитаты из сегментов
5. **Русский:** аннотации story + переводы слов и примеров в vocabulary

## Чтение новелл на английском (подбор + проверка уровня)

Когда Василий просит «найди китайскую/азиатскую новеллу, которую я смогу читать на английском» — это **НЕ** ranobe-download (тот про русские переводы). Это режим english: подбор по сложности языка + честная проверка уровня ПЕРЕД рекомендацией (он сам говорит «не всегда уверен в уровне»).

### Протокол проверки уровня
1. Взять РЕАЛЬНУЮ (не адаптированную) 1-ю главу: `web-tools extract https://readnovelfull.com/<novel-slug>/chapter-1-<chapter-slug>.html` (паттерн URL: readnovelfull.com/<novel>/chapter-N-<title>.html)
2. Дать отрывок ~250-300 слов + 4-5 вопросов на понимание (можно отвечать по-русски)
3. Попросить отметить незнакомые слова + оценить % понимания
4. По ответам определить ярус сложности (таблица: `references/chinese-novels-english.md`)
5. Сомневается / A2-B1 → зелёный ярус. Никогда не давать красный сразу.

### Скачивание EPUB (после выбора новеллы)
- Готовые EPUB английских переводов: **GitHub chazzam/wordpress-epub** — `https://github.com/chazzam/wordpress-epub/raw/master/epubs/<Novel-Name>.epub` (рабочий пример: Tales-of-Demons-and-Gods.epub, 253 главы, 1.2 МБ). Подробности и проверка файла: `references/chinese-novels-english.md`.
- Доставка: sendDocument с MIME `application/epub+zip` (НЕ MEDIA), навык telegram-file-delivery.

### Формат чтения (Android)
- У Василия Android: читалка **ReadEra** или Moon+ Reader, тап по слову = перевод.
- ⚠️ НЕ предлагать выписывать незнакомые слова агенту («дорого по времени») — тап-перевод в читалке. Интерактивный vocab-разбор — только для уроков /english, не для новелл.

### Замер уровня (08.2026)
- Реальный уровень чтения: **B1 → тянет к B2** (A2 в конфиге занижен). Слабое место — идиомы (conveying, took delight in, ingrained, inferior). Подбор: 🟡 Tales of Demons and Gods (короткие главы) или 🟢 King's Avatar.

### Ярусы сложности (кратко)
- 🟢 Лёгкий (A2-B1): The King's Avatar, Release That Witch, Coiling Dragon, Bringing the Nation's Husband Home
- 🟡 Средний (B1-B2): Tales of Demons and Gods, A Will Eternal, 1/2 Prince, I Shall Seal the Heavens
- 🔴 Сложный (C1+): Lord of the Mysteries, Reverend Insanity

Полный список (главы, жанры, источники): `references/chinese-novels-english.md`

## Скрипты

| Скрипт | Назначение | Запуск |
|--------|-----------|--------|
| `english-segment.py <url>` | Разбить YouTube на сегменты 500-700 слов | `~/.venv/bin/python` |
| `english-next-chunk.py <slug>` | Взять следующий сегмент | `~/.venv/bin/python` |
| `english-complete-chunk.py <slug> [N]` | Отметить сегмент завершённым | `~/.venv/bin/python` |
