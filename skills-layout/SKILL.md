---
name: skills-layout
description: Где лежат навыки владельца и как их ставить, создавать и обновлять (свои Hermes, общие agent-skills, чужие через npx skills, большие наборы в vendor). Использовать перед созданием, установкой, обновлением или удалением любого навыка.
---

# Раскладка навыков (с 23.09.2026)

| Что | Где | Кто меняет |
|---|---|---|
| Навыки ассистента Hermes (брифы, дневник, OLX, дом…) | `~/.hermes/skills` = репо `ogodevonline/hermes-skills` | ты: создавай здесь; коммит и push делает cron ежедневно в 04:30 UTC (~/bin/skills-autocommit.sh, лог ~/logs/skills-autocommit.log), найденный секрет блокирует коммит |
| Общие навыки владельца для всех агентов (код, git, lead-platform, канал, money-suite) | `~/Projects/Personal/GitHub/agent-skills/skills` (подключено через `skills.external_dirs`) | владелец на ноутбуке; здесь только `git pull`, сам не правь без просьбы |
| Чужие навыки | `~/.agents/skills` (подключено через `skills.external_dirs`), список — `agent-skills/third-party.txt` | через `npx skills`, не копией |
| Большие чужие наборы (Show Me The Money) | `~/.agents/vendor/<набор>`, агентам — один указатель (`money-suite`) | `vendor.txt` + `git pull` |
| Встроенные навыки Hermes (builtin) | идут с Hermes | обновляет `hermes update`, не трогать |

## Правила

- Чужой навык не копируй в `~/.hermes/skills` и не ставь через `hermes skills install`:
  его добавляют строкой в `~/Projects/Personal/GitHub/agent-skills/third-party.txt`
  (формат `<github-репо> <навык>…`, меняет владелец в git); на сервере затем
  `NPX_AGENTS=universal ~/Projects/Personal/GitHub/agent-skills/bin/link-skills.sh`.
- Обновить всё: `NPX_AGENTS=universal ~/Projects/Personal/GitHub/agent-skills/bin/skills-update.sh`
  (agent-skills, vendor и чужие). `NPX_AGENTS=universal` обязателен — иначе навыки
  лягут в `~/.claude/skills`, которую Hermes не читает.
- Модули money: читай `~/.agents/vendor/show-me-the-money/skills/<модуль>/SKILL.md`
  по указателю `money-suite`.
- Секреты в навыки не клади; git-доступ к GitHub — через `gh` (токены в URL запрещены).
- Проверка, что видишь: `hermes skills list`.
