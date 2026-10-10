---
name: vault-git-workflow
category: productivity
description: "Use when committing/pushing the git-backed vault."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
tags: [vault, git, obsidian]
metadata:
  hermes:
    tags: [vault, git, obsidian]
    related_skills: [vault-frontmatter, vault-structure]
---

# Git-гигиена при записи в vault

Дополняет `vault-frontmatter` (тот владеет правилами frontmatter). Здесь — только доведение записи до запушенного коммита: хук линтит ВЕСЬ vault, индекс общий с другими агентами, push имеет свои грабли.

## When to Use

- Любая запись в `~/hermes-vault/` (заметка, карточка, календарь, дайджест), которую надо зафиксировать в git.
- «Записал, но не залилось» / push падает с ошибкой авторизации или non-fast-forward.

## Порядок

```bash
cd ~/hermes-vault
# 1) файл уже написан; frontmatter проверен скриптом навыка vault-frontmatter

# 2) коммит только своих путей (в индексе могут лежать staged-файлы других агентов)
git add <мой/файл> [<ещё один>]
git commit -m "<scope>: <что сделано>" -- <мой/файл> [<ещё один>]

# 3) push: GH_TOKEN из окружения может быть невалидным — тогда git-хелпер gh падает
#    «Invalid username or token», хотя `gh auth status` показывает живой аккаунт
env -u GH_TOKEN git push

# 4) если remote ушёл вперёд — rebase с автостешем (обычный --rebase ругается на чужой индекс)
env -u GH_TOKEN git pull --rebase --autostash
env -u GH_TOKEN git push

# 5) ПРОВЕРКА, что запись дошла
git status -sb   # '## main...origin/main' без [ahead N] = залито
```

## Pitfalls

- **Коммит удался ≠ запушен.** `git status -sb` показывает `ahead N` — значит push не прошёл; не докладывать «записал и запушил» до проверки.
- **Хук линтит весь vault, а не твой файл.** Чужие ERR (например Journal-файлы без frontmatter) блокируют твой коммит. Порядок: прогнать `gotham-ensure-frontmatter.py --mode=add-missing` по каждому ERR-файлу (контент не трогает) → коммитить со pathspec. `--no-verify` только если его прямо предписывает рецепт конкретного навыка (карточки/циклы).
- **`--no-verify` не освобождает от frontmatter.** Хук обходится, но невалидный файл останется невалидным и сломает следующий коммит другого агента.
- **Общий индекс.** В vault параллельно пишут cron/агенты; `git add -A` утащит чужие файлы в твой коммит — всегда pathspec, а для rebase — `--autostash`.
- **Невалидный `GH_TOKEN` в окружении важнее живого gh-логина.** Лечится только `env -u GH_TOKEN` на конкретную команду; не переписывать .env и не просить новый токен.
- **Секреты (пароли прокси, ключи) в заметку — только при приватном remote.** Проверить: `curl -s -o /dev/null -w "%{http_code}" https://github.com/<owner>/<repo>` → 404 = приватный, 200 = публичный (тогда хранить только всё, кроме секрета).
