# Gotham Nightly Repair Pipeline

Интеграция gitmark lint + frontmatter repair + stale check + Telegram delivery в единый no_agent cron-скрипт.

## Архитектура

```
cron (00:00 MSK) → gotham-nightly-with-telegram.sh (no_agent=true)
  ├── 1. gitmark.py lint --strict          — онтология, сироты, README, frontmatter
  ├── 2. gotham-ensure-frontmatter.py      — чинит отсутствующий frontmatter (если ERR)
  ├── 3. gotham-stale-status.py            — archived для >90d без обновлений
  ├── 4. git add + commit + push           — фиксы в vault
  └── 5. Python → Telegram Bot API         — sendDocument отчёта файлом
```

## Скрипт

`~/.hermes/scripts/gotham-nightly-with-telegram.sh`

## Ключевые решения

### no_agent=true — почему
- Без LLM — 0 токенов на каждый запуск
- Скрипт сам пишет отчёт в vault и шлёт файл через Telegram API
- stdout не используется для доставки — только для логирования ошибок

### Telegram file delivery без MEDIA
- `MEDIA:/path` не работает с `no_agent=true` (stdout идёт как текст)
- Решение: Python heredoc внутри bash-скрипта, прямой вызов `api.telegram.org/bot{token}/sendDocument`
- Таймаут 60 сек — Telegram API бывает медленным

### Чтение TELEGRAM_BOT_TOKEN из .env
- Токен имеет формат `8720033011:***` (литеральные `***` в .env файле)
- ❌ **Никогда `source .env`** — bash делает glob expansion на `***`, ломает строку
- ✅ **Python читает файл построчно** — `startswith('TELEGRAM_BOT_TOKEN=')` + `split('=',1)`

## Критический pitfall: `git commit || true` молча глотает отказ pre-commit hook (2026-09-04)

Vault имеет pre-commit hook, который гоняет `gitmark lint --strict` и режет коммит при ЛЮБОЙ ERR (G01/G02/G05/G06).

Старая версия nightly-скрипта делала `git commit ... || true` → при ERR коммит отклонялся, ошибка глоталась, в отчёт писалась ложная строка «fixes committed». Результат: с 31.08 по 04.09.2026 **ни один коммит не прошёл**, отчёты/журналы копились staged (`git status` → `A`). Внешне джоба выглядела работающей (статус ok, файл в Telegram уходит).

**Диагностика «джоба ничего не меняет»:**
1. `git log --oneline -3` в vault — если последний коммит старый, а файлы новые → коммиты падают
2. `git status --short | grep -c '^A'` — staged-мусор = git add проходит, commit нет
3. Проверить сам коммит: `git commit` без `|| true`, посмотреть вывод hook

**Исправление (в скрипте):**
- после repair — повторный `lint --strict` в переменную POST_CLEAN (по exit code, НЕ по grep 'ERR' — grep ловит «0 ERR» из summary!)
- коммитить только при POST_CLEAN=1, иначе писать в отчёт честный COMMIT FAILED
- весь отчёт (включая Result и подпись) писать ДО `git add`/`commit`, иначе хвост вечно висит модификацией после коммита
- подпись отчёта `_Report auto-generated` — до git add, не после

## TZ-баг: bash и Python в одном скрипте расходятся по дате (2026-09-04)

Bash писал отчёт с `TZ=Europe/Moscow date` (report-YYYY-MM-DD.md), а Python-heredoc отправки использовал `datetime.now()` без TZ = серверное UTC. В 00:00 МСК это ВЧЕРАШНИЙ день по UTC → в Telegram уходил вчерашний отчёт, сегодняшний (bash) оставался в vault.

**Фикс:** в Python-части `datetime.now(timezone(timedelta(hours=3)))`. Общее правило: в одном скрипте дата файла и дата отправки должны браться из ОДНОГО источника TZ.

## Авто-фикс G06/links вручную (что ensure не чинит)

ensure-frontmatter чинит только frontmatter, НЕ битые links (G06). Типовые G06 и фиксы:
- lowercase `journal/README.md` в `links.parent` — файл `Journal/README.md` (регистр! Linux case-sensitive) → заменить на `./README.md` (как у остальных journal)
- `part_of` → несуществующий README.md курса/урока → создать README курса (node_type: index) или переписать ссылку на существующий файл
- fallback по base-name в resolve_link: `index.md` может «случайно» резолвиться на чужой `Areas/Profile/index.md` (единственный с таким именем) — линтер молчит, связь мусорная

После правок: `lint --strict` → 0 ERR, затем commit проходит.

## Авто-фикс node_type в существующем frontmatter (с 2026-09-04)

`gotham-ensure-frontmatter.py --mode=add-missing` теперь не только создаёт frontmatter с нуля, но и: добавляет недостающий `node_type` в существующий frontmatter; заменяет невалидный (`contact`→`person`, `reference`→`learning`) по guess из папки. Полный прогон: `--all --mode=add-missing --vault /home/hermes/hermes-vault`. Одиночный `--path` без `--vault` даёт неверный guess (`note`).

### Pitfall: замена невалидного node_type = замена строки, НЕ вставка новой (2026-09-04)

При невалидном `node_type: contact` наивная инъекция добавляла ВТОРУЮ строку `node_type: person` ПЕРЕД старой — получался двойной ключ, и YAML берёт последнее значение (`contact` оставался действующим). Обнаружено по `grep -c '^node_type:'` → 2 в починенных файлах (лима.md, Colloquium/*).

**Правило:** в `add_missing_frontmatter` две разные ветки —
- ключа нет вовсе → `_inject_missing_keys` (вставить node_type после открывающего `---`),
- ключ есть, но невалиден → `_replace_node_type_value` (заменить значение в существующей строке `node_type: X` на правильное).

После любого прогона проверять дубли: `for f in $(git diff --name-only | grep '\.md$'); do grep -c '^node_type:' "$f"; done`.

### FOLDER_GUESS_RULES: добавлять и латиницу, и кириллицу (2026-09-04)

Правило было только `/Areas/Contacts/люди/` (кириллица), а реальная папка — `people/` (латиница) → лима.md не получала guess `person` и уходила в fallback `note`. Онтология (01-Ontology.md) указывает канонический путь — сверяй правила с ним. Добавлено `/Areas/Contacts/people/` → person.\n\n### Паттерн parallel delegate_task для vault\n\n```python\n# В контексте каждой задачи обязательно:\ncontext = \"\"\"\nVault: /home/hermes/hermes-vault/\nWorking dir: /home/hermes/hermes-vault/\nAGENTS.md frontmatter rules: node_type, status, created, updated\nLinks format — ТОЛЬКО многострочный:\n  links:\n    parent:\n      - ./README.md\n  (НЕ links: {parent: [val]} — не распознаётся)\n\nДля agent-memory: links: {parent: [./README.md], created_by: [person/василий.md]}\nДля Journal: links: {parent: [./README.md]}\nДля Learning sessions: links: {parent: [./README.md]}\n\"\"\"\n\ngoal = \"\"\"\nProcess each session dir:\n1. Create README.md with node_type: index\n2. Add parent links to all .md files in dir\nUse patch() for links. Use write_file() for READMEs.\nCommit after all edits.\n\"\"\"\n```\n\n### Порядок обхода (проверено 12.06.2026)\n\n| Приоритет | Группа | Файлов | Что делать |\n|-----------|--------|--------|------------|\n| 1 | Journal/ (дневники) | ~48 | README + parent links |\n| 2 | Learning/ книги (003, 004) | ~200 | 14-34 README на сессию + parent links |\n| 3 | Остальные Learning/ | ~25 | README + parent links |\n| 4 | Areas/ + root | ~30 | README для контактов, профилей + parent links |\n| 5 | System/AgentsData/ + Projects/ | ~50 | README для каждого агента + parent + created_by |\n\nЗапускать по 3 параллели (max_concurrent_children=3).\n\n### После всех правок\n\n```bash\n# Переиндексация (обязательно!)\npython3 ~/.hermes/scripts/gitmark.py index --force\n\n# Финальная проверка\npython3 ~/.hermes/scripts/gitmark.py lint --strict\n\n# Ожидаемый результат: 0 ERR · 0 WARN\n```\n\n### Пример стоимости (реальные цифры 12.06.2026)\n\n- 7 параллельных задач\n- ~3.8M input tokens, ~87K output tokens\n- deepseek/deepseek-v4-flash:discounted через KiloCode — ~$0.5-1\n- Общее время: ~12 минут

### YAML-формат links (критично!)\n\n**Важно:** gitmark использует stdlib-парсер YAML (строка 333 в gitmark.py). После патча июня 2026: парсер корректно обрабатывает вложенные структуры под `links:`.\n\nInline-формат НЕ распознаётся:\n```yaml\n# ❌ Не будет найден как typed link\nlinks:\n  parent: [./README.md]\n```\n\n**Только многострочный:**\n```yaml\n# ✅ Распознаётся\nlinks:\n  parent:\n    - ./README.md\n```\n\nЕсли патчишь парсер — проверь 4 тест-кейса:\n1. Многострочный с одним ключом (`parent: - val` под links)\n2. Inline в старом формате (`parent: [val]` под links) — должен упасть в dict, а не top-level\n3. Два ключа под links (`parent: + created_by:`)\n4. Файл без links — `fm.get('links')` = None, `not links` = True (корректный I3)

## Проверка работоспособности

```bash
# Ручной запуск
cd ~/hermes-vault && bash ~/.hermes/scripts/gotham-nightly-with-telegram.sh

# Проверить что файл ушёл в Telegram
# В ответе от API: Status: 200, result.message_id

# Проверить отчёт в vault
ls -la "System/Gotham/report-$(TZ=Europe/Moscow date +%Y-%m-%d).md"
```

## Файлы скриптов

| Файл | Путь |
|------|------|
| gitmark.py | `~/.hermes/scripts/gitmark.py` |
| gotham-ensure-frontmatter.py | `/home/hermes/scripts/gotham-ensure-frontmatter.py` |
| gotham-stale-status.py | `/home/hermes/scripts/gotham-stale-status.py` |
| gotham-nightly-with-telegram.sh | `~/.hermes/scripts/gotham-nightly-with-telegram.sh` |

## Cronjob

- ID: `d59980a11310`
- Расписание: `0 0 * * *` (каждый день в 00:00 МСК)
- Тип: `no_agent=true`
- Скрипт: `gotham-nightly-with-telegram.sh`
