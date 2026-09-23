---
name: writing-plans
description: "Write implementation plans: bite-sized tasks, paths, code."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, design, implementation, workflow, documentation]
    related_skills: [subagent-driven-development, test-driven-development, requesting-code-review]
---

# Writing Implementation Plans

## Overview

Write comprehensive implementation plans assuming the implementer has zero context for the codebase and questionable taste. Document everything they need: which files to touch, complete code, testing commands, docs to check, how to verify. Give them bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume the implementer is a skilled developer but knows almost nothing about the toolset or problem domain. Assume they don't know good test design very well.

**Core principle:** A good plan makes implementation obvious. If someone has to guess, the plan is incomplete.

## When to Use

**Always use before:**
- Implementing multi-step features
- Breaking down complex requirements
- Delegating to subagents via subagent-driven-development

**Don't skip when:**
- Feature seems simple (assumptions cause bugs)
- You plan to implement it yourself (future you needs guidance)
- Working alone (documentation matters)

## Bite-Sized Task Granularity

**Each task = 2-5 minutes of focused work.**

Every step is one action:
- "Write the failing test" — step
- "Run it to make sure it fails" — step
- "Implement the minimal code to make the test pass" — step
- "Run the tests and make sure they pass" — step
- "Commit" — step

**Too big:**
```markdown
### Task 1: Build authentication system
[50 lines of code across 5 files]
```

**Right size:**
```markdown
### Task 1: Create User model with email field
[10 lines, 1 file]

### Task 2: Add password hash field to User
[8 lines, 1 file]

### Task 3: Create password hashing utility
[15 lines, 1 file]
```

## Plan Document Structure

### Header (Required)

Every plan MUST start with:

```markdown
# [Feature Name] Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

### Task Structure

Each task follows this format:

````markdown
### Task N: [Descriptive Name]

**Objective:** What this task accomplishes (one sentence)

**Files:**
- Create: `exact/path/to/new_file.py`
- Modify: `exact/path/to/existing.py:45-67` (line numbers if known)
- Test: `tests/path/to/test_file.py`

**Step 1: Write failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

**Step 2: Run test to verify failure**

Run: `pytest tests/path/test.py::test_specific_behavior -v`
Expected: FAIL — "function not defined"

**Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

**Step 4: Run test to verify pass**

Run: `pytest tests/path/test.py::test_specific_behavior -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## Mandatory Pre-Work: Phase 0 — Data Collection & Alignment

**Before ANY implementation, follow this protocol. Skipping it causes catastrophic failures (corrupted files, gateway crashes, cascading breaks).**

### 0.1 Collect Current State

Gather facts before touching anything:
- What exists now? What files are involved?
- What's the current config/state of the system?
- Which processes are running? (gateway, agents, etc.)
- What are the dependencies and risks?
- **📌 Who writes to these files?** — Map the agent ecosystem that touches them: Kanban profiles, cron jobs, delegate_task children, skills (evening-diary, morning-brief, hermes-book...), user manually. A plan that says «patch file X once» fails if an agent overwrites X later without the fix. Identify ALL agents that write to the target files, and plan to patch each one.

Run read-only commands first:
```python
# Check file contents
read_file("target/file.py")

# Check process state
terminal("systemctl --user is-active hermes-gateway")

# Check config
terminal("grep relevant_key ~/.hermes/config.yaml")

# Check what skills/commands exist
from agent.skill_commands import get_skill_commands
```

### 0.2 Analyze Root Cause

- What actually needs to change, and WHY?
- What's the minimal change that fixes the issue?
- What COULD go wrong? (file corruption, process crash, syntax error)
- Is there a safer approach? (config change instead of code edit, alias instead of new handler)

### 0.3 Clarify & Get Alignment

Present your findings + proposed plan to the user BEFORE writing code:
> "Вот что я нашёл: [данные]. План: [что сделаю]. Ок?"

If the user corrects your approach, adjust the plan. Do NOT start implementing until the user confirms.

### 0.4 Plan (Write It Down)

Only now open `writing-plans` and produce a full implementation plan. Include:
- Exact files to modify
- Fallback/rollback strategy for each file
- Verification step after each change
- The rollback command (e.g. `git checkout path/to/file`)

### 0.5 Implement in Small Steps

**One change at a time with verification:**
1. Make change → 2. Check syntax (`python3 -c "compile(open('file').read(), 'file', 'exec')"`) → 3. Verify logic → 4. Only then make next change

**CRITICAL-FILE SAFETY PROTOCOL (gateway/run.py, hermes_cli/commands.py, config.yaml):**
- NEVER use patch/heredoc on critical live files — these tools can silently corrupt multi-kilobyte files on interruption
- ALWAYS write modified content via write_file with syntax validation:
  ```bash
  python3 -c "compile(open('path').read(), 'path', 'exec'); print('OK')"
  ```
- ALWAYS stop the process that uses the file BEFORE editing:
  ```bash
  systemctl --user stop hermes-gateway
  ```
- After changes, restart and verify:
  ```bash
  systemctl --user start hermes-gateway
  sleep 3
  systemctl --user is-active hermes-gateway  # must return "active"
  ```
- Know your rollback: `git checkout path/to/file`

**GATEWAY INTERRUPTION TRAP:** Every gateway restart interrupts your current tool execution. If you edit gateway code, changes take effect only after restart. The restart itself will kill your in-flight tool calls. Plan for this — batch changes, apply them while gateway is stopped, then restart once.

### Pitfall: Skipping Phase 0

Skipping data collection and alignment inevitably leads to:
- Wrong files edited
- Broken syntax from corrupted patches
- Gateway crashes
- Cascading restarts that interrupt your own tool calls
- User frustration and trust erosion

The cost of 2 extra minutes gathering data is zero compared to 30 minutes recovering from a corrupted 18K-line file.

After this phase, proceed with the normal writing process below.

## Writing Process

### Step 1: Understand Requirements

Read and understand:
- Feature requirements
- Design documents or user description
- Acceptance criteria
- Constraints

### Step 2: Explore the Codebase

Use Hermes tools to understand the project:

```python
# Understand project structure
search_files("*.py", target="files", path="src/")

# Look at similar features
search_files("similar_pattern", path="src/", file_glob="*.py")

# Check existing tests
search_files("*.py", target="files", path="tests/")

# Read key files
read_file("src/app.py")
```

### Step 3: Design Approach

Decide:
- Architecture pattern
- File organization
- Dependencies needed
- Testing strategy

### Step 4: Write Tasks

Create tasks in order:
1. Setup/infrastructure
2. Core functionality (TDD for each)
3. Edge cases
4. Integration
5. Cleanup/documentation

### Step 5: Add Complete Details

For each task, include:
- **Exact file paths** (not "the config file" but `src/config/settings.py`)
- **Complete code examples** (not "add validation" but the actual code)
- **Exact commands** with expected output
- **Verification steps** that prove the task works

### Step 6: Review the Plan

Check:
- [ ] Tasks are sequential and logical
- [ ] Each task is bite-sized (2-5 min)
- [ ] File paths are exact
- [ ] Code examples are complete (copy-pasteable)
- [ ] Commands are exact with expected output
- [ ] No missing context
- [ ] DRY, YAGNI, TDD principles applied

### Step 7: Save the Plan

```bash
mkdir -p docs/plans
# Save plan to docs/plans/YYYY-MM-DD-feature-name.md
git add docs/plans/
git commit -m "docs: add implementation plan for [feature]"
```

### Test-Plan-Driven Task Breakdown

Когда в проекте есть отдельный план тестирования (таблицы тестов по этапам, как `08-test-plan.md`):

1. Прочитай его ДО написания плана — это источник задач.
2. Привяжи КАЖДЫЙ тест к конкретной задаче: в секции **Files** задачи указывай точные имена тестов (`test_leads_filter` → задача 4.5) и файл теста (`tests/api/test_admin_clients.py`). Не «тесты на клиентов», а конкретные имена.
3. Одна задача = 1–3 связанных теста + реализация. Финальная проверка плана: каждый тест из тест-плана упомянут хотя бы в одной задаче — 100% покрытие тест-плана = критерий готовности этапа.
4. Backend-задачи — полный TDD-цикл (красный тест → FAIL → код → PASS → commit).
5. Фронтенд: если в тест-плане проекта нет фронт-тестов — НЕ выдумывай vitest-инфраструктуру (YAGNI). Проверка = `npm run build` + ручной smoke по критериям приёмки + commit.
6. Многоэтапный проект (этап N планируется после этапов 1..N-1): обязателен раздел «Допущения» — что уже готово из прошлых этапов (модели, зависимости, event bus, notifier'ы, helper рабочих часов), с оговоркой «если пути в проекте отличаются — адаптируй, сохраняя интерфейсы». Читай файлы шагов ПРЕДЫДУЩИХ этапов, а не только целевого.

Рабочий процесс с конкретными путями и структурой: `references/booking-platform-planning.md`.

## Multi-Stage Plans (многоэтапные планы)

Для проектов из нескольких этапов (этап = файл в `steps/` спеки) один плоский список задач не работает. Проверенная структура (Booking Platform, этапы 1–3: 3 этапа, 60 задач, 4546 строк):

- **Нумерация задач с префиксом этапа**: `### Задача N.M:` (1.10, 3.14). Кросс-ссылки «см. задачу 3.10» однозначны, порядок исполнения очевиден.
- **Каждый этап**: «Цели» + «Критерии приёмки» (копируются из файла шага `steps/NN`) + задачи.
- **«Структура файлов» — таблица на КАЖДЫЙ этап** (Путь | Роль | ~строк | Интерфейс), не одна общая: видно, в каком этапе файл появляется.
- **Первый этап (foundation) добавляет раздел «0. Общие правила»**: TDD-цикл, лимит 150 строк, команды окружения (venv, docker compose, создание тестовой БД), конвенция коммитов, тестовая БД (отдельная `*_test`, схема через `create_all` в conftest, не через alembic — быстрее).
- **«Решения и допущения» таблицей в КОНЦЕ плана** (репозиторий, auth-подход, enum-значения, YAGNI-отсечения) — для первых этапов обязательна: инфраструктуры ещё нет, каждое решение фиксируется с обоснованием.
- **Закрывающая задача этапа**: `wc -l` лимит + полный `pytest` + коммит `chore: stage N complete`.

### Как писать ОЧЕНЬ большие планы (2000+ строк)

Один write_file не справится безопасно. Пиши частями в /tmp и склеивай:

```bash
cat /tmp/plan_part1.md /tmp/plan_part2.md ... > <target>.md && rm /tmp/plan_part*.md
wc -l <target>.md
grep -c "^### Задача" <target>.md   # сверить число задач
```

Разбивка: part1 = header + правила + структура файлов; part2..N = этап на часть. Перед «готово» проверь склейку: число задач, заголовки разделов, хвост файла. Замечание: `search_files` может не находить якорные regex (`^### `) — для верификации используй `grep`.

### Питфолл: дополнение плана ≠ только новые задачи

Когда после ревью в существующий план добавляются задачи (напр. 3.18–3.20 после проверки), НЕ ограничивайся вставкой задач. ОБЯЗАТЕЛЬНО синхронизируй:

1. **Раздел «Структура файлов»** — добавить новые файлы (specialist_status.py, retarget_service.py, тест-файлы), новые таблицы БД (specialist_notifications, retarget_sent) в описание моделей.
2. **Итоговые счётчики** — «~66 файлов», «44/44 тестов» и т.п. пересчитать; устаревшие цифры = потеря доверия.
3. **Критерии приёмки этапа** — новые фичи должны попасть в DoD-список.
4. **Пути файлов в новых задачах** — сверять с уже существующей структурой проекта (модели в `infrastructure/db/models/`, хэндлеры ботов в `interface/bots/handlers/`), а не выдумывать новые. Ревьюер плана A (2026-08-19) ловил: `src/domain/booking/models.py` не существует, реальный путь `src/infrastructure/db/models/booking.py`.

Проверка после дополнения: `grep -c "^### Задача" <plan>.md` (число задач), `wc -l` (размер), повторная сверка ключевых терминов спеки.

### Питфолл: dataclass-события домена

Базовое `DomainEvent` с полями-дефолтами (`event_id`, `occurred_at`) + подкласс с полями БЕЗ дефолтов → `TypeError: non-default argument follows default argument`. Фикс: `@dataclass(kw_only=True)` на базовом классе И каждом событии — поля подкласса остаются обязательными, поля базы — keyword-only.

## Mandatory Architecture Section (HARDLINE)

Каждый план, который описывает КОД, ОБЯЗАН включать раздел «Структура файлов» с декомпозицией. Без него план не принимается.

### File Size Limit (жесткий лимит)
- **Максимум 150 строк на файл** (целевой оптимум: 80-120)
- Файл больше 150 строк → обязан быть разбит на модули в плане
- Никогда не планируй файл на 300+ строк — это считается сломанным дизайном
- Лимит применяется к: логике, моделям, хэндлерам, сервисам, тестам

### Required Structure
В разделе «Структура файлов» для КАЖДОГО нового файла укажи:
- Путь: `src/domain/booking/appointment.py`
- Роль: что делает (одна ответственность)
- Ожидаемый размер: ~80-120 строк
- Интерфейс: публичные функции/классы

### Event-Driven + DDD по умолчанию
- Связь между модулями — через СОБЫТИЯ (`AppointmentCreated`, `ClientMessaged`), не прямые вызовы
- Домены (bounded contexts): `booking`, `clients`, `messaging`, `scheduling`, `ai`, `plans`
- Бизнес-правила — в домене, не в UI/хэндлерах
- Side-эффекты (уведомления, крон, эскалации) — через подписку на события
- Если план нарушает event-driven/DDD — перепиши его до реализации

### Verification in Plan
- Шаг «Проверить размер файлов»: `wc -l src/**/*.py | sort -rn | head` — ни один файл > 150 строк
- Критерий приёмки плана: все файлы ≤ 150 строк, модули разбиты, события определены

## Principles

### DRY (Don't Repeat Yourself)

**Bad:** Copy-paste validation in 3 places
**Good:** Extract validation function, use everywhere

### YAGNI (You Aren't Gonna Need It)

**Bad:** Add "flexibility" for future requirements
**Good:** Implement only what's needed now

```python
# Bad — YAGNI violation
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.preferences = {}  # Not needed yet!
        self.metadata = {}     # Not needed yet!

# Good — YAGNI
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
```

### TDD (Test-Driven Development)

Every task that produces code should include the full TDD cycle:
1. Write failing test
2. Run to verify failure
3. Write minimal code
4. Run to verify pass

See `test-driven-development` skill for details.

### Frequent Commits

Commit after every task:
```bash
git add [files]
git commit -m "type: description"
```

## Common Mistakes

### Vague Tasks

**Bad:** "Add authentication"
**Good:** "Create User model with email and password_hash fields"

### Incomplete Code

**Bad:** "Step 1: Add validation function"
**Good:** "Step 1: Add validation function" followed by the complete function code

### Missing Verification

**Bad:** "Step 3: Test it works"
**Good:** "Step 3: Run `pytest tests/test_auth.py -v`, expected: 3 passed"

### Missing Agent Ecosystem Mapping

**Bad:** «Patch all vault files with frontmatter once, then done.»
**Good:** «Identify all agents that write to vault files (evening-diary, morning-brief, hermes-book, worker, growth-coach...). Patch each one to include frontmatter. Create a lint gate for enforcement.»

A plan that patches files «once and done» fails when agents rewrite those files later without the fix. Before planning changes to vault/workspace/skill files:
1. Map WHO writes to them (Kanban profiles, cron jobs, delegate_task children, skills, user manually)
2. Decide: patch each writer individually **OR** build enforcement infrastructure (write_file hooks, pre-commit lint, shared templates)
3. Include the infrastructure cost in the plan — don't pretend «one-time patch» is a complete solution

### Missing File Paths

**Bad:** "Create the model file"
**Good:** "Create: `src/models/user.py`"

## Spec ≠ Plan (Pitfall)

**Спека описывает ЧТО строим; план описывает КАК реализовать.** Это разные артефакты, оба обязательны. Готовая спека НЕ является планом — после неё всегда запускай планирование.

**Послойное проектирование спеки (в чате с пользователем):**
- Слои сверху вниз: бизнес/границы → сценарии → функциональные требования → архитектура → данные → UX → этапы.
- Согласуй КАЖДЫЙ слой с пользователем ДО перехода к следующему: задавай вопросы, предлагай варианты (таблицы сравнения), фиксируй решения.
- Записывай согласованные слои в vault/Obsidian по мере прохождения.
- Полный процесс фазы спеки (вопросы по слоям, фиксация, дерево, передача в планирование): навык `spec-design`.

**Терминологическая дисциплина при перепозиционировании продукта:**
- Если пользователь перепозиционировал продукт («это НЕ приложение для клиник, это лид-платформа») — сразу пройдись по ВСЕЙ документации и замени устаревшие доменные термины (клиника→бизнес, врач→специалист/мастер, пациент→клиент).
- Нейтральную терминологию согласуй в Слое 0 и зафиксируй в `00-overview.md` как обязательную. Продолжение разговора в старых терминах после перепозиционирования = раздражает пользователя.

**Древовидная структура документации (требование пользователя):**
- НИКОГДА не пиши спеку одним файлом. Один файл на 7 слоёв = нечитаемо и для человека, и для агентов-исполнителей («и человеку проще читать, и нейронки потом пойдут по шагам»).
- Обязательное дерево:
  - `README.md` — содержание, дерево, таблица слоёв, шорткат ключевых решений
  - файл на каждый слой (`01-layer0-...md`, ...)
  - `steps/` — файлы шагов для исполнителей (цель, задачи, критерии приёмки, wc -l проверка)
  - `08-test-plan.md` — план тестирования (TDD, тесты по этапам, каждый тест = задача в плане)
  - `plans/` — детальные implementation plans (пишутся планировщиками после спеки)
- Относительные ссылки между файлами. Каждый файл — одна ответственность.

**Параллельное планирование после спеки:**
- Для крупного проекта распараллеливай написание implementation plans: `delegate_task` с batch tasks (до лимита concurrent), каждый планировщик получает свой блок этапов (напр. 1-3, 4-5, 6-8).
- Каждому планировщику передавай: пути к файлам спеки/тест-плана/шагов, требование загрузить writing-plans, жёсткие лимиты (≤150 строк, event-driven+DDD), путь для сохранения плана.
- Проверяй готовые планы: размер файлов, полнота, отсутствие монолитов.

**Параллельная проверка планов (reviewer fan-out) — обязательный шаг после планирования:**
- После того как планировщики написали планы, запускай проверку: `delegate_task` с batch reviewer-задачами (по одному на план), каждый сверяет СВОЙ план со спекой.
- Каждому ревьюеру передавай: **явный чек-лист требований** (выжимка из спеки, 15-20 пунктов: зазор, окно отмены, статусы, эскалация, роли, техподдержка, лимит строк, покрытие тестов...) + пути к слоям/тест-плану/шагам.
- Формат отчёта ревьюера: по каждому пункту `[OK] (задача N)` или `[MISSING]` + список пробелов в конце.
- Найденные пробелы → дописать задачи в план → при необходимости повторный прогон ревьюера.
- Реальный кейс: такой прогон нашёл 3 забытые фичи (ретаргетинг, статус специалиста, кнопки связи с человеком), которых не было ни в одном плане.
- Быстрая grep-сверка перед диспетчеризацией: `grep -ric "термин" plans/*.md` — нулевые вхождения ключевой фичи спеки = гарантированный пробел.

**Playbook выполнения проверки (проверено на этапах 6-8 Booking Platform, 2026-08-20):**
1. Прочитай ВСЁ до анализа: слои спеки (business/functional/architecture/data/UX), test-plan, step-файлы, сам план. План 900+ строк — читай `read_file` по 500 строк (offset/limit), не head/tail.
2. Маппь каждый пункт чек-листа на КОНКРЕТНЫЕ номера задач плана (`6.3`, `7.4`, `8.2`) — `[OK]` только при явной задаче, покрывающей требование. Цитируй номера задач в отчёте, чтобы пользователь мог перепроверить.
3. Проверь покрытие test-plan: каждый тест из таблицы этапа обязан иметь задачу в плане. Отклонения («тест реализован скриптом, а не pytest», «тест проверяет только `docker compose config -q`») — замечание, НЕ `[MISSING]`.
4. Кросс-план ownership: фича живёт ровно в ОДНОМ плане. Ищи ключевые слова по ВСЕМ планам директории (ретаргетинг → только plan-01-03 задача 3.20, техподдержка → plan-04-05 задача 5.14); текущий план должен лишь стыковаться ссылками на чужие задачи, не дублировать. «Нет упоминания в плане X» ≠ «не реализовано» — проверь другие планы ДО вывода `[MISSING]`.
5. `[MISSING]` — только реальный пробел (требование спеки не покрыто нигде). Слабости (скрипт вместо автотеста, имплицитная связка, расхождение формулировок между планами) — отдельный блок «замечания». Сверхнормативные тесты плана (которых нет в test-plan) — плюс, не пробел.
6. Отчёт на русском: «Проверка N пунктов» — по каждому `**N. Название — [OK]/[MISSING]**` + обоснование и номера задач → «Список пробелов» (реальные → мелкие → замечания) → «Спецпроверки» (дубли фич, связки между планами) → итог «X/N [OK], Y [MISSING]».
7. Pitfall `search_files` (content): паттерн с альтернацией `a|b|c` (особенно с кириллицей) может вернуть ЛОЖНЫЙ 0, хотя строки есть. Получил 0, а ожидал совпадения → повтори одиночными словами (path — директория, не файл) или `grep -c`. Одиночные кириллические слова ищутся надёжно.

Подробная карта проверки этапов 6-8 (18 пунктов, маппинг на задачи, кросс-план ownership, найденные пробелы): `references/booking-platform-review-6-8.md`.

См. также: `references/spec-tree-template.md` — проверенный шаблон дерева спеки.

## Execution Handoff

After saving the plan, offer the execution approach:

**"Plan complete and saved. Ready to execute using subagent-driven-development — I'll dispatch a fresh subagent per task with two-stage review (spec compliance then code quality). Shall I proceed?"**

When executing, use the `subagent-driven-development` skill:
- Fresh `delegate_task` per task with full context
- Spec compliance review after each task
- Code quality review after spec passes
- Proceed only when both reviews approve

## Remember

```
Bite-sized tasks (2-5 min each)
Exact file paths
Complete code (copy-pasteable)
Exact commands with expected output
Verification steps
DRY, YAGNI, TDD
Frequent commits
```

**A good plan makes implementation obvious.**

## Architecture Specs (Mandatory Format)

**Любой system-level архитектурный spec** (multi-module, multi-file, data pipelines, мониторинг, новая система) **ОБЯЗАН** следовать формату из `references/architecture-spec-format.md`:

1. **≤200 строк на файл** — ни один spec-файл не превышает 200 строк. Если не влезает — режь на модули.
2. **README.md = оглавление** с ссылками на все файлы + таблица ключевых решений + data flow.
3. **Cross-links** между файлами (`[[01-database]]`, `→ [подробнее](02-collector.md)`).
4. **Каждый файл** описывает одну независимую сущность/модуль.

**Нарушение этого правила = пользовательская боль.** Предыдущий spec был написан одним файлом — пользователь явно сказал: «так нельзя, надо сразу на несколько файлов разбивать».

Прочитай `references/architecture-spec-format.md` перед тем как писать любой architecture spec.

## Related Resources

- **Architecture spec format (MANDATORY):** `references/architecture-spec-format.md` — формат разделения, оглавление, cross-links, таблица решений. Прочти перед архитектурным spec'ом.
- **Multi-tenant SaaS паттерны:** `references/multi-tenant-saas-notes.md` — ядро+модули, tenant_id, домен записи (слоты/статусы/эскалация), триал 7 дней, воронка продаж, анти-фрод, роли, ИИ-агент. Проверено на Booking Platform 2026-08.
- **Execution:** `subagent-driven-development` skill dispatches tasks with two-stage review.
- **Пример project-специфичного процесса:** `references/booking-platform-planning.md` — чтение исходников, структура плана, конвенции путей и frontmatter для многоэтапного проекта в vault (Booking Platform, этапы 4–5).
