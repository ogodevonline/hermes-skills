# Gotham Scripts — точные пути

Скрипты разбросаны по двум директориям. Всегда используй абсолютные пути — tilde (`~`) не раскрывается в terminal() у subagent-воркеров.

## Исполняемые скрипты

| Скрипт | Путь | Назначение |
|--------|------|-----------|
| `gitmark.py` | `/home/hermes/.hermes/scripts/gitmark.py` | Lint, валидация, --strict |
| `gotham-ensure-frontmatter.py` | `/home/hermes/scripts/gotham-ensure-frontmatter.py` | Добавление/валидация frontmatter |
| `gotham-stale-status.py` | `/home/hermes/scripts/gotham-stale-status.py` | Архивация stale-заметок |
| `gotham-nightly.sh` | `/home/hermes/.hermes/scripts/gotham-nightly.sh` | Nightly cron repair |

## Pitfall: не используй единый SCRIPTDIR

Первая версия nightly-скрипта использовала `SCRIPTDIR=/home/hermes/scripts` — gitmark.py по этому пути НЕ НАШЁЛСЯ (он в `~/.hermes/scripts/`).

**Правильный паттерн:** задавай каждому скрипту отдельную переменную с абсолютным путём:
```bash
GITMARK=/home/hermes/.hermes/scripts/gitmark.py
ENSURE=/home/hermes/scripts/gotham-ensure-frontmatter.py
STALE=/home/hermes/scripts/gotham-stale-status.py
```

## Pre-commit hook

`/home/hermes/hermes-vault/.git/hooks/pre-commit` — запускает `gitmark.py lint --strict`.
Блокирует коммиты при ERR-нарушениях (G01, G02, G05, G06).
