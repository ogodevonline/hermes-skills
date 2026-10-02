---
name: vault-structure
category: productivity
description: "Единый справочник по структуре Obsidian vault: куда какой агент/навык пишет, canonical пути. Journal/ — каноничный путь для дневников."
---

# Vault Structure — canonical save paths

> **Загрузи этот навык, если твоя задача пишет в `/home/hermes/hermes-vault/`.**
> Определяет единый источник правды: куда сохранять результат, какой node_type ставить, какой паттерн имён.

## ⚠️ Жёсткое правило

**Все записи — только в `~/hermes-vault/`. Никогда в `~/obsidian/`** (симлинк без гита).

Перед записью проверь: `ls ~/hermes-vault/Journal/` — если папка есть, vault существует.

---

## 1. Дневники (утро + вечер)

| Назначение | Путь | node_type |
|---|---|---|
| Утренний ритуал | `Journal/{YYYY-MM-DD}.md` → секция `## ☀️ Утренний ритуал` | journal |
| Вечерний дневник | `Journal/{YYYY-MM-DD}.md` → секция `# 📖 Вечерний дневник` | journal |
| Решённые планы | `Journal/{YYYY-MM-DD}.md` → секция `## 📝 Решённые планы` | journal |

**Единая директория:** `Journal/` (англ) — каноничный путь для всех дневниковых записей.
- `Дневник/` (рус) — удалён. Все файлы перенесены в `Journal/`.

**Использовать `write_section("Journal/{TODAY}.md", "## ☀️ Утренний ритуал", content)`** — секции не перезаписывают друг друга.

---

## 2. Агенты (agents-data)

Каждый агент пишет в `agents-data/<AgentName>/`. Список всех путей:

| Агент (profile) | Путь в vault | node_type |
|---|---|---|
| Worker | `agents-data/Worker/` | agent-memory |
| Architect | `agents-data/Architect/` | agent-memory |
| Coder | `agents-data/Coder/` | agent-memory |
| Debugger | `agents-data/Debugger/` | agent-memory |
| Researcher | `agents-data/Researcher/` | agent-memory |
| Reviewer | `agents-data/Reviewer/` | agent-memory |
| Orchestrator | `agents-data/Orchestrator/` | agent-memory |
| Coach | `agents-data/Coach/` | agent-memory |
| Scout | `agents-data/Scout/` | agent-memory |
| Realtor | `agents-data/Realtor/` | agent-memory |
| SkillWriter | `agents-data/SkillWriter/` | agent-memory |
| SkillImprover | `agents-data/SkillImprover/` | agent-memory |
| SelfImprover | `agents-data/SelfImprover/` | agent-memory |
| RefactoringGuru | `agents-data/RefactoringGuru/` | agent-memory |
| Explorer | `agents-data/Explorer/` | agent-memory |
| Learning | `agents-data/Learning/` | agent-memory |
| PromptEngineer | `agents-data/PromptEngineer/` | agent-memory |

**Формат имени файла:** `YYYY-MM-DD-<kebab-topic>.md`
**Способ сохранения:** `python3 ~/.hermes/scripts/obsidian_save.py <AgentName> - <<'EOF'`

---

## 3. Planning (долгосрочное)

| Назначение | Путь |
|---|---|
| Долгосрочные планы | `Projects/Planning/{YYYY-MM-DD}/` |

**Паттерн имён** (проверить `ls ~/hermes-vault/Projects/Planning/` перед созданием):
- `10-лет.md` — десятилетний горизонт
- `5-лет.md` — пятилетка
- `год-2026.md` — на год
- `месяц-май-2026.md` — на месяц
- `2-мес-май-июнь.md` — двухмесячный
- `3-мес-Q2.md` — квартальный
- `review.md` — ревью по периоду

**node_type:** `plan`
**Проверка:** `ls ~/hermes-vault/Projects/Planning/` перед созданием — следуй существующему паттерну.

---

## 4. Learning

| Назначение | Путь | node_type |
|---|---|---|
| Английский (книги) | `Learning/English/Книга-NNN-{slug}/` | note (сессии) / book (книга) |
| IELTS | `Learning/IELTS/` | learning |
| Python / CS | `Learning/Python/` | learning |
| Million Steps | `Learning/Million-Steps/` | learning |
| Уроки (скриптовые) | `Learning/English/lessons/{topic}.md` | note |

**YAML-файлы метаданных:** `book.yaml`, `state.yaml`, `session.yaml` — не индексируются gms (.md only), содержат данные обучения.

---

## 5. Contacts

| Назначение | Путь | node_type |
|---|---|---|
| Люди | `Areas/Contacts/people/{name}.md` | person |

Каждый `.md` файл — карточка человека.

---

## 6. User Profile

| Назначение | Путь | node_type |
|---|---|---|
| Карточка | `Areas/Profile/index.md` | profile |
| Tech-stack | `Areas/Profile/tech-stack.md` | profile |
| Опыт (14 проектов) | `Areas/Profile/experience/_index.md` | profile |

---

## 7. Self-improvements (анализ сессий)

| Назначение | Путь | node_type |
|---|---|---|
| Анализ неудач | `self-improvements/{YYYY-MM-DD}-{topic}.md` | reflection |

Self-improver и Skill-improver сохраняют планы сюда.

---

## 8. System

| Назначение | Путь | node_type |
|---|---|---|
| Онтология, spec Gotham (архив, только чтение) | `Archive/Agents/Gotham/` | system-note |
| AGENTS.md (правила frontmatter) | `AGENTS.md` (корень vault) | system-note |
| Home.md (стартовая) | `Home.md` (корень vault) | index |

---

## 9. Остальное

| Назначение | Путь | node_type |
|---|---|---|
| Inbox (быстрые заметки) | `Inbox/` | note |
| Archive (старые/закрытые) | `Archive/` | archive |
| Journal (дневники) | `Journal/` — каноничный путь | journal |
| Habits | `Areas/Habits/` | note |

---

## 10. Скрипты для сохранения

- **obsidian_save.py** — `python3 ~/.hermes/scripts/obsidian_save.py <Agent> -` — сохраняет в `agents-data/<Agent>/`, git add+commit+push
- **obsidian_utils** — `from obsidian_utils import write_section, commit_all, get_vault_path` — для write_section (дневники)
- **vault-frontmatter skill** — загрузить перед любым write_file в vault (правила frontmatter + node_type table + валидация)

---

## 11. Self-check перед записью

Перед любым write_file в vault:

0. **Загрузи vault-structure skill** — `skill_view('vault-structure')`. Единый источник правды по путям. Без него ты будешь гадать или использовать устаревшие пути из памяти.
1. Путь — `~/hermes-vault/`, не `~/obsidian/`?
2. Директория существует? `ls ~/hermes-vault/Journal/`
3. Какой node_type у файла? (см. vault-frontmatter)
4. Есть ли frontmatter? (YAML: node_type, status, created, updated)
5. Не дублируешь ли секцию? (write_section заменяет по точному заголовку)
6. Паттерн имён существует? (для Projects/Planning/ — `ls` перед созданием)

---

## 12. Critical: Comprehensive path migration rule

Когда vault-папки переименовываются (русские названия → английские или любые другие):

**НЕЛЬЗЯ** исправлять только то, о чём явно спросил пользователь. Нужно найти И заменить ВСЕ старые имена директорий во ВСЕХ файлах сразу — и в навыках, и в самом vault.

**Полная процедура — `references/vault-path-audit-procedure.md`** — запускай её при любом stale-пути.

Краткий чеклист:

### 1. Vault .md файлы (самое важное!)
```bash
cd ~/hermes-vault
grep -rln 'СтарыйПуть' --include="*.md" | grep -v ".obsidian/" | grep -v "Archive/Agents/Gotham/report-"
```
Ищи в: `System/Docs/` (документация), `Areas/` (профили, викилинки), `Projects/` (README), `Journal/` (старые дневники с битыми ссылками), `System/audits/`, `Archive/Agents/AgentsData/`

### 2. Навыки и скрипты
```bash
grep -rn 'СтарыйПуть' ~/.hermes/skills/ --include='*.md' --include='*.py'
grep -rn 'СтарыйПуть' ~/.hermes/scripts/ --include='*.py'
```
Проверь: SKILL.md (включая pitfall'ы, примеры, changelog), .legacy/SKILL.md, references/

### 3. Обнови исторические файлы
- **Agent memories** (Archive/Agents/AgentsData/Worker/) — добавь `⚠️ УСТАРЕЛО` notice сверху (не меняй историю!)
- **Audits** (System/audits/) — добавь outdated notice
- **Archive/Agents/Gotham/report-\*.md** — НЕ трогать (исторические)

### 4. Закрепи в памяти
Обнови memory: `memory(action='replace', target='memory', old_text='...', content='All vault paths are English: ...')`

### 5. Перепроверь
```bash
grep -rn 'СтарыйПуть' ~/hermes-vault/ ~/.hermes/skills/ --include="*.md" | grep -v "report-" | grep -v ".obsidian/" | grep -v "УСТАРЕЛО"
```
Допустимы только: migration reference таблицы (старый→новый по смыслу) и user-facing сообщения.

**Урок 15.06.2026:** пользователь нашёл stale `Дневник/` пути в System/Docs/, Areas/Profile/wikilinks, и исторических agent memories. Предыдущий фикс (13.06) пропустил их, потому что искал только в skills и scripts. Теперь полный vault-скан обязателен.

---

## 13. Post-migration staleness trap (урок 15.06.2026)

**Проблема:** Даже когда все `SKILL.md` уже обновлены — **reference-файлы других навыков** могут содержать старые пути. Когда AGENTS.md подсистема автоматически загружает `vault-frontmatter`, его `references/obsidian-paths-consolidation-plan.md` может иметь устаревшие пути. Эти stale-пути подсознательно влияют на твои terminal-команды.

**Симптом:** ты пишешь в terminal старый путь (например `Дневник/`), хотя навык morning-ritual уже правильный. Ты не тупишь — тебя «заразил» stale reference из другого загруженного навыка.

**Правило — при любой ошибке пути в vault:**
1. Не фикси только один файл.
2. Сразу grep ВСЕ загруженные навыки и их references/:
   ```bash
   grep -rn 'СтарыйПуть' ~/.hermes/skills/ --include='*.md'
   grep -rn 'СтарыйПуть' ~/.hermes/scripts/ --include='*.py'
   ```
3. Найденное → исправить ВСЁ одним пакетом (patches).
4. Перепроверить: `grep` даёт 0 результатов.
5. Только потом продолжай задачу.

**Триггер:** любое «команда не нашла файл по пути Х» + «Х — старый (русский) путь». Не отмахивайся — ищи глубже.

### Расширенное правило (урок 15.06.2026)

Когда пользователь сообщает о stale-пути, **НЕДОСТАТОЧНО** проверять только известный список из миграции. ВСЕГДА делай полный рейд:

```bash
cd ~/hermes-vault
# Папки с русскими символами
find . -maxdepth 4 -type d -name "*[а-яА-Я]*" | grep -v ".obsidian" | grep -v "Archive/Agents/Gotham"
# Файлы с русскими символами
find . -maxdepth 4 -type f -name "*[а-яА-Я]*" | grep -v ".obsidian" | grep -v "Archive/Agents/Gotham/report-"
# Wikilinks с русскими путями
grep -rn "\[\[[а-яА-Я].*/" --include="*.md" | grep -v ".obsidian/" | grep -v "Archive/Agents/Gotham/report-"
```

Это находит даже то, что не входит в список миграции (группы/, люди/, Узбекистан-2026/, План.md, архитектура-агентов).

После переименования папок — обнови ВСЕ навыки, которые определяют эти пути как canonical:
- **vault-structure** (раздел Contacts, Learning и т.д.)
- **vault-frontmatter** (таблица node_type → path)
- **contacts** (древо файлов, примеры путей)
- **universal-planner** (примеры `План.md` → `plan.md`)

Если не обновить — навык будет указывать на несуществующую папку, и следующий агент повторит ошибку.

---

## references/

- `references/journal-vs-dnevnik-migration.md` — лог миграции путей (13.06.2026): Дневник/ → Journal/, Планирование/ → Projects/Planning/, Проекты/ → Projects/, профиль-пользователя/ → Areas/Profile/, Привычки/ → Areas/Habits/