# Проблема загрузки `.legacy/SKILL.md`

## Симптом
При вызове `/morning` система загрузила `.legacy/SKILL.md` вместо основного `SKILL.md`.
В `.legacy/SKILL.md` остались устаревшие пути: `Дневник/` вместо `Journal/`, `Планирование/` вместо `Projects/Planning/`.

## Причина
В `~/.hermes/skills/productivity/morning-ritual/` существует поддиректория `.legacy/` со своим `SKILL.md`.

## Каноничные пути vault (на 15.06.2026)
- Дневники: `~/hermes-vault/Journal/YYYY-MM-DD.md`
- Планирование: `~/hermes-vault/Projects/Planning/YYYY-MM-DD/`
- Профиль: `~/hermes-vault/Areas/Profile/`
- Привычки: `~/hermes-vault/Areas/Habits/`

## Истина на диске
Перед любой записью в Obsidian: `ls ~/hermes-vault/`. Если папки нет на диске — путь неверный, не важно что говорит память или навык.
