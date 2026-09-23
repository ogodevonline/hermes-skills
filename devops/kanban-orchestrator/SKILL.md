---
name: kanban-orchestrator
description: Decomposition playbook + anti-temptation rules for an orchestrator profile routing work through Kanban. The "don't do the work yourself" rule and the basic lifecycle are auto-injected into every kanban worker's system prompt; this skill is the deeper playbook when you're specifically playing the orchestrator role.
version: 3.5.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, routing]
    related_skills: [kanban-worker]
---

# Kanban Orchestrator — Decomposition Playbook

> The **core worker lifecycle** (including the `kanban_create` fan-out pattern and the "decompose, don't execute" rule) is auto-injected into every kanban process via the `KANBAN_GUIDANCE` system-prompt block. This skill is the deeper playbook when you're an orchestrator profile whose whole job is routing.

## 🚨 MUST LOAD BEFORE CREATING TASKS

Любая операция создания Kanban задачи из CLI начинается с `skill_view('kanban-orchestrator')`.

Если ты начал создавать задачу, не загрузив этот навык — **остановись**. Первый tool call — загрузить навык. Не угадывай флаги, не пиши `--title`, не гадай синтаксис. Читай Quick Reference ниже.

## Quick Reference (создание задачи)

```bash
# ✅ Базовое создание — title ПОЗИЦИОННЫЙ, не --title
hermes kanban create "Моя задача" --body "Описание" --assignee coder --initial-status blocked --priority 1

# ❌ НЕПРАВИЛЬНО
hermes kanban create --title "Задача"  # unrecognized arguments
hermes kanban create --description "..."  # не существует

# ✅ Body из файла — head -N, не весь файл (multi-line ломает bash)
hermes kanban create "Задача" --body "$(head -40 /tmp/body.md)" --assignee coder

# ✅ Получить task_id после create: stdout содержит "Created t_xxxx (todo, ...)" — грепай
hermes kanban create "Задача" --body "..." --assignee coder 2>&1 | grep -oE "t_[a-f0-9]{8}" | head -1
# ⚠️ --json выводит много полей и в терминале обрезается (id теряется) — не полагайся на него.
# Для parent-цепочки: создавай по ОДНОЙ задаче за вызов, id предыдущей → --parent следующей.
```

## Profiles are user-configured — not a fixed roster

Hermes setups vary widely. Some users run a single profile that does everything; some run a small fleet (`docker-worker`, `cron-worker`); some run a curated specialist team they've named themselves. There is **no default specialist roster** — the orchestrator skill does not know what profiles exist on this machine.

Before fanning out, you must ground the decomposition in the profiles that actually exist. The dispatcher silently fails to spawn unknown assignee names — it doesn't autocorrect, doesn't suggest, doesn't fall back. So a card assigned to `researcher` on a setup that only has `docker-worker` just sits in `ready` forever.

**Step 0: discover available profiles before planning.**

Use one of these:

- `hermes profile list` — prints the table of profiles configured on this machine. Run it through your terminal tool if you have one; otherwise ask the user.
- `kanban_list(assignee="<some-name>")` — sanity-check a single name. Returns an empty list (rather than an error) for an unknown assignee, so this only confirms a name you're already considering.
- **Just ask the user.** "What profiles do you have set up?" is a fine first turn when the goal needs more than one specialist.

Cache the result in your working memory for the rest of the conversation. Re-asking every turn wastes a tool call.

Newly created profiles need the `kanban-worker` skill in their skills dir before the dispatcher can spawn them. **Auto-repair in v3.2+:** the dispatcher creates the symlink automatically on first spawn. For older dispatchers, symlink manually (see the "Profiles missing kanban-worker" pitfall below). See also `references/profile-setup-checklist.md` for the full setup recipe (skills, config, SOUL.md, .env).

## When to use the board (vs. just doing the work)

Create Kanban tasks when any of these are true:

1. **Multiple specialists are needed.** Research + analysis + writing is three profiles.
2. **The work should survive a crash or restart.** Long-running, recurring, or important.
3. **The user might want to interject.** Human-in-the-loop at any step.
4. **Multiple subtasks can run in parallel.** Fan-out for speed.
5. **Review / iteration is expected.** A reviewer profile loops on drafter output.
6. **The audit trail matters.** Board rows persist in SQLite forever.

If *none* of those apply — it's a small one-shot reasoning task — use `delegate_task` instead or answer the user directly.

## Researcher task creation — DON'T over-specify

Когда создаёшь Kanban-задачу на researcher, тело должно быть **минимальным**:
- Только **тема** + **конкретные вопросы** для поиска
- НЕ указывать: путь сохранения в Obsidian, self-check, шаблон, инструкции по формату
- Researcher сам знает свой пайплайн (типизация > сбор > верификация > шаблон > self-check > obsidian_save.py) — всё прописано в его SOUL.md и навыках
- Достаточно: --skill research-report-templates (он сам загрузит, разберётся)
- --max-runtime 30m — чтобы хватило на глубокий поиск (researcher ходит по 7-10 источникам)

Пример **правильного** тела:
```
Тема: Как программисту заработать с AI-агентами в 2026
Вопросы: бизнес-модели, платформы, реальные кейсы с цифрами, техстек, риски
```

Пример **неправильного** (лишнее):
- "Сохранение: ~/hermes-vault/..." — researcher сам знает куда
- "Self-check: 5 вопросов" — прописано в его SOUL.md
- "Шаблон: research-report-templates" — он сам загрузит

### `--goal` для open-ended research

Для исследовательских задач (market research, обзор рынка, сравнение сервисов) **обязательно** используй `--goal` + `--goal-max-turns 50` + `--max-runtime 30m`:

```bash
hermes kanban create "Исследование: ..." \
  --body "..." \
  --assignee researcher \
  --goal \
  --goal-max-turns 50 \
  --max-runtime 30m
```

Без `--goal` researcher делает один проход и завершает — нередко с неполным результатом. `--goal` запускает judge-loop: после каждого ответа проверяет, выполнена ли задача, и если нет — worker продолжает в той же сессии, пока judge не решит, что всё сделано. 50 turns достаточно для глубокого поиска по 7-10 источникам.

### Для debugger-задач

### Для coder-задач

- Тело: по шаблону GCCD (см. раздел ниже). Goal + Context + Constraints + Done when.
- --skill: загрузить нужные навыки (github-pr-workflow, test-driven-development и т.д.)
- --max-runtime: зависит от сложности, для coder минимум 30m

## GCCD — Goal, Context, Constraints, Done When

> Подробный справочник с примерами по каждому профилю: [references/gccd-framework.md](references/gccd-framework.md)
> Источник: OpenAI Codex Best Practices

Все Kanban-задачи (кроме researcher — у него свой пайплайн) структурировать по GCCD:

```
**Goal:** Что конкретно нужно сделать? Одно предложение.
**Context:** Какие файлы, доки, примеры, ошибки релевантны? @-упоминания файлов.
**Constraints:** Tech-stack, конвенции, архитектурные ограничения, safety rules.
**Done when:** Конкретный критерий приёмки — что можно проверить руками/тестами.
```

**Почему это важно:** Без GCCD агент делает предположения. Scope расползается. Результат приходится переделывать. GCCD — это контракт между оркестратором и агентом.

**Когда сокращать:**
- **researcher** — только Goal + Context (он сам знает свой пайплайн из SOUL.md)
- **debugger** — обязательны все 4 секции, особенно Context (логи, трассировки) и Done when (какой баг считается исправленным)
- **coder** — обязательны все 4 секции
- **architect** — Goal + Constraints важнее всего, Context может быть минимальным
- **reviewer** — Goal (что ревьюить) + Constraints (на что обращать внимание) + Done when (критерии прохождения ревью)

**Примеры тел задач по профилям (см. references/gccd-framework.md для полного набора):**

**Coder:**
```
**Goal:** Добавить эндпоинт GET /api/health
**Context:** src/main.py (строки 45-120), схема ответа в docs/api.md
**Constraints:** FastAPI, без новых зависимостей, code-style как в проекте (black, isort)
**Done when:** curl localhost:8000/api/health → 200 {"status":"ok"}; pytest tests/test_health.py -v → PASS
```

**Debugger:**
```
**Goal:** Найти причину таймаутов при параллельных запросах к /api/search
**Context:** Логи /var/log/app/error.log (строки 200-350), код src/api/search.py
**Constraints:** Не менять API-контракт, не добавлять новые зависимости
**Done when:** 10 concurrent запросов — все <500ms; в логах нет timeout-ошибок
```

**Architect:**
```
**Goal:** Спроектировать модуль аутентификации
**Context:** docs/db-schema.md, docs/api-spec.yaml
**Constraints:** JWT, refresh rotation, rate limiting, без внешних SSO. Каждый файл ≤200 строк — если модуль больше, разбивать на несколько файлов с чёткими границами ответственности.
**Done when:** spec содержит: endpoints, DB-schema, middleware flow, sequence diagram. Все файлы ≤200 строк.
```

**Reviewer:**
```
**Goal:** Проверить PR #42 — модуль авторизации
**Context:** PR diff, docs/auth-spec.md
**Constraints:** Безопасность (SQLi, CSRF, XSS), code-style, покрытие >80%
**Done when:** Все acceptance criteria из spec выполнены; issues с severity
```

После завершения:
1. Сохрани полный отчёт в /home/hermes/.hermes/kanban/results/{task_id}.md
2. Вызови kanban_complete(summary="Кратко: <итог>", artifacts=["/home/hermes/.hermes/kanban/results/{task_id}.md"])
НЕ используй clarify — в Kanban нет пользователя.

## The anti-temptation rules

Your job description says "route, don't execute." The rules that enforce that:

- **Do not execute the work yourself.** Your restricted toolset usually doesn't even include terminal/file/code/web for implementation. If you find yourself "just fixing this quickly" — stop and create a task for the right specialist.
- **For any concrete task, create a Kanban task and assign it.** Every single time.
- **Split multi-lane requests before creating cards.** A user prompt can contain several independent workstreams. Extract those lanes first, then create one card per lane instead of bundling unrelated work into a single implementer card.
- **Run independent lanes in parallel.** If two cards do not need each other's output, leave them unlinked so the dispatcher can fan them out. Link only true data dependencies.
- **If no specialist fits the available profiles, ask the user which profile to create or which existing profile to use.** Do not invent profile names; the dispatcher will silently drop unknown assignees.
- **Decompose, route, and summarize — that's the whole job.**

## Decomposition playbook

### Step 1 — Understand the user's vision first (Vision-First Pipeline)

Before any decomposition, the orchestrator must anchor the entire pipeline to the user's actual intent. Agent drift happens when a coder interprets a vague spec in a way the user didn't mean.

**1a. Surface the user's mental model.** Ask clarifying questions before creating any cards. Don't assume you understand. Extract:
- What outcome does the user expect? (not how, but what)
- What does "done" look like to them?
- What would make them reject the result?

**1b. Write Acceptance Criteria in human language.** Transform the user's answers into 3-5 bullet-point acceptance criteria written as user-visible outcomes, not technical specs. Example:

```
## Acceptance Criteria
1. As a user, I get a list of houses in Nukus up to 300 million sum
2. Each listing shows: title, price, link, photo
3. On error — email alert with the error reason, not an empty report
4. Report arrives once daily at 14:30 MSK
```

**1c. Show the criteria to the user and get approval.** Paste them back in your response: "Вот моё понимание. Я правильно понял?" Wait for explicit confirmation. This is the cheapest time to catch misalignment — one message back-and-forth vs. wasted architect+coder+reviewer cycles.

**1d. Pass criteria to every downstream task.** Include the accepted criteria in every task body you create — architect (to design spec), coder (to not deviate), reviewer (to validate against them). The architect writes specs with an `## Acceptance Criteria` section. The coder strictly follows them. The reviewer blocks if code doesn't match them. The criteria are the contract between the user's vision and the implementation.

**1e. Never skip user spec review.** For sequential pipelines (architect → coder), always show the spec to the user and get approval before the coder starts. The spec must be in human-readable language with acceptance criteria. The user must be able to read it and say "да, это то, что я хотел."

**Cheap to ask; expensive to spawn the wrong fleet.**

### Step 2 — Sketch the task graph

Before creating anything, draft the graph out loud (in your response to the user). Treat every concrete workstream as a candidate card:

1. Extract the lanes from the request.
2. Map each lane to one of the profiles you discovered in Step 0. If a lane doesn't fit any existing profile, ask the user which to use or create.
3. Decide whether each lane is independent or gated by another lane.
4. Create independent lanes as parallel cards with no parent links.
5. Create synthesis/review/integration cards with parent links to the lanes they depend on.

Examples of prompts that should fan out (using placeholder profile names — substitute whatever exists on the user's setup):

- "Build an app" → one card to a design-oriented profile for product/UI direction, one or two cards to engineering profiles for implementation, plus a later integration/review card if the user has a reviewer profile.
- "Fix blockers and check model variants" → one implementation card for the blocker fixes plus one discovery/research card for config/source verification. A final reviewer card can depend on both.
- "Research docs and implement" → a docs-research card can run in parallel with a codebase-discovery card; implementation waits only if it truly needs those findings.
- "Analyze this screenshot and find the related code" → one card to a vision-capable profile for the visual analysis while another searches the codebase.

Words like "also," "finally," or "and" do not automatically imply a dependency. They often mean "make sure this is covered before reporting back." Only link tasks when one card cannot start until another card's output exists.

Show the graph to the user before creating cards. Let them correct it — including which actual profile name should own each lane.

**User preference: review specs before coding.** For sequential pipelines (architect → coder), always let the user review and approve the spec before creating coder tasks. Users often want to correct details, add edge cases, or adjust priorities before implementation begins. Either:
- Create the architect task first, wait for it to complete, show the spec to the user, then create coder tasks after approval.
- Or create all three cards (architect → coder → reviewer) at once with parent links — the coder task stays in `todo` until architect reaches `done`. Before the architect completes, show the spec to the user. If they request changes, revise the spec and only then complete the architect task, which auto-promotes coder to `ready`.

**❗ Spec format (user requirement):** Не пиши spec одним файлом. В теле задачи архитектору явно укажи: разбить на несколько файлов в Obsidian с README-оглавлением и перекрёстными ссылками. См. `references/spec-format-obsidian.md` — там шаблон структуры папки и правила.

Skipping this review step leads to wasted work when the user expected different output.

### Step 3 — Create tasks and link

**🔥 CRITICAL — ALWAYS create tasks as `blocked` first when user approval is needed.** If `dispatch_in_gateway: true` (the default), the dispatcher auto-picks `ready` tasks within seconds. Creating a task at `ready` bypasses the approval gate entirely — the worker starts before you can even show the task to the user.

The correct lifecycle:
1. Create with `initial_status="blocked"` (or `--initial-status blocked` via CLI)
2. Subscribe to notifications (`kanban notify-subscribe`)
3. Show the task body to the user
4. Wait for explicit OK
5. Unblock (`kanban unblock <task_id>`)
6. Dispatcher picks it up

Only skip the `blocked` step when the task is fully pre-approved (e.g. the user explicitly said "just do it, no need to check with me").

Use the profile names from Step 0. The example below uses placeholders `<profile-A>`, `<profile-B>`, `<profile-C>` — replace them with what the user actually has.

```python
t1 = kanban_create(
    title="research: Postgres cost vs current",
    assignee="<profile-A>",
    body="Compare estimated infrastructure costs...",
    initial_status="blocked",  # 🔴 MUST be blocked — show user before dispatch
    tenant=os.environ.get("HERMES_TENANT"),
)["task_id"]

t2 = kanban_create(
    title="research: Postgres performance vs current",
    assignee="<profile-A>",
    body="Compare query latency, throughput...",
    initial_status="blocked",
)["task_id"]

# Show t1/t2 to user, get approval, then unblock
# After unblock, dispatcher picks them up

t3 = kanban_create(
    title="synthesize migration recommendation",
    assignee="<profile-B>",
    body="Read the findings from T1 (cost) and T2 (performance)...",
    parents=[t1, t2],
    initial_status="blocked",
)["task_id"]

t4 = kanban_create(
    title="draft decision memo",
    assignee="<profile-C>",
    body="Turn the analyst's recommendation into a 2-page memo...",
    parents=[t3],
    initial_status="blocked",
)["task_id"]
```

`parents=[...]` gates promotion — children stay in `todo` until every parent reaches `done`, then auto-promote to `ready`. No manual coordination needed; the dispatcher and dependency engine handle it.

### Step 4 — Subscribe to task notifications (while task is still blocked)

After creating each task (while it's still `blocked`), subscribe to notifications so the user gets pings when workers complete, block, or error:

**Do this BEFORE showing the task to the user and BEFORE unblocking.** Subscribing while blocked ensures the notification system is wired up before the worker ever starts.

```bash
hermes kanban notify-subscribe <task_id> --platform telegram --chat-id <user_chat_id>
```

**Subscribe to every task the user will care about**, not just the parent orchestrator task. Leaf tasks (coder, reviewer, researcher) are the ones whose completion the user wants to know about. Subscribe at creation time — you can list existing subscriptions with:

```bash
hermes kanban notify-list
```

**🔥 MUST — verify subscription was registered:**
```bash
hermes kanban notify-list | grep <task_id>
```
If the subscription doesn't appear, re-subscribe. Known issue (30 May 2026): notify-subscribe may return success without actually registering — always verify.

Subscriptions survive restarts (stored in the board's SQLite). Without this, completed tasks sit silent on the board and the user has to manually check.

**🔥 Quality gate — review the summary BEFORE showing to the user.**

When a task completes and its summary arrives (either via Telegram notification or when you poll), do NOT blindly show it to the user. First read it critically:

- Does it answer the user's question precisely, or is it vague/approximate?
- Does it contain ranges instead of exact values?
- Is there a missing piece the user explicitly asked for?

If the output is low-quality (vague, ranges, missing key data), **do NOT deliver it as-is**. Instead:
1. Check if you can quickly get the missing data yourself (web_extract on a better source, or a dedicated API)
2. Supplement the result: take the usable parts from the agent + add the missing parts yourself
3. Only then present the combined result to the user
4. **Fix the root cause for recurring issues.** If the same profile consistently returns low-quality data (ranges instead of exact values, unverified prices, vague summaries), don't just supplement — patch the profile's SOUL.md with verification rules. Add: (a) «Точные данные — не диапазоны» rule, (b) «Верификация 2+ источников» rule, (c) «Использовать domain-specific API (aviasales-api для билетов) вместо поиска» rule, (d) шаг верификации в workflow перед `kanban_complete`. One permanent fix to the SOUL.md saves dozens of future supplements.

Example from 30.05.2026: Researcher returned "7 000–12 000" for flight prices. User wanted exact "6 171". I first checked Яндекс.Расписания via web_extract, then used the **Aviasales Data API** (см. `references/aviasales-data-api.md`) which returned exact prices (9 886 ₽) plus a purchase link. Supplemented the agent's vague output with API-precise data + purchase links before showing to the user. The Aviasales API is the preferred supplement tool for flight prices — instant, zero tokens, exact numbers.

Don't be a passive pipe between Kanban workers and the user. Be the quality gate.

### Dedicated skill for flight prices

The `search/aviasales-api` skill wraps the Travelpayouts API with exact endpoints, token handling, and fallback sources. When creating researcher tasks for flight prices, use `--skill aviasales-api` so the worker loads it automatically. See `references/aviasales-data-api.md` for the raw API reference.

### Step 5 — Complete your own task

If you were spawned as a task yourself (e.g. a planner profile was assigned `T0: "investigate Postgres migration"`), mark it done with a summary of what you created:

```python
kanban_complete(
    summary="decomposed into T1-T4: 2 research lanes in parallel, 1 synthesis on their outputs, 1 prose draft on the recommendation",
    metadata={
        "task_graph": {
            "T1": {"assignee": "<profile-A>", "parents": []},
            "T2": {"assignee": "<profile-A>", "parents": []},
            "T3": {"assignee": "<profile-B>", "parents": ["T1", "T2"]},
            "T4": {"assignee": "<profile-C>", "parents": ["T3"]},
        },
    },
)
```

### Step 5 — Report back to the user

Tell them what you created in plain prose, naming the actual profiles you used:

> I've queued 4 tasks:
> - **T1** (`<profile-A>`): cost comparison
> - **T2** (`<profile-A>`): performance comparison, in parallel with T1
> - **T3** (`<profile-B>`): synthesizes T1 + T2 into a recommendation
> - **T4** (`<profile-C>`): turns T3 into a CTO memo
>
> The dispatcher will pick up T1 and T2 now. T3 starts when both finish. You'll get a gateway ping when T4 completes. Use the dashboard or `hermes kanban tail <id>` to follow along.

## Common patterns

**Fan-out + fan-in (research → synthesize):** N research-style cards with no parents, one synthesis card with all of them as parents.

**Structured Market Research (3+1 pattern):** A concrete instantiation of fan-out + fan-in for exploring monetization / product-market fit options. Use when the user needs to explore a business opportunity from multiple angles before deciding.

**When to use:** User says «нужно исследовать все возможные варианты» about a product/platform they already have. The goal is enumeration + comparison + recommendation.

**Structure:**
```
T1 ─┐  Competitors & market          (researcher)
T2 ─┼─► T4  Synthesis + top-3        (researcher)
T3 ─┘  Sales channels & biz models   (researcher)
```
Optionally: a fourth parallel researcher for data-products/features if the platform is rich.

**Body guidelines for each lane:**
- Keep each task ≤ 1500 chars. A lane covers ONE dimension.
- Include concrete context about the existing platform (what it does, what data it has, what APIs exist).
- Include explicit research questions per lane — researcher needs direction.
- End every body with: `После завершения: 1. Сохрани полный отчёт в /home/hermes/.hermes/kanban/results/{task_id}.md 2. Вызови kanban_complete(summary="Кратко: ...", artifacts=["/home/hermes/.hermes/kanban/results/{task_id}.md"]) НЕ используй clarify — в Kanban нет пользователя.`

**Synthesis task (T4):**
- Has `parents=[T1, T2, T3]` — auto-promotes when all 3 complete.
- Body should instruct: read results from Obsidian (agents-data/Researcher/), produce unified comparison table, recommend top-3, include risks and MVP plan.
- --max-runtime: 45m (more work than individual lanes).

**Lifecycle (same as all orchestrated pipelines):**
1. Create all 4 tasks with `--initial-status blocked` and `--max-runtime 30m` for researchers, 45m for synthesis
2. Subscribe to all 4: `hermes kanban notify-subscribe <id> --platform telegram --chat-id <chat_id>`
3. Show user the full structure — task graph, profiles, dimensions
4. Get explicit approval
5. Promote all ready tasks: `hermes kanban promote T1 T2 T3`
6. Dispatch: `hermes kanban dispatch --max 1`
7. Synthesis auto-starts when researchers complete (parent dependency)

**Known pitfalls from real session (01.06.2026):**
- Creating duplicate tasks: check `hermes kanban list` BEFORE creating — if tasks with identical names already exist (e.g. from a previous attempt that was interrupted), block/archive them first, THEN create new ones. Create tasks one at a time via separate terminal calls, not a bulk script — shell quoting of long bodies across multiple create calls can produce duplicates if dispatch catches them mid-script.
- Verify subscription after creation: `hermes kanban notify-list | grep <task_id>` — known bug where subscribe returns success but doesn't register.
- Synthesis task has `--initial-status blocked` AND parent links. Parent dependencies only promote `todo` tasks to `ready`, not `blocked`. To make synthesis auto-start after parents complete, create it with `initial_status="blocked"` and manually unblock it after parents finish. Or create without blocked status — the parent dependency prevents it from starting early.

**Parallel implementation + validation:** one implementer card makes the change while one explorer/researcher card verifies config, docs, or source mapping. A reviewer card can depend on both. Do not make the implementer own unrelated verification just because the user mentioned both in one sentence.

**Vision-First pipeline (spec → implement → review with user gates):** The most important pattern for preventing agent drift. Three hard gates where the user must approve before the pipeline advances:

1. **Gate 1: User vision → Acceptance Criteria.** Orchestrator asks clarifying questions, writes acceptance criteria in human language, shows to user. User says "да, это то." Only then proceed.
2. **Gate 2: Architect spec → User approval.** Architect writes spec with `## Acceptance Criteria` section. The user (or the user's assistant/manager) reads it and approves. Only then create coder tasks.
3. **Gate 3: Reviewer validation against criteria.** Reviewer checks code against both code quality AND acceptance criteria. If criteria are not met → `kanban_block` with specific failed criteria. If criteria are met but code quality has issues → `kanban_complete` with findings (fixes can be done later).

Task graph (all created at once with parent links, architect task waits for gate 1 approval):
```python
# Gate 1 already passed — user approved acceptance criteria

t_spec = kanban_create(
    title="spec: [feature] architecture",
    assignee="architect",
    body="Write spec with ## Acceptance Criteria. Criteria:\n1. ...\n2. ...\n\nInclude concrete file paths, interfaces, dependencies, edge cases.",
    workspace="dir:/home/hermes/projects/<repo>",
)[\"task_id\"]

# Coder and reviewer wait for spec. Orchestrator shows spec to user before advancing.
t_code = kanban_create(
    title="implement: [feature]",
    assignee="coder",
    body="STRICTLY follow the spec. Read parent task's spec before coding. TDD required. Acceptance Criteria are the law.",
    parents=[t_spec],
    workspace="dir:/home/hermes/projects/<repo>",
)[\"task_id\"]

t_review = kanban_create(
    title="review: [feature]",
    assignee="reviewer",
    body="Verify: code matches spec, all acceptance criteria met. Block ONLY if criteria are not met. Complete with findings for code quality issues.",
    parents=[t_code],
)[\"task_id\"]
```

The orchestrator's job after creating these: wait for `t_spec` to complete → read the spec → show it to the user → get approval → only then allow `t_code` to proceed. This can be done by either:
- Creating `t_code` only after user approves the spec (delayed creation)
- Creating all three at once but manually pausing `t_code` (not ideal — dispatcher may pick it up)
- Setting `t_code` body to include "Wait — do not start until orchestrator explicitly confirms user approved spec" (soft guard)

The delayed-creation approach is most reliable for production use.

**Sequential pipeline (spec → implement → review):** A simpler chain without the vision gates — use when the spec is already clear (e.g., from an existing document or a tiny change where the user already approved the approach).

```python
t_spec = kanban_create(
    title="Design auth architecture",
    assignee="architect",
    body="Design the auth module: endpoints, DB schema, middleware. Write spec in WORKSPACE/spec-auth.md.",
    workspace="dir:/home/hermes/kanban-test",
)["task_id"]

t_code = kanban_create(
    title="Implement auth module",
    assignee="coder",
    body="Implement auth per the architect's spec. Read spec from parent task's summary/metadata. TDD required. Commit and complete — there is already a downstream reviewer task.",
    parents=[t_spec],
    workspace="dir:/home/hermes/projects/<repo>",
)["task_id"]

t_review = kanban_create(
    title="Review auth implementation",
    assignee="reviewer",
    body="Verify implementation against spec. Check: correctness, security, test coverage, style.",
    parents=[t_code],
)["task_id"]
```

**Critical invariant — complete vs block.** When the coder is in a pipeline with a downstream reviewer card (linked via `parents`), they must `kanban_complete` — NOT `kanban_block` with `review-required`. The dependency engine promotes children only when parents reach `done`. A `kanban_block` leaves the coder task stuck in `blocked` status, so the reviewer card stays in `todo` forever. If a coder's SOUL.md says "block when done, for review", the orchestrator must either: (a) put a specific instruction in the task body telling the coder to complete instead, or (b) update the coder SOUL.md to distinguish pipeline vs ad-hoc patterns. The body instruction approach is safer because it's per-task.

**⚠️ SOUL.md is not always the root cause.** The `KANBAN_GUIDANCE` system prompt (`agent/prompt_builder.py`) historically contained a blanket "Do not complete a task you didn't actually finish. Block it." rule that EVERY worker saw. **This was fixed on 28 May 2026** — the three toxic instructions were replaced with complete-on-error semantics. If ALL profiles still exhibit block-on-error, check if the old patterns persist in `prompt_builder.py` (the fix may not be deployed to your checkout). See `references/kanban-guidance-block-trap.md` for full fix details.

**Coder with repo (worktree ПОД ВЕТО владельца 21.09.2026):** When the implementer needs a real git repo, set `workspace="dir:/home/hermes/projects/<repo>"` — worker edits the actual checkout, commits and pushes сам. Worktree-задачи НЕ создавать (`workspace="worktree"`, равно как `--project`+scratch — kanban резолвит проект в свежий worktree). Защита от конфликтов — **последовательный диспатч: один воркер на репозиторий**, следующую задачу того же репо dispatchать только после done+push предыдущей и чистого `git status --short`.

**Задачи в общем репозитории (ВЕТО владельца 21.08./21.09.2026):** только `--workspace dir:<абсолютный путь к репо>` + последовательный диспатч. Два воркера в одном дереве конфликтуют (реальный случай 20.08: зомби-процесс с `git checkout --`) — теперь это лечится сериализацией, а НЕ worktree. `--project <slug>` без явного `dir:` не использовать для репо-задач: kanban резолвит проект в worktree, что запрещено.

**⚠️ [LEGACY] Оркестратор мержит worktree-ветку в main после КАЖДОЙ done-задачи (только ветки, созданные до 21.09.2026; новых worktree не создавать).** Воркер коммитит в ветку `wt/<branch>` и НЕ мержит её сам — следующая задача стартует worktree от main и НЕ видит код предыдущей (тесты → реализация: «нет модуля», RED-тесты пропадают из дерева). Обязательная последовательность после каждой done-задачи в общем репо, ДО запуска следующей:
```bash
cd ~/projects/<repo>
git merge wt/<branch> --no-ff -m "merge: <что> (t_<task_id>)"   # имя ветки — git branch -a | grep wt/
git push
git log --oneline -2   # проверить: свежий merge-коммит в main?
```
Симптом пропуска: `git log --oneline -2` в main не показывает коммит воркера → ветка не смержена, мержи до диспатча следующей задачи.

**⚠️ Точное имя ветки — из `git branch -a | grep t_<task_id>`, НЕ угадывай по title (урок 21.08.2026, Этапы 8-9).** Для `--project <slug> --workspace worktree` ветка называется `lead-platform/t_<id>-<slugified-title>`, и слагификация НЕ совпадает с ожидаемой: «Этап 9: тесты ai-template (TDD, красные)» → `t_5f9e7def-9-ai-template-tdd`, «реализация 2/2 — сид + billing + E2E (8.4-8.6)» → `t_b10ba838-8-2-2-billing-e2e-8.4-8.6`, «доработка по ревью (M-1 M-2, L-1 L-3)» → `t_6fcbc8fd-8-m-1-m-2-l-1-l-3`. Симптом угадывания: `git merge lead-platform/t_<id>-<моё-имя>` → «not something we can merge», `git log` не двигается. Всегда перед merge: `git branch -a | grep t_<task_id>` (или `hermes kanban show <id> | grep branch`) → мержи ТОЧНУЮ ветку.

**⚠️ НЕ используй `..` в title Kanban-задачи, привязанной к репо (урок 21.08.2026, Этап 8).** Title транслитерируется в имя git-ветки worktree; `..` — невалидный символ (диапазон ревизий) → `git worktree add` падает `fatal: '<branch>' is not a valid branch name` → spawn_failed ×2 → диспетчер авто-блокирует задачу (Diagnostics: `workspace: git worktree add failed`). Реальный случай: «Этап 8: доработка по ревью (M-1..M-2, L-1, L-3)» → `lead-platform/t_8d2d197d-8-m-1..m-2-l-1-l-3`. Фикс: пересоздать задачу с названием без `..` («M-1 M-2»), старую заархивировать (`hermes kanban archive <id>`).

**⚠️ После merge проверь main на незакоммиченные правки (урок 21.08.2026, follow-up этапа 7).** Воркер может поправить файл ПРЯМО в main-чекауте (не в worktree) и не закоммитить — правка не попадёт ни в одну ветку. Реальный случай: после merge wt/stage7-fix2 `git status --short` в main показал ` M scripts/measure_ai_cost.py`, при этом в wt/stage7-fix1, wt/stage7-fix2 и HEAD файл был старым. Диагностика: `git show <wt-branch>:<file>` vs `git show HEAD:<file>` vs рабочий файл. Если правка корректна и нужна (напр. датакласс-доступ после M-4-типизации) — закоммить сам и запушь (`chore(ai): ...`); воркер не вернётся. Сделай `git status --short` после каждого merge — часть рутины.

Полный рецепт автономного ночного прогона (последовательность этапа, краш-паттерны, тайминги): `references/autonomous-night-run-crash-recovery.md`.

**⚠️ Merge-фаза волны фиксов — ревью безопасности, конфликты параллельных веток, salvage мёртвого воркера (урок 21.08.2026, lead-platform).** Когда мержишь НЕСКОЛЬКО worktree-веток подряд (параллельные воркеры, один репо) — оркестратор последний рубеж проверки:

1. **Смотри security-диффы ДО merge**: `git diff main..<branch> -- docker-compose.yml src/config.py src/interface/api/deps.py .env*`. Реальный случай: воркер dev-входа по ТЗ включил в compose `VITE_DEV_LOGIN=1` + `DEV_LOGIN_ALLOWED=1` — ровно ту дыру, которую пользователь запретил. Оркестратор запатчил ветку ДО merge (`fix(compose): не включать dev-вход в проде`) и только потом смержил. Код за флагом оставить можно, АКТИВАЦИЮ в проде — нет.
2. **Конфликты между параллельными ветками — норма**: общий `src/config.py`/`web/src/lib/telegram.ts` правят оба воркера → `git merge` падает `Aborting / ort failed`. Разрешать руками: взять ОБЕ стороны (пример: main добавил `super_admin: 800` в DEV_TG_IDS, ветка переименовала константу — объединить оба изменения), убрать маркеры `<<<<<<<`/`=======`/`>>>>>>>`, `git add` + merge-коммит. Проверка после: `grep -cE '^<<<<<<<|^>>>>>>>' <file>` → 0.
3. **Воркер умер, задача висит `running`, а код закоммичен — salvage**: `ps -p <pid>` пуст, но `git -C .worktrees/<id> log --oneline -1` показывает коммиты воркера (не main) → смержи ветку (разреши конфликты), закрой задачу САМ: `hermes kanban complete <id> --summary "..."` (CLI-флаг `--summary`). НЕ перезапускай воркера — он начнёт с нуля.
4. **Воркер может застейшить работу и rebase'нуться на свежий main**: worktree чистый (`status` пусто), но `git stash list` показывает `WIP on lead-platform/t_<id>-...` → воркер ЖИВ, обновляет ветку под новый main, потом pop. Не паникуй, не убивай; проверь `stash list` и лог воркера (растут `API call #N`).
5. **Два параллельных воркера пишут в ОДИН agent.log** профиля — различай по session id в строке лога (`[20260821_204632_b9f434]`), а не по профилю.
6. **`kanban_wait.py` врёт про завершение**: вывод `[t_x] ЗАВЕРШИЛАСЬ: ready` — это ЛЮБОЙ переход статуса, не обязательно `done`. Всегда сверяй `hermes kanban show <id> | grep status` перед мержем.
7. **CLI-квирки волны фиксов**: `hermes kanban list --project <slug>` — флага НЕТ (`unrecognized arguments: --project`), фильтруй `list` grep-ом по названию; `hermes kanban edit` — только для done-задач (backfill результата), тело ready-задачи не обновить → `archive` + `create` заново (готовую к запуску задачу с неверным ТЗ архивируй и создавай новую с правильным).

```python
kanban_create(
    title="Add /users endpoint",
    assignee="coder",
    body="Add GET /users with pagination. TDD. Commit when done.",
    workspace="dir:/home/hermes/projects/<repo>",
)
```

**Pipeline with gates:** `planner → implementer → reviewer`. Each stage's `parents=[previous_task]`. Reviewer blocks or completes with findings; if blocked, the operator unblocks with feedback and the cycle continues.

**Same-profile queue:** N tasks, all assigned to the same profile, no dependencies between them. Dispatcher serializes — that profile processes them in priority order, accumulating experience in its own memory.

**Human-in-the-loop:** Any task can `kanban_block()` to wait for input. Dispatcher respawns after `/unblock`. The comment thread carries the full context.

**Background fire-and-forget tasks:** Tasks that skip approval gate. Useful for refactoring, dependency updates, tests, docs, minor fixes.

When to use:
- Refactoring (renaming, extracting functions, cleanup)
- Dependency updates
- Test additions/fixes
- Minor fixes (typos, renaming, formatting)
- Documentation

When NOT to use (foreground with gate required):
- New feature
- Architecture change
- Critical bug
- Any task where user wants to see intermediate decisions

Implementation:
1. Body starts with `[background]` marker
2. Create with `--initial-status ready` (not blocked)
3. Notify-subscribe active, but approval gate skipped
4. Agent works → `kanban_complete` → result in Telegram
5. Orchestrator shows final result without pre-approval

See `references/improvement-roadmap.md` for full detail.

**Verification loop pattern (auto-review):** After a foreground coder task completes, auto-create a reviewer task with parent link. The reviewer checks that code meets `Done when` criteria from the parent coder task.

Rules (token-efficient):
- Reviewer on same cheap model (deepseek)
- `max_turns=12` (enough for reading diff + verdict)
- Task body: only "Проверь что код соответствует Done when из родительской задачи"
- If all OK → `kanban_complete(approved=True)`
- If issues → `kanban_comment` with specifics + `kanban_block`

When to add:
- Foreground coder tasks only (those that pass approval gate)
- NOT for background tasks
- NOT for researcher/debugger — different pipeline

See `references/improvement-roadmap.md` for full detail.

**File size discipline pattern:** Architect/planner tasks enforce file size limits. Smaller files = less context = fewer errors = easier reviews. Add this constraint to every architect task body:

```
Constraints: Each file ≤200 lines. If a module is larger, split into multiple files with clear responsibility boundaries.
```

Embed in the GCCD template for architect (see GCCD section above and `references/gccd-framework.md`).

**TDD pipeline pattern (тесты, реализация и РЕВЬЮ — РАЗДЕЛЬНЫЕ задачи):** Для каждого этапа разработки кода создавай ТРИ задачи вместо одной. Жёсткое требование пользователя (2026-08-19, Booking Platform):

1. **Задача N-T «Этап N: тесты (TDD, красные)»** — агент пишет ВСЕ тесты этапа из test-plan'а (unit/api/bot/integration). Никакого production-кода. Критерий приёмки: `pytest` → тесты ПАДАЮТ (RED).
2. **Задача N-R «Этап N: реализация по тестам (GREEN)»** — СЛЕДУЮЩИЙ агент реализует код до зелёного. **ТЕСТЫ НЕ МЕНЯТЬ — это контракт** (иначе реализатор «упростит» фичу под себя).
3. **Задача N-Rev «Этап N: ревью (reviewer)»** — третий агент проверяет: pytest зелёный, лимит строк ≤150 (wc -l), event-driven/DDD, edge cases, безопасность, соответствие спеке. Проблемы → `kanban_block` со списком замечаний; чисто → `kanban_complete`.
4. Цепочка: каркас → 1T → 1R → 1Rev → 2T → 2R → 2Rev → ... Каждая следующая зависит от предыдущей (parent link или последовательное создание после завершения). Тесты N+1 пишутся только после зелёной N-R и прошедшего N-Rev.
5. Перед 1T — задача «Создать проект-каркас» (структура папок, pyproject, docker-compose, git init + приватный репозиторий GitHub `gh repo create --private --source . --push`). Без логики — только скелет, чтобы тестам было куда ложиться.

**Цикл доработки (ревью не прошло):**
- Reviewer нашёл проблемы → `kanban_block N-Rev` с комментарием (СПИСОК замечаний, что чинить) + полный отчёт в /home/hermes/.hermes/kanban/results/{task_id}.md
- Оркестратор создаёт НОВУЮ задачу доработки на coder (title «Этап N: доработка по ревью (...)»), в body — замечания дословно; parent = задача ревью (реальная практика этапов 1-5: всегда новая карточка, не «та же задача»)
- ⚠️ Trapped child (урок 20.08.2026, Этап 5): доработка с parent=blocked-ревью застревает в `todo` — dependency engine ждёт `done` родителя, диспетчер не берёт (`Spawned: 0`). Решение: закрыть ревью с вердиктом `hermes kanban complete <review_id> --summary "Вердикт: BLOCKED — findings в отчёте, переданы в доработку <id>"` (вердикт уже в комментарии/отчёте, история не теряется) → дочерняя промоутнется в ready; затем unblock + dispatch. НЕ удалять заблокированное ревью и НЕ пересоздавать доработку.
- Coder чинит ровно замечания ревью (тесты не трогает) → `kanban_complete` (НЕ block — есть downstream повторное ревью) → оркестратор мержит worktree-ветку в main (см. «Оркестратор мержит worktree-ветку»)
- Повторное ревью: новая задача на reviewer (parent=доработка, blocked до OK пользователя) → цикл до зелёного
- **APPROVED с новыми MEDIUM «на follow-up» (урок 21.08.2026, Этап 7):** ревью может завершиться APPROVED (все AC выполнены, критерии приёмки закрыты), но перечислить новые MEDIUM «на follow-up, не блокеры» (напр. фиксы без тестов, непокрытая tenant-валидация, типизация). Если замечания реальные (безопасность/тесты/типизация) — НЕ игнорируй: создай follow-up задачу на coder (parent=ревью, body — замечания дословно), прогони, затем компактное третье ревью (только проверка пунктов follow-up). Реальный цикл: ревью1 BLOCKED (4M+4L) → доработка → ревью2 APPROVED + M-5/M-6 → follow-up (14 тестов + tenant-валидация service/specialist) → ревью3 APPROVED. Один LOW с пометкой ревьюера «на будущее» — можно зафиксировать в HANDOFF и не гонять цикл.
- `kanban complete` на уже завершённой задаче → «cannot complete (unknown id or terminal state)» — воркер сам закрыл, не дублировать, просто идти дальше
- **Стоп-кран:** после `failure_limit` (по умолчанию 2) неудачных попыток подряд задача авто-блокируется — остановиться и разобраться вручную (вероятно, проблема в спеке/плане, а не в коде)
- Реальный пример (Booking Platform, 20.08.2026): ревью нашло 3 MEDIUM + 3 LOW (docker-compose без app, EventBus убивал воркер при исключении, TenantMiddleware мёртвый код) → задача доработки → 22/22 PASS → повторное ревью

Body-шаблон задачи тестов:
```
Спека: <путь>. Тест-план: <путь>. План: <путь к задачам N>.
Написать ВСЕ тесты этапа N из тест-плана (unit/api/bot/integration).
Никакого production-кода. Запустить: pytest — тесты должны ПАДАТЬ (RED).
```

Body-шаблон задачи реализации:
```
Тесты уже написаны в задаче <id N-T>. Реализовать код до зелёного.
ТЕСТЫ НЕ МЕНЯТЬ — это контракт. Запустить: pytest -v — все PASS.
Лимит: файлы ≤150 строк, event-driven + DDD.
Типизация: датаклассы вместо Any/dict/tuple (см. coder SOUL.md §6).
```

Body-шаблон задачи ревью:
```
Реализация в задаче <id N-R>. Проверить: pytest -v, лимит ≤150 (wc -l),
event-driven/DDD, типизация (датаклассы вместо Any/dict/tuple), edge cases,
безопасность, соответствие спеке.
Проблемы → kanban_block с комментарием. Чисто → kanban_complete.
```

**⚠️ Типизация — датаклассы, не сырые структуры (user preference, 20.08.2026).** Пользователь жёстко требует в ЛЮБОМ коде: НИКАКИХ `Any`, голых `dict`/`list`/`tuple`/`set` без параметров, анонимных кортежей как структур (`tuple[str, int, float]`), словарей-структур (`payload = {"id": ...}`), `**kwargs` для передачи данных — вместо этого `@dataclass` (frozen, где возможно). Дополнительно: магические строки/числа → `Enum`, ID-сущностей → `NewType` (`UserId`, `TenantId`, `SpecialistId`), `TypedDict` только на границе JSON (API/БД), `**kwargs` в публичных сигнатурах запрещено, `Protocol` для интерфейсов. Внесено в SOUL.md coder (Architecture Standards §6 HARDLINE) и reviewer (правило 7 + чек-лист, нарушение = MEDIUM+). Оркестратор: включай краткую версию в Constraints/GCCD coder-задач и в body ревью — ревьюер проверит и зарепортит нарушения как MEDIUM+.

**⚠️ Не создавай задачу N-R заранее, если coder может создать её сам.** В реальной сессии coder, завершив задачу тестов, сам создал дочернюю задачу реализации (с parent-связью и детальным контекстом из своего workspace) — а у оркестратора уже была своя, созданная заранее. Получился дубликат, который пришлось архивировать. Правило: после завершения N-T проверь `hermes kanban list` — если coder уже создал N-R сам, заархивируй свою и разблокируй его (у неё есть parent-связь и правильный контекст); только если N-R не создана — создавай свою.

**⚠️ По одному этапу, не все сразу (user preference, 2026-08-19).** Для длинного TDD-пайплайна (8 этапов = 17+ задач) пользователь явно выбрал: создавать задачи ТОЛЬКО текущего этапа, а следующие этапы — по мере завершения предыдущих («давай по одному этапу»). НЕ создавай весь граф заранее — это мусор на доске и потерянный контроль темпа. Доска показывает: тесты → реализация → ревью текущего этапа; следующий этап появляется после зелёного ревью.

Исключения: маленькие фичи (1-2 файла) — одна задача, но строгий RED→GREEN внутри; прототипы/spike — пометить явно. Подробности: навык `test-driven-development`, раздел «TDD Pipeline через Kanban».

**⚠️ Автономный режим «не спрашивай, работай до утра» (user preference, 21.08.2026).** Пользователь может явно снять approval gate: «меня дальше не спрашивай, надеюсь до утра все сделаешь». Тогда:
- Покажи граф этапа ОДИН раз в начале, без ожидания OK на каждый этап
- Создавай задачи сразу `blocked` → `unblock` + dispatch, не спрашивая между этапами
- Гони всю цепочку до конца (все этапы плана, включая следующие), мержа каждую done-ветку в main
- Обновляй HANDOFF.md по ходу каждого этапа (устал — статус живёт там, а не в памяти)
- Утром — итоговый отчёт: что APPROVED, что осталось на доске
- Разрешённые остановки: только реальные блокеры, требующие решения человека. Краши/таймауты воркеров разруливай сам (перезапуск, ретрай, merge) — это НЕ повод будить пользователя

**⚠️ Не диспатчь новый этап в репозиторий, где уже идёт задача (20.08.2026).** У тех-долга этапа N и задач этапа N+1 ОБЩАЯ рабочая копия (один `~/projects/<repo>`). Два параллельных воркера в одном репо конфликтуют: одновременные коммиты, миграции alembic, pytest-прогоны. Реальный случай (Booking Platform): тех-долг t_37c38450 running на coder, задачи Этапа 3 созданы заранее (ready/todo с parent-связями), но диспатч НЕ запускался до завершения тех-долга. Правило: задачи следующего этапа создавай сразу (пользователь видит план на доске), но `hermes kanban dispatch` — только после того, как предыдущая задача в этом репо дошла до `done`. Проверка перед диспатчем: `hermes kanban show <id_предыдущей> | grep status`.

**⚠️ Проверяй пути в теле задачи перед unblock (20.08.2026).** Body задач из старых сессий может содержать устаревший путь к проекту. Реальный случай: тех-долг указывал `~/projects/booking-platform`, а код фактически в `~/projects/lead-platform` (проект переименован; старые body не обновляются автоматически). Перед unblock:
1. `ls ~/projects/` — сверить реальный путь с тем, что в body задачи
2. Не совпадает → `hermes kanban comment <id> "ВАЖНО: код в <реальный путь> (НЕ <старый>). Репо ..., ветка main."`
3. Только потом unblock + dispatch

Иначе воркер теряет минуты на несуществующую директорию и может зафейлиться с «нет такого пути».

**Порядок цепочки обеспечивают parent-связи, не приоритет.** Тесты (`ready`) → реализация (`todo`, `--parent тесты`) → ревью (`todo`, `--parent реализация`): дочерние не стартуют, пока родитель не `done`, независимо от приоритета. `--priority` — только tiebreaker среди одновременно `ready` задач (в этой сессии: тесты 30 → реализация 20 → ревью 10).

**Frontend-этапы в TDD-пайплайне (урок 20.08.2026, Booking Platform 4b):** для фронта (React/web) классического test-plan'а обычно НЕТ — план требует «build + ручной smoke». Проверенный формат:
1. **Реализация 1/2** — инфраструктура: скаффолд (Vite+Tailwind+shadcn), авторизация (initData), shell+роутинг. Дополнительно попросить воркера поставить **vitest** и написать тесты ключевой логики (api-клиент, useAuth, RoleRoute) — это сработало отлично: 16 vitest-тестов поймали контрактные проблемы ДО экранов.
2. **Реализация 2/2** — экраны + интеграция (CORS/static) + финальные проверки (`wc -l` ≤150, `npm run build`, `pytest` — не сломать backend).
3. **Ревью** — по критериям приёмки этапа + ролевые guards (specialist не видит «Статистику» и т.п.).

**Большой этап — группировка подзадач плана (урок 20.08.2026, Booking Platform этап 5):** план этапа может содержать 15 подзадач (5.1-5.15), но Kanban-граф НЕ должен повторять их 1:1. Проверенная разбивка: **1 задача тестов** (все тестовые файлы этапа из test-plan'а, RED, `--initial-status blocked`) → **N задач реализаций**, сгруппированных по доменам (ядро чата → эскалация → frontend → бот-меню; 2-4 подзадачи плана на одну Kanban-задачу) → **1 задача ревью** (включает финальную проверку: wc -l, полный pytest, build). Все реализации строго последовательные (parent-связи) — общее репо, параллельные воркеры конфликтуют. Дочерние задачи создаются БЕЗ `--initial-status` — parent-связь сама ставит их в `todo`, диспатчер не тронет до `done` родителя. Отдельную задачу «финальная проверка» из плана НЕ создавать — она дублирует чек-лист ревьюера (в этапах 1-4 ревьюер сам гонял pytest/wc -l/build).

**⚠️ Пути/контракты в плане могут устареть — разрешай воркеру сверяться с фактом (урок 20.08.2026, Этап 6).** План этапа 6 предписывал роутер `/api/v1/plans`, а в коде этапов 4-5 фактический prefix был `/api/admin` — воркер, слепо следующий плану, написал бы тесты на несуществующий путь. В тело задачи тестов добавляй явное разрешение: «Путь API из плана: X (проверить фактический prefix проекта — уточнить в conftest/роутерах и использовать фактический)». Аналогично для имён модулей (план: `domain/messaging/models.py`, факт: `src/domain/messaging/` — проект использует `src/`-префикс). Спека/план — ориентир, фактический код — источник истины для путей.

**⚠️ Контрактный дефицит API между фронтом и бэком (урок 20.08.2026):** frontend-воркер первым делом обнаружил, что его `GET /api/me` на бэкенде не существует (есть только `POST /api/auth/init`, который роль не возвращает). Правильное поведение воркера (закрепить в body): **НЕ расширять scope** — backend не трогать без отдельной задачи, а создать follow-up задачу (`blocked`) на недостающий эндпоинт и указать контракт (путь, ожидаемый ответ `{id, name, role}`). Оркестратор: такую follow-up разблокировать ДО задач экранов — без неё фронт не залогинится и экраны не протестировать.

**⚠️ Связка фронт↔бэк — пользователь хочет живую проверку (user preference, 20.08.2026):** «бэк запустить и тестировать, что ничего не отвалилось в связке с фронтом». При разработке фронта не ограничивайся `npm run build` + smoke — подними backend (uvicorn + Postgres) и проверь реальные запросы фронта к API (proxy 5173→8000). Бэк из docker-compose: `sg docker -c "docker compose up -d --build app"`; локально: сначала `uv sync` в проекте (без venv uvicorn из другого окружения не найдёт зависимости проекта — `ModuleNotFoundError: sqlalchemy`). Проверка после подъёма: `curl :8000/health`, открыть фронт в dev и пройти авторизацию.

**Self-improvement reminders pattern:** Not auto-fix, just a weekly reminder. Cronjob runs once a week (Sunday evening) with a short summary:
```
На неделе завершено N задач.
— Coder: M задач, среднее время X мин
— Researcher: K задач, Y источников
— Reviewer: Z задач
Стоит что-то улучшить в профилях/навыках?
```
User decides what to do. No auto-patching.

See `references/improvement-roadmap.md` for full detail.

## Pitfalls

**Read the board via `hermes kanban list` — never raw sqlite on kanban.db.** Probing `~/.hermes/kanban.db` with `python3 -c "import sqlite3..."` triggers the terminal approval gate (blocks waiting for user consent), while `hermes kanban list` / `hermes kanban show <id>` return the same info without prompting. For status checks, task listing, and verifying duplicates, always use the CLI. Raw sqlite is only for repair scenarios (e.g. `.corrupt` recovery), not for reading.

**`scheduled` status is a dead end — dispatcher only picks `ready` tasks.** If you call `hermes kanban schedule <id>`, the task transitions to `scheduled` status. The dispatcher (inside gateway) does NOT pick up `scheduled` tasks — it only picks `ready`. There is no direct `scheduled → ready` command (`promote` only works on `todo`/`blocked`, `block` doesn't work on `scheduled`). 

**Fix:** Call `hermes kanban unblock <id>` which transitions `scheduled` → `ready`. The dispatcher will then pick it up on the next tick.

**Lesson:** prefer `create --initial-status blocked` → `unblock` over `create` → `schedule`. The `blocked → ready` path is the intended lifecycle. Only use `schedule` when you explicitly want a task that won't be picked up automatically.

**Inventing profile names that don't exist.** The dispatcher silently fails to spawn unknown assignees — the card just sits in `ready` forever. Always assign to a profile from your Step 0 discovery; ask the user if you're unsure.

**Bundling independent lanes into one card.** If the user asks for two independent outcomes, create two cards. Example: "fix blockers and check model variants" is not one fixer task; create a fixer/engineer card for the fixes and an explorer/researcher card for the variant check, then optionally gate review on both.

**Over-linking because of wording.** "Finally check X" may still be parallel with implementation if X is static config, docs, or source discovery. Link it after implementation only when the check depends on the implementation result.

**Forgetting dependency links.** If the task graph says `research -> implement -> review`, do not create all tasks as independent ready cards. Use parent links so implement/review cannot run before their inputs exist.

**Reassignment vs. new task.** If a reviewer blocks with "needs changes," create a NEW task linked from the reviewer's task — don't re-run the same task with a stern look. The new task is assigned to the original implementer profile.

**`hermes kanban dispatch` — НЕ принимает task_id.** Частая ошибка: `hermes kanban dispatch t_xxxx` → `unrecognized arguments: t_xxxx`. Dispatch — это «прогон диспетчера» без аргументов, он сам подбирает ready-задачи:

```bash
# ❌ Ошибка — dispatch не принимает id
hermes kanban dispatch t_fb91c4c9

# ✅ Правильно — сначала unblock, потом прогон диспетчера
hermes kanban unblock t_fb91c4c9
hermes kanban dispatch --max 1   # подберёт ready-задачу сам
```

`--max N` ограничивает число спавнов за один прогон (полезно, когда готово несколько задач, а запустить нужно одну — например, строго последовательный TDD-пайплайн).

**`hermes kanban complete` — CLI syntax trap.** Закрытие задачи из CLI использует `--result` / `--summary` / `--metadata`, а НЕ `--artifacts`. Флаг `--artifacts` существует только в Python API (`kanban_complete(artifacts=[...])`), в CLI его нет:

```bash
# ✅ Правильно (CLI)
hermes kanban complete t_xxxx --result "Спек готов, путь: README.md"
hermes kanban complete t_xxxx --summary "Структурированный handoff для downstream-задач"

# ❌ Ошибка — unrecognized arguments: --artifacts
hermes kanban complete t_xxxx --artifacts "path/to/file.md"
```

Проверяй флаги через `hermes kanban complete --help` перед сложными вызовами.

**`hermes kanban create` — CLI syntax trap.** Title is a **positional argument**, not `--title`. Body goes through `--body`, not `--description`. The common first-time mistake:

```bash
# ❌ Wrong — --title and --description don't exist
hermes kanban create --title "Task" --description "Body"  # unrecognized arguments

# ✅ Correct — title is positional, body via --body
hermes kanban create "Task title" --body "Task body" --assignee coder
```

This is CLI-only — the Python API (`kanban_create(title=..., body=...)`) is unaffected. Double-check syntax via `hermes kanban create --help` before complex multi-flag calls.

**Body with multi-line content.** Использование `--body "$(cat file.md)"` ломает bash, если файл содержит несколько строк и специальные символы. Всегда используй `head -N` чтобы ограничить количество строк:

```bash
# ✅ Работает
hermes kanban create "Задача" --body "$(head -40 /tmp/body.md)" --assignee coder --initial-status blocked

# ❌ Ломает bash при multi-line
hermes kanban create "Задача" --body "$(cat /tmp/body.md)" --assignee coder
```

Если тело всё равно ломается — запиши его одной строкой или используй `--body` с коротким inline-текстом, а полный контекст добавь через `hermes kanban comment <id> "..."`

**Auto-dispatch catches unblocked tasks instantly.** If `dispatch_in_gateway: true` (the default), creating a task at `ready` status triggers an immediate spawn — the worker starts before you finish typing the response. This bypasses the approval gate entirely. The user sees a running task they never approved, which causes strong frustration.

**Always create with `initial_status="blocked"` (or `--initial-status blocked` via CLI).** The lifecycle is: create (blocked) → subscribe → show user → OK → unblock → dispatcher picks it up.

If you forget and the task auto-starts: immediately `kanban block <id> "created prematurely — awaiting user approval"` and explain to the user. Do NOT let it keep running — it wastes tokens on work the user may not want.

**CRITICAL — Never create duplicate tasks on the same topic.** When the user asks to adjust a task (change profile, refine body, reassign from self-improver to researcher), do NOT create a new task while the old one is still running. Instead:
1. First, block or archive the old running task with a reason like "replaced by reassigned task"
2. Only then create the new task
3. Verify with `hermes kanban list` that only ONE task per topic is running

Failing to do this floods the Kanban board with concurrent workers on the same problem, wasting tokens and confusing the user. Symptom: user frustration ("ну не дибил ли", "все задачи падают в блок").

**Profile swap protocol.** When the user asks to assign a task to a different profile than originally planned:
1. If the original task is still running — block it first (`hermes kanban block <id> reassigned to <new-profile>`)
2. Create the new task with the correct assignee
3. Verify only one task exists for this topic via `hermes kanban list`
4. Do NOT let two tasks on the same topic run in parallel

**Self-improver profile.** Self-improver is configured for analysis and planning. All profiles on this setup run deepseek, so self-improver uses deepseek. If the user questions the model — confirm their preference. If they insist on reassigning, follow the profile swap protocol (block old → create new).

**Verify after dispatch.** After `hermes kanban dispatch --max 1`, check with `hermes kanban list` that the intended task is now `running`. If dispatch reports `Spawned: 0` but the task is already running (picked up by daemon), that's fine — acknowledge to the user. Do NOT create a duplicate task because dispatch seemed to do nothing.

**First-time setup: you MUST know the user's platform and chat_id before subscribe works.** If you've never done `notify-subscribe` before, you don't have the delivery coordinates. Get them early:

1. **Ask the user** directly: «На какой канал/чат слать результат?»
2. **Or discover via** `send_message(action='list')` — shows all connected channels with chat_ids.
3. **Or check memory** — if known from a prior session, it's saved there.

**Once known, save to memory immediately** so future sessions don't re-ask the user:
```
memory(action='replace', target='memory', old_text='Kanban create:', content='...subscribe(platform=telegram,chat_id=XXXXXX)...')
```

**If you DON'T know the chat_id AND can't ask (e.g. it's your first Kanban task for this user):** create the task anyway, then manually deliver the result here in the chat. The user will correct you, and you'll learn the chat_id for next time.

---

**Notify-subscribe may not be reliable (observed 29-30 May 2026).** `hermes kanban notify-subscribe` may return success without actually registering the subscription — the task never appears in `hermes kanban notify-list`. Additionally, archived tasks lose their subscriptions. Symptoms: user expects a Telegram ping but gets nothing. **Tested 30.05.2026:** subscription was registered (appeared in notify-list), task completed with summary, but no Telegram notification arrived. Workaround: verify subscription immediately with `hermes kanban notify-list | grep <task_id>`; if missing, re-subscribe. For critical tasks, poll `hermes kanban show <task_id>` as the primary delivery mechanism — check status 2-3 minutes after expected completion and show the summary to the user manually. Do NOT rely solely on notifications for delivery.

**⚠️ Notify-subscribe delivers only the task title, not the summary (observed 03.06.2026).** Even when notify-subscribe works correctly, the delivered message is a brief summary line — `✔ @profile Kanban t_XXXX done — Title`. The full `kanban_complete(summary=...)` content stays in the Kanban SQLite database, NOT in the Telegram notification. Neither the orchestrator nor the user sees the actual result in the notification.

**✅ Solution: use `artifacts=[]` in kanban_complete — built-in, zero extra work.**

The gateway has a built-in `_deliver_kanban_artifacts()` (gateway/run.py, line 5042) that auto-delivers files when `kanban_complete(artifacts=[...])` is called. The file arrives as a **native attachment** in Telegram right after the done notification. No polling, no extra reads.

Add this instruction to EVERY Kanban task body (replace the old bare `kanban_complete` instruction):

```
После завершения:
1. Сохрани полный отчёт в /home/hermes/.hermes/kanban/results/{task_id}.md
2. Вызови kanban_complete(summary="Кратко: <одна строка>", artifacts=["/home/hermes/.hermes/kanban/results/{task_id}.md"])
НЕ используй clarify — в Kanban нет пользователя.
```

What happens:
- Telegram gets: `✔ @profile Kanban t_XXXX done — Title` (first 200 chars of summary)
- **Immediately after:** the `.md` file arrives as a downloadable document
- User opens the file → full report
- Zero extra actions for orchestrator or user

**Why the old approach is worse:** Saving without `artifacts=` means the orchestrator must manually read the file and present it. With `artifacts=`, delivery is fully automatic — the gateway sends the file alongside the notification.

**Prerequisite:** ensure the directory exists:
```bash
mkdir -p /home/hermes/.hermes/kanban/results
```

**`hermes kanban list` may show completed tasks as running (observed 29 May 2026).** Tasks that are actually `status: done` with a completed run may appear in `hermes kanban list` with a `● running` indicator. This misleads the orchestrator into thinking the task is actively working when it's already finished. Root cause under investigation (task `t_995ff2b6`).

**Diagnostic workflow for «stuck running» tasks:**
1. `hermes kanban list` — see which tasks show `● running`
2. `hermes kanban show <id>` — check real `status:` field. If it says `done` with a `completed:` timestamp, the task is finished despite the list indicator
3. Archive completed tasks: `hermes kanban archive <id>`
4. For genuinely stuck tasks (spawned but never completed, no `completed:` field): create a new task or use `delegate_task` bypass
5. If a display bug is suspected (running → actually done): create a debugger task to investigate

**Do NOT** re-dispatch or duplicate a task that's showing `running` in list but is actually `done` — verify with `show` first.

**Argument order for links.** `kanban_link(parent_id=..., child_id=...)` — parent first. Mixing them up demotes the wrong task to `todo`.

**Don't pre-create the whole graph if the shape depends on intermediate findings.** If T3's structure depends on what T1 and T2 find, let T3 exist as a "synthesize findings" task whose own first step is to read parent handoffs and plan the rest. Orchestrators can spawn orchestrators.

**Tenant inheritance.** If `HERMES_TENANT` is set in your env, pass `tenant=os.environ.get("HERMES_TENANT")` on every `kanban_create` call so child tasks stay in the same namespace.

**Coder's SOUL.md says "block, don't complete".** Many coding profiles have a SOUL.md that says "after writing code, kanban_block with review-required". This breaks sequential pipelines — the downstream reviewer task stays in todo forever because the dependency engine only promotes children when the parent reaches done. Workaround: explicitly tell the coder in the task body to kanban_complete instead: "kanban_complete when done — there is already a reviewer task gated on you." The body instruction overrides the profile's SOUL.md for this run. If this happens repeatedly, update the coder profile's SOUL.md to distinguish pipeline mode (complete) from ad-hoc mode (block).

**Also applies to reviewer profiles.** The same problem occurs when a reviewer's SOUL.md says "if issues found → kanban_block". In a sequential pipeline, a blocking reviewer stops the entire chain. The orchestrator should either: (a) explicitly tell the reviewer in the task body to complete with findings instead of blocking, or (b) update the reviewer's SOUL.md to always complete. Option (b) is more reliable — once fixed, all future pipeline reviews work.\n\n**Meta-block trap: do NOT delegate Kanban-blocking fixes to Kanban.** If the problem IS agents blocking instead of completing, creating a Kanban task to investigate will produce another blocked task (because the same lifecycle governs the fixer agent). Break the cycle: analyze `prompt_builder.py` directly, compile a plan, show the user, get approval, apply patches. No Kanban, no Claude Sonnet — just code reading and patching.

### KANBAN_GUIDANCE — the root cause deeper than SOUL.md

The `KANBAN_GUIDANCE` block in `agent/prompt_builder.py` is auto-injected into EVERY kanban worker's system prompt. It contains THREE instructions that together create the "block instead of complete" trap:

```python
# 🔴 TOXIC INSTRUCTION 1 (most harmful) — prompt_builder.py, line 238
"Do not complete a task you didn't actually finish. Block it."

# 🔴 TOXIC INSTRUCTION 2 — prompt_builder.py, lines 212-219
"if your output is a code change that needs human review... end with
 kanban_block(reason=\"review-required: <one-line-summary>\")"

# 🟡 TOXIC INSTRUCTION 3 — prompt_builder.py, lines 202-205
"Block on genuine ambiguity. If you need a human decision you cannot
 infer (missing credentials, UX choice, paywalled source...)"
```

**How they interact:**
- Instruction 1 tells the agent: "error = not finished = block." This is the blanket catch-all.
- Instruction 2 tells coders: "after writing code, block with review-required." This breaks pipelines with parent-linked reviewer tasks.
- Instruction 3 is meant for genuine ambiguity but agents interpret technical errors (API failure, parse error, timeout) as "ambiguity" because of the broad framing of Instruction 1.

**These override any SOUL.md instructions.** Even if your coder/reviewer SOUL.md says "complete with findings", Instruction 1 ("don't complete unless you actually finished") takes precedence because it's in the system prompt. The orchestrator's body instruction workaround still works, but it's fragile — the agent may ignore it if the system prompt feels more authoritative.

**The actual fix (targets `agent/prompt_builder.py`):**

| Line | Was | → | Should be |
|------|-----|---|-----------|
| 238 | `Do not complete a task you didn't actually finish. Block it.` | → | `If you encounter an error, complete the task with an error summary in metadata. Only block for human-decidable ambiguity (missing credentials, UX choice). Technical errors (API failures, parse errors, timeouts) are NOT ambiguity — complete with error summary.` |
| 212-219 | `kanban_block(reason="review-required: ...")` | → | Remove block. Use `kanban_comment` with details + `kanban_complete`. Pipelines are governed by parent links, not by blocking. |
| 202-205 | `Block on genuine ambiguity...` | → | Add explicit exclusion: `Technical errors (API failures, parse errors, timeouts) are NOT ambiguity — complete with error summary in metadata.` |

**Symptoms that signal this root cause vs. a SOUL.md issue:**
- ALL profiles (coder, researcher, architect, reviewer) exhibit the same block-on-error behavior, not just one
- The task body says "complete when done" but the agent blocks anyway on error
- No SOUL.md contains `kanban_block` — the behavior comes from the system prompt

**Diagnostic:** grep `prompt_builder.py` for the three toxic patterns above. If present, fix `prompt_builder.py` first (see `references/kanban-guidance-block-trap.md` for patch commands). **As of 28 May 2026, this fix has been applied** — the old patterns no longer exist in the current checkout.

See `references/kanban-guidance-block-trap.md` for the full analysis context (session transcript, line-by-line breakdown).

**Post-fix verification protocol:** After patching KANBAN_GUIDANCE, verify EVERY profile in sequence with a minimal test task:
1. Start with the simplest profile (worker — file create)
2. Progress through architect → coder → debugger → researcher → reviewer
3. Each must `kanban_complete` (not `blocked`) within 60s
4. Clean up artifacts and archive after each test
5. If any crashes, check `--skills` flag first (most common cause is missing symlink)
6. Researcher tests may take 3+ minutes (web_search latency) — this is normal, not a crash

The full test sequence from the 28 May 2026 fix session: worker (50s ✅), architect (31s ✅), coder (39s ✅), debugger (15s ✅), researcher (187s ✅).

**Reviewer tasks need more max_turns — 40 НЕ достаточно для полного ревью.** Reviewers read code, cross-reference specs, run tests, and write structured reports — this uses more iterations than simple coder tasks. Реальный факт (20.08.2026, Booking Platform этап 4a): reviewer с `max_turns: 40` упёрся в `Iteration budget exhausted (40/40)` на ревью 12-пунктового чек-листа (3 прогона pytest, проверка миграции на чистой БД, edge probe) — вердикт остался в логе, комментировать/завершать пришлось оркестратору. После подъёма до 100 ревью этапа проходит без таймаута. **Правило: профилю reviewer ставь `agent.max_turns = 100`** (не 40):
```bash
hermes -p reviewer config set agent.max_turns 100
```
Для маленьких ревью (1 файл, 1 фикс) 40 хватает, но 100 не вредит — лишние итерации не тратятся, если не нужны. Текущие значения профилей (20.08.2026): coder=100, reviewer=100, researcher=45, architect=45, debugger=40, worker=20.

**Profiles missing kanban-worker skill crash with "Unknown skill(s): kanban-worker".** The `kanban-worker` skill is NOT automatically available in every profile's skills directory. When `hermes -p <profile>` starts, the CLI resolves skills from the **profile-scoped** skills dir (`<profile_home>/skills/`), NOT the default root. If the skill is missing there, the CLI immediately crashes with `Error: Unknown skill(s): kanban-worker` (exit code 1), not silently. The dispatcher then detects "pid not alive" and retries, creating a crash loop.

**Auto-repair (modern dispatcher):** The `_kanban_worker_skill_available()` function in `kanban_db.py` delegates to `_ensure_profile_skill(hermes_home, "kanban-worker")`, which **automatically creates the symlink** when it detects the bundled skill exists in the default root but the profile lacks it. Before returning, it runs `skills_root.mkdir(parents=True, exist_ok=True)` and `os.symlink(bundled, link_target)`. This means the first spawn attempt for a new profile self-heals — no manual action needed.

**Fallback — manual fix (legacy):** If running an older dispatcher, or if auto-repair fails due to permissions:
```bash
ln -sf ~/.hermes/skills/devops/kanban-worker ~/.hermes/profiles/<profile>/skills/kanban-worker
```

**Diagnosing:** Check the worker log at `<kanban_root>/logs/<task_id>.log` for `Error: Unknown skill(s): kanban-worker`. With auto-repair, this should only happen on old dispatchers.

**Symlink exists but still crashes:** Check:
  - **Broken symlink:** `readlink -f` resolves to a valid file? Re-run `ln -sf`.
  - **Custom HERMES_HOME:** If the profile config sets `hermes_home` override, auto-repair creates the symlink in the correct path (it follows `HERMES_HOME` from spawn env), but verify manually.
  - **Wrong category path:** Target must be `devops/kanban-worker/` (the full category subpath), not just `kanban-worker/`.
  - **Duplicate presence: top-level symlink + category subdirectory both exist.** When auto-repair creates a top-level `kanban-worker` symlink AND the profile already has `devops/kanban-worker/` as a proper subdirectory (common when profile is created from a template with all skills), the error is `Unknown skill(s): kanban-worker` (NOT `Ambiguous skill name`). The CLI cannot resolve the skill name because the bundle manifest finds the skill in the category path but the symlink at the top level confuses resolution. Fix: delete the top-level symlink: `rm ~/.hermes/profiles/<profile>/skills/kanban-worker`. Verify: `hermes -p <profile> --skills kanban-worker chat -q "test"` starts successfully. Symptom: log shows `Error: Unknown skill(s): kanban-worker` repeated, `skills list` shows `kanban-worker` as present, but `--skills kanban-worker` fails.

**Same for other profile-scoped skills.** Any skill referenced via `--skills <name>` in a kanban task must exist in the profile's skills directory. If the skill is only in the default root, the worker crashes the same way.

**Auto-repair (modern dispatcher v3.4+):** The `_ensure_profile_skill()` function in `kanban_db.py` handles ALL skills generically — not just `kanban-worker`. Before dispatching, it checks each skill in ``task.skills``, searches the default root for it (across all category subdirectories: devops, software-development, search, research, etc.), and auto-creates a symlink into the profile skills dir. This means any skill that exists in the default root is automatically made available to the profile on first spawn. No per-skill configuration needed.

**Kanban-worker is special — do NOT symlink it into profile skills dirs.**

Unlike all other skills, `kanban-worker` must live ONLY in the default root (`~/.hermes/skills/devops/kanban-worker/`). If you symlink it into a profile's skills dir (manually or via `sync_profile_skills.py`), the dispatcher sets `HERMES_HOME=<profile_dir>` before spawning, and `skill_view('kanban-worker')` finds the skill in **two places** — the profile dir (via symlink) AND the default root — raising `Ambiguous skill name 'kanban-worker': 2 skills match`.

This is a **worse crash** than the missing-skill one, and it loops the same way.

The lifecycle contract ships via the `KANBAN_GUIDANCE` system prompt block, NOT from the skill file. If `_kanban_worker_skill_available()` returns False (no profile-level symlink), the dispatcher simply skips `--skills kanban-worker` and the worker starts clean.

**Recursive symlinks in skill directories cause duplicate entries.** If a skill dir contains a symlink pointing to itself (`kanban-worker -> ../kanban-worker`), `skills_list` shows the skill 20+ times. **Diagnostic:** `ls -la ~/.hermes/skills/<category>/<skill>/` — look for a self-referencing symlink. **Fix:** delete it and verify with `skills_list`.

**Fix if profile dirs have kanban-worker symlinks:**
```bash
find ~/.hermes/profiles/*/skills -name "kanban-worker" -delete
```

**Verify no ambiguity:**
```bash
hermes -p <profile> --skills kanban-worker chat -q "test" 2>&1 | head -3
# Should NOT show "Unknown skill(s): kanban-worker"  
# Should NOT show "Ambiguous skill name"
```

**For all OTHER skills** (writing-plans, TDD, subagent-driven-development, etc.) — symlinks in profile dirs are correct and necessary, because those skills are NOT in the default root. The existing auto-repair and manual `ln -sf` instructions below apply to them.
```bash
# Find the skill in the default root first:
find ~/.hermes/skills/ -name "SKILL.md" -path "*/<skill-name>/SKILL.md" | head -1 | xargs dirname
# Then symlink the parent directory into the profile:
ln -sf /path/to/found/skill ~/.hermes/profiles/<profile>/skills/<skill-name>
```

**Orchestrator profile itself missing skills.** The orchestrator profile needs its own skills symlinked to properly decompose and route work. Without `writing-plans`, the orchestrator has no structured decomposition playbook. Without `subagent-driven-development`, it can't orchestrate the 2-stage review pipeline. Symlink these into the orchestrator profile:
```bash
ln -sf ~/.hermes/skills/software-development/writing-plans ~/.hermes/profiles/orchestrator/skills/writing-plans
ln -sf ~/.hermes/skills/software-development/subagent-driven-development ~/.hermes/profiles/orchestrator/skills/subagent-driven-development
```
The orchestrator's SOUL.md should also list available profiles (including newly created ones like `skill-writer`) so it can route to them. Update SOUL.md whenever a new specialist profile is added to the fleet.

## Visual Dashboard

Kanban has a **web UI dashboard** — drag-drop cards, comment threads,
live WebSocket updates, Recovery drawer for stuck workers. Open it:

```bash
hermes dashboard
```

See `references/failure-pattern-duplicate-fanout.md` for a real failure pattern (28 May 2026) — duplicate tasks flooding the board when the orchestrator failed to block-and-replace before creating a new task.

See `references/accessing-kanban-dashboard.md` for full details (auth,
custom ports, LAN access).

## Parent agent feedback during execution

When you (the user's assistant) create Kanban tasks and then wait for them to complete, **the user needs status updates**. Silent waiting frustrates users — they don't know if the system is working, stuck, or crashed. Follow this feedback protocol:

1. **Immediately after dispatching**: tell the user what tasks were created and which profiles are working. Show the task graph.
2. **After subscribing**: tell the user they'll get notified when tasks complete.
3. **Every 2-3 minutes of idle wait**: send a brief status update: "Coder still working on X, reviewer finished Y, 2 tasks left."
4. **When a task blocks**: tell the user what blocked and why, before fixing it. Don't silently unblock without context.
5. **On completion**: summarize what was accomplished — don't just say "done."

Use `hermes kanban list` or `hermes kanban show <task_id>` to check status when the user asks. Prefer notify-subscribe over polling with sleep.

**⚠️ НЕ используй фоновые watcher-скрипты для ожидания задач (user preference, 20.08.2026).** Первая версия этого навыка учила ставить `kanban_watch.sh` в background + notify_on_complete. Пользователь это отверг («watcher хуйня из-за которой ты завис») — фоновый процесс создаёт шум, путает уведомления и заставляет оркестратора «зависать» на обработке watcher-событий вместо работы. **Правильный способ — foreground timeout-цикл одной командой:**

```bash
cd ~/.hermes && hermes kanban unblock <task_id> 2>&1 && hermes kanban dispatch --max 1 2>&1 | tail -3
# затем ОДНА команда, которая блокирует до завершения (или таймаута):
timeout 550 bash -c 'while true; do S=$(hermes kanban show <task_id> 2>/dev/null | grep -E "^  status:" | awk "{print \$2}"); if [ "$S" = "done" ] || [ "$S" = "blocked" ]; then echo "STATUS: $S"; break; fi; sleep 15; done' 2>&1
# после цикла — сразу показать summary:
hermes kanban show <task_id> 2>&1 | sed -n '/status:/p;/Latest summary/,/Events/p' | head -20
```

- `timeout 550` — максимальное ожидание (foreground-лимит 600 сек; не превышай). Если задача дольше — запусти цикл повторно.
- `sleep 15` — частота опроса. Не делай чаще (лишние процессы hermes show).
- После выхода из цикла сразу покажи summary — это то, что watcher пытался делать, но с шумом.
- Для LONG задач (реализация этапа, большие фиксы) — цикл может упереться в таймаут; просто запусти его ещё раз.
- Если пользователь спрашивает «не зависло ли?» — покажи реальную активность воркера (см. ниже), а не «running».

**Проверка «жив ли воркер» (когда пользователь спрашивает «не зависло ли?»):** не ограничивайся статусом running — покажи реальную активность:
```bash
# Процесс жив? (etime = сколько работает, pcpu = активен ли)
ps -o pid,etime,pcpu,cmd -p $(pgrep -f "kanban task <task_id>" | head -1) 2>/dev/null
# Что воркер делает прямо сейчас (последние строки лога)
tail -10 ~/.hermes/profiles/<profile>/logs/agent.log | grep -v "^\s*$"
```
API-вызовы в логе (`API call #N`) и `tool terminal completed` = воркер активно работает, не завис. Это позволяет ответить пользователю конкретикой («ревьюер уже на 5-м API-вызове, проверяет код»), а не абстрактным «работает».

**Parallel task monitoring protocol:** When multiple independent tasks run simultaneously (e.g., 2+ coder tasks in parallel), track ALL of them:

1. After dispatch, wait ~30-60s then check ALL tasks: `hermes kanban show T1` + `hermes kanban show T2`
2. If some are still `running` and some are `done`, check the logs of the running ones for progress: `hermes kanban log <task_id> | tail -10` — this shows what the worker is doing (patching, testing, etc.) without needing to read the full event log
3. Continue checking every 60-90s until all are done or the user asks
4. For long-running tasks (>3 min), read intermediate logs to give the user meaningful progress updates ("worker found a bug in gitmark.py exit code, fixing it...")
5. When all complete, present results for each task, grouped by status

This is preferable to a single long `sleep N && show` because parallel tasks complete at different times — checking all of them gives a complete picture.

The one exception: background tasks the user explicitly said not to bother them about. Always clarify upfront: "I'll notify you when done, or you can check the board anytime."

## Recovering stuck workers

When a worker profile keeps crashing, hallucinating, or getting blocked by its own mistakes (usually: wrong model, missing skill, broken credential), the kanban dashboard flags the task with a ⚠ badge and opens a **Recovery** section in the drawer. Three primary actions:

1. **Reclaim** (or `hermes kanban reclaim <task_id>`) — abort the running worker immediately and reset the task to `ready`. The existing claim TTL is ~15 min; this is the fast path out.
2. **Reassign** (or `hermes kanban reassign <task_id> <new-profile> --reclaim`) — switch the task to a different profile (one that exists on this setup) and let the dispatcher pick it up with a fresh worker.
3. **Change profile model** — the dashboard prints a copy-paste hint for `hermes -p <profile> model` since profile config lives on disk; edit it in a terminal, then Reclaim to retry with the new model.

### Handling a blocked pipeline task

When a task in a sequential pipeline (e.g., `architect → coder → reviewer`) is `blocked` and the pipeline is stuck, follow this recovery protocol instead of blindly unblocking:

1. **Read the blocked task's comment thread.** If the blocker is a `review-required` from the reviewer, they found real issues — don't unblock and retry the same reviewer. Create a new fix task assigned to the original implementer instead.
2. **Fix the code** (either yourself or create a new coder task) → commit → then unblock the reviewer task and reassign it to the reviewer profile.
3. **If the blocker is a crash (max_turns exhausted, non-zero exit)**, read the run log first. Common causes:
   - `Iteration budget exhausted (N/N)` → increase `agent.max_turns` in the profile's config.yaml, then unblock and dispatch.
   - `Unknown skill(s): kanban-worker` → likely an old dispatcher. Modern dispatchers (v3.3+) auto-symlink on spawn. Fix: symlink manually: `ln -sf ~/.hermes/skills/devops/kanban-worker ~/.hermes/profiles/<profile>/skills/kanban-worker`, then unblock. Same for any other `Unknown skill(s): <name>` — `_ensure_profile_skill()` handles all skills generically on modern dispatchers.
   - `ModuleNotFoundError` → verify PYTHONPATH or import paths in the code.
4. **Never unblock a review-required task and reassign to the same profile without fixing the issues first.** The fresh run will find the same problems and block again, wasting time and tokens.
5. **For critical issues found by the reviewer:** the fastest path is to fix the code yourself (you have full context from the conversation), commit, then unblock + reassign. The reviewer re-validates that the fix resolved the specific issue. This is faster than creating a new coder task and waiting for another pipeline cycle.

**Не паникуй при 1-2 крашах с авто-retry (урок 20.08.2026, Этап 5 frontend).** Задача упала дважды подряд: `#443 crashed {pid not alive}` + `#444 protocol_violation {worker exited cleanly rc=0 without calling kanban_complete or kanban_block}`. Диспетчер сам перезапустил (run #445) — третья попытка успешна. Перед любым вмешательством (reclaim/пересоздание/delegate_task) проверь: `ps -o pid,etime,pcpu -p $(pgrep -f "kanban task <id>")` — процесс жив и %CPU > 0, в `~/.hermes/profiles/<profile>/logs/agent.log` растут «API call #N» → воркер работает, жди ещё цикл `kanban_wait.py`. Reclaim/reassign/delegate_task — только после 3+ крашей подряд или мёртвого процесса без перезапуска.

**⚠️ Воркер ЖИВ, но ЗАВИС (futex_wait_queue) — это НЕ «краш» и НЕ «работает» (урок 21.08.2026, Этап 8).** Сигнатура зависшего процесса (отличать от живого и от мёртвого): процесс существует (`ps` показывает `hermes -p <profile> ... kanban task <id>`), но `cat /proc/<pid>/wchan` → `futex_wait_queue`, `pcpu` ≈ 0 (реальный случай: 41 сек CPU за 3 часа), heartbeat в `hermes kanban show` устарел на часы (последний 15:21 при now 18:22), лог воркера оборвался на середине tool-вызова («preparing todo…»), дочерних процессов нет, в errors.log тишина (без исключений). Наиболее вероятная причина — зависший сетевой запрос к LLM API без таймаута. Лечение: `kill -9 <pid>` — диспетчер при смерти процесса сам снимает claim и запускает новый run (проверь `hermes kanban show <id>` → появился `[run N] spawned` с новым pid и свежим heartbeat). Незакоммиченные файлы в worktree остаются — новый воркер продолжит с них. НЕ создавай дубликат и НЕ reclaim, пока не убедился, что диспетчер не перезапустил сам (подожди тик ~60-90с).

**⚠️ «protocol violation (rc=0 без kanban_complete)» на coder = deepseek thinking-loop (21.08.2026, Этап 6 и 7A).** Сигнатура в логе: воркер генерирует объяснения/планы вместо tool calls (в логе: «the only winning move is to stop generating explanatory words entirely»), API-вызовы копятся с высокой латентностью (30-50с), файлов мало, потом CLI выходит rc=0 без вызова kanban_* → диспетчер пишет protocol violation. Диагностика: `tail -30 ~/.hermes/kanban/logs/<id>.log` (искать само-рефлексию «I'll do it now»), плюс `cd ~/.worktrees/<id> && git status --short` — если файлы есть, перезапуск добьёт; если файлов нет после 15-20 мин — резать задачу. Сам перезапуск: `hermes kanban unblock <id>` + dispatch (после failure_limit) — новый воркер часто продолжает с незакоммиченных файлов. Это НЕ баг окружения и не повод для delegate_task.

**⚠️ Crash loops cost real money.** Every crashed run consumes tokens on the dispatcher health-check cycle AND on the failed spawn. A task that crashes 16+ times (real case: `t_5bff682a`, self-improver + missing `web-search-scraper` skill, 28 May 2026) burns money silently. Block or reclaim the task after 3 consecutive crashes — do not let it loop. Check `--skills` flag: if the profile lacks the skill, the CLI crashes before the agent starts, with empty logs.

When a kanban task consistently crashes on dispatch ("pid not alive" or exit code 1 every 60-90s) despite the profile being registered, the kanban-worker skill being symlinked, and the profile config being complete, **use delegate_task as a bypass**. The spawn mechanism within delegate_task works differently from kanban's dispatch_in_gateway spawning and often succeeds where kanban dispatch fails.

Protocol:
1. Block the crashing kanban task with reason "crashed N times — retry via delegate_task"
2. Run the same task body via `delegate_task` with appropriate toolsets and the goal/context matching the original task body
3. After delegate_task completes successfully, either:
   - Archive the original kanban task (it's done via delegate_task)
   - Or if the kanban pipeline has downstream tasks with parent links, update those links to reference a kanban task that actually completed, or complete the original blocked task manually with the delegate_task's summary

This is a tactical workaround — the root cause (dispatch_in_gateway health checks, spawn timing, or session bootstrap) should be diagnosed separately. But for unblocking a user who needs results, delegate_task fallback is the fastest path.

⚠️ **CRITICAL — include `kanban` in toolsets.** When spawning via delegate_task, the subagent gets a restricted toolset. If `kanban` is NOT in the toolsets, the agent CANNOT call `kanban_complete` — it does the work, completes the analysis, but the original kanban task stays `running` forever. You'll have to manually `kanban complete <task_id>` after the delegate_task summary comes back.

Always include `kanban` in toolsets for bypass tasks:

```python
# Block the crashing task
# Run hermes kanban block <id> "crashed 11+ times — retry via delegate_task"

# Then spawn via delegate_task — kanban MUST be in toolsets
result = delegate_task(
    goal="[task body here]",
    toolsets=["terminal", "file", "web", "kanban"],  # ← kanban is required
)
```

After delegate_task completes, verify the kanban task was auto-completed. If it's still `running`, complete it manually with the delegate_task's summary as the reason.

### Handling a reviewer that blocks instead of completing

If a reviewer profile consistently calls `kanban_block` (because its SOUL.md says "block if issues found") but the task is part of a pipeline where it should complete, the root cause is the profile's SOUL.md. Fix it permanently:

Edit `~/.hermes/profiles/reviewer/SOUL.md` and replace the output section with:
```
## Output
- kanban_comment with detailed findings (issues by severity)
- kanban_complete with summary and verdict
- Do NOT kanban_block — the issue report is in the comment, and the orchestrator or user decides what to fix.
```

While a SOUL.md edit is permanent, you can also override per-task by adding to the task body: "Complete with findings in a comment — do NOT block. A new fix task will be created if needed."

### Handling iteration budget exhaustion (reviewer)

The reviewer profile runs out of turns (`Iteration budget exhausted (N/N)`) more often than coder profiles because reviewing involves reading code, cross-referencing specs, running tests, and writing structured output. Fix:

- Increase `agent.max_turns` in the reviewer's `~/.hermes/profiles/reviewer/config.yaml` from 40 to **100** (20.08.2026: 40 не хватило на полное ревью этапа с 12-пунктовым чек-листом).
- Verify `agent.reasoning_effort` is `high` — reviewer tasks benefit from deeper analysis.
- If the reviewer's task body asks them to review too many files in one shot, split into multiple reviewer tasks (e.g., reviewer #1: correctness/security, reviewer #2: style/test-coverage).

**Если воркер всё равно упёрся в лимит, но работа сделана (вердикт в логе):** перед повторным диспатчем прочитай `~/.hermes/kanban/logs/<task_id>.log` — последние строки перед «Reached maximum iterations» содержат финальный отчёт. Если вердикт APPROVED с findings — заверши задачу сам: `hermes kanban comment <id> "<текст ревью>" --author reviewer` + `hermes kanban complete <id> --summary "..."` (по вердикту из лога). Не диспатчь повторно — воркер сделает то же самое и снова упрётся. Дважды проверено (20.08.2026: t_8d210406, t_a2bd4c3d).

**⚠️ worker max_turns=20 мало для multi-file задач с коммитом — файлы написаны, но не закоммичены (урок 21.08.2026, Этап 8 доки).** Worker (max_turns=20) написал оба markdown-файла (112+118 строк), но упёрся в `Iteration budget exhausted (20/20)` ДО коммита и `kanban_complete` — задача авто-блокировалась (consecutive_failures=2). Диагностика: в worktree `git status --short` показывает файлы, лог заканчивается рекомендацией «сделать коммиты, затем kanban_complete». По вердикту из лога: файлы корректны и соответствуют ТЗ → закоммить сам (`git add <файлы> && git commit -m "docs(...): ..."`), затем `hermes kanban complete <id> --summary "..."` — НЕ перезапускай воркера (сделает то же и снова упрётся). Для задач «2+ файла + коммит + complete» не назначай worker'у (20 итераций не хватает) — coder или `--max-runtime` побольше.

### Handling iteration budget exhaustion (coder)

Coder profiles also hit the iteration limit — especially on large files (>2000 LOC) or when the task requires reading a lot of context before patching. The default max_turns of 50 (from `agent.max_iterations: 90` minus tool call overhead) can be tight.

**Fix:** Use `--max-runtime` when creating the task. Set it generously:

```python
kanban_create(
    title="MCP: cleanup orphans at startup",
    assignee="coder",
    body="...",
    max_runtime_seconds=1800,  # 30m — big file, needs room
)
```

Or via CLI: `hermes kanban create --max-runtime 30m --assignee coder "..." --body "..."`

**When the task blocks with `Iteration budget exhausted (N/N)` — do NOT ask the user to split into subtasks for a simple change.** This frustrates the user. Instead:

1. Check the task log to understand if the work was partially done (files may already be patched)
2. Archive the old blocked task
3. Create a new task with `--max-runtime 30m` (or higher) — same body, same assignee
4. Dispatch immediately with a brief status update: "iterations не хватило, перезапустил с 30m"

Only split into subtasks when the work genuinely requires multiple independent files/systems — never for a single-file patch.

**Known reference:** mcp_tool.py (3593 строки) exhausted 50 iterations in 7 min on a simple 2-point patch (28 May 2026). Reset with `--max-runtime 30m` completed fine.

**⚠️ Большая реализация (5-8 модулей) → Iteration budget exhausted (100/100) дважды (21.08.2026, Этап 7A: 8 модулей 7.1-7.8).** Воркер тратит десятки итераций на исследование контекста (чтение существующих сервисов, тестов, фикстур) и пишет файлы в САМОМ конце — не успевает прогнать тесты до зелёного. Два run подряд упали на 100/100. Правила:
1. **Режь реализации на куски по 2-3 подзадачи плана**, не 5-8. Одна Kanban-задача = модели+миграция, другая = сервисы, третья = интеграция/клиенты.
2. **Файлы сохраняются в worktree между run'ами.** После `Iteration budget exhausted`: `hermes kanban unblock <id>` + dispatch — новый воркер продолжает с незакоммиченных файлов и часто доводит до зелёного (этап 7A: run #3 done). НЕ создавай новую задачу и не архивируй.
3. **Оцени остаток сам перед перезапуском** — прогнать pytest прямо в worktree (быстро, без LLM):
```bash
cd ~/projects/<repo>/.worktrees/<task_id> && ~/projects/<repo>/.venv/bin/python -m pytest <files> -q
```
⚠️ У worktree НЕТ своего `.venv` — используй `.venv` главного чекаута `~/projects/<repo>/.venv/bin/python`.
4. 10 passed / 9 failed после 2 таймаутов = воркер успел написать всё, осталась доводка — перезапуск почти гарантированно добьёт.

Hallucination warnings appear on tasks where a worker's `kanban_complete(created_cards=[...])` claim included card ids that don't exist or weren't created by the worker's profile (the gate blocks the completion), or where the free-form summary references `t_<hex>` ids that don't resolve (advisory prose scan, non-blocking). Both produce audit events that persist even after recovery actions — the trail stays for debugging.

## Cost & Usage Monitoring

Hermes tracks per-session token usage and estimated cost in `state.db`. See `references/token-cost-tracking.md` for queries by model/day, pricing data sources, and common reasons for discrepancies between estimated and actual billing.

## Researcher speed

See `references/researcher-speed-tuning.md` — `reasoning_effort: high` + `max_turns: 30` + `web_extract` abuse cause 3+ min search times. Recommended: `reasoning_effort: medium`, `max_turns: 15`, ban `web_extract` in task body.

## Researcher max_turns escalation

When a researcher task involves multiple dates/sources (flight search on 7 dates, comparison shopping), the default 15-20 turns are NOT enough. Each web_search = 1 turn, each crawl4ai = 2-3 turns. For 7 dates × 3 sources × crawls = 30+ turns minimum.

**Increase researcher max_turns before dispatching:**
```bash
hermes --profile researcher config set agent.max_turns 45
grep max_turns ~/.hermes/profiles/researcher/config.yaml  # verify
```

Use 40-45 for multi-date/multi-source research. Reset back to 20 after the task if you want to save tokens on single-query tasks (optional — the extra buffer doesn't cost tokens unless used).
