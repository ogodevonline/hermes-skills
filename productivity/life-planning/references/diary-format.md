# Diary Format — Obsidian Dnevnik

## Format 1: Text comments (current, since ~09.05.2026)

Section header: `## 💭 Восемь сфер жизни` (or `## 8 сфер`)

Table without numeric scores:

```
| Сфера | Комментарий |
|-------|-------------|
| 💼 Карьера | Настраивал навыки Hermes, немного поработал |
| ❤️ Лима | Встретил вечером |
| 👨‍👩‍👧 Семья | Созвонился с братом |
| 📚 Развитие | — |
| 💪 Здоровье | Не сходил в зал |
| 🏠 Быт/Финансы | — |
| 🤝 Друзья | — |
| 🎮 Хобби/Отдых | Отдыхал большую часть дня |
```

Parsed by `planning.py` as `comments` dict. No numeric scores available — `sphere_averages` will be empty.

## Format 2: Numeric scores (older format, not in current use)

Table with numeric score column:

```
| 💼 Карьера | 7 | заметки |
```

Parsed as `scores` dict. `sphere_averages` has data when present.

## Format 3: No spheres section at all

Older diaries (before ~09.05) only have reflection section (`## 💭 Рефлексия`) with 5 questions. No sphere tracking. `planning.py` returns empty diaries for these.

## Tasks section in diary

Section header: `## 📋 Задачи`

Contains ✅ (done) and ⏳ (pending) tasks:

```markdown
## 📋 Задачи
✅ [H] [92] 🏠 План покупки квартиры в Узбекистане
⏳ [H] [93] 💰 План перевода денег в Узбекистан
✅ [M] [68] 🤖 Создать ассистента планирования
```

Parsed by `planning.py` as `done_tasks` (lines starting with ✅).

## Habits section in diary

Section header: `## 🔁 Привычки` (or `## Привычки`)

Contains ✅ (done) and ⏳ (pending) habits:

```markdown
## 🔁 Привычки
✅ [ 1] Omega + D3 08:00
⏳ [ 2] Дыхание по Вим Хофу 08:00
✅ [ 4] Цинк + Магний 22:00
```

Parsed by `planning.py` as `done_habits` (lines starting with ✅).

## Reflection section

Section header: `## 💭 Рефлексия`

Five numbered questions in bold:

```markdown
**1. Что сегодня прошло ХОРОШО?**
текст ответа

**2. Где облажался / можно лучше?**
текст ответа
```

Parsed by `planning.py` as `reflections` dict with keys `q1`-`q5`.

---

## Parsing logic in planning.py

```python
in_sphere_section = False
for line in text.splitlines():
    if "Восемь сфер жизни" in line or "8 сфер" in line:
        in_sphere_section = True
        continue
    if in_sphere_section and line.startswith("##"):
        in_sphere_section = False
        continue
    if not in_sphere_section:
        continue

    # Try numeric format first: | emoji Sphere | 7 | ...
    m = re.match(r'\|\s*[💼❤️👨‍👩‍👧📚💪🏠🤝🎮🎯]\s*(.+?)\s*\|\s*(\d+)\s*\|', line)
    if m:
        scores[m.group(1).strip()] = int(m.group(2))
        continue

    # Fallback to text format: | emoji Sphere | text comment |
    m = re.match(r'\|\s*[💼❤️👨‍👩👧📚💪🏠🤝🎮🎯]\s*(.+?)\s*\|\s*(.+?)\s*\|', line)
    if m:
        comments[m.group(1).strip()] = m.group(2).strip()
```

## Emojis used for spheres

| Sphere | Emoji | Key |
|--------|-------|-----|
| Карьера | 💼 | career |
| Лима | ❤️ | lima |
| Семья | 👨‍👩‍👧 | family |
| Развитие | 📚 | development |
| Здоровье | 💪 | health |
| Быт/Финансы | 🏠 | home |
| Друзья | 🤝 | friends |
| Хобби/Отдых | 🎮 | hobbies |

Note: some emojis are multi-codepoint (e.g. 👨‍👩‍👧 = man + ZWJ + woman + ZWJ + girl). The regex `[💼❤️👨‍👩‍👧📚💪🏠🤝🎮🎯]` may match only the first codepoint in some environments — Pandantic about this only matters if the regex fails. If it works, leave it.