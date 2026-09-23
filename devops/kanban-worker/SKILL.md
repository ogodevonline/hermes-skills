---
name: kanban-worker
description: Pitfalls, examples, and edge cases for Hermes Kanban workers. The lifecycle itself is auto-injected into every worker's system prompt as KANBAN_GUIDANCE (from agent/prompt_builder.py); this skill is what you load when you want deeper detail on specific scenarios.
version: 2.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, multi-agent, collaboration, workflow, pitfalls]
    related_skills: [kanban-orchestrator]
---

# Kanban Worker — Pitfalls and Examples

> You're seeing this skill because the Hermes Kanban dispatcher spawned you as a worker with `--skills kanban-worker` — it's loaded automatically for every dispatched worker. The **lifecycle** (6 steps: orient → work → heartbeat → block/complete) also lives in the `KANBAN_GUIDANCE` block that's auto-injected into your system prompt. This skill is the deeper detail: good handoff shapes, retry diagnostics, edge cases.

## Step 0 — Load your profile's skills

**Critical first action:** Your profile's `skills/` directory may contain domain-specific skills (crawl4ai, web-search-scraper, database-tools, etc.) that hold executable scripts, exact CLI invocations, and parameter docs. **You must load them before you start working.**

Your SOUL.md may mention these skills by name, but that's not the same as having them loaded — SOUL.md text is just documentation. Without calling `skill_view('skill-name')`, you won't see the actual commands, paths, or flags you need to run.

**Checklist at startup:**
1. List your profile skills: `ls ~/.hermes/profiles/<PROFILE_NAME>/skills/` (or use your profile name from `$HERMES_KANBAN_PROFILE` if available, otherwise `os.environ.get('HERMES_KANBAN_PROFILE', 'researcher')` — fall back to listing `~/.hermes/skills/` subdirectories if the profile env isn't set)
2. For each skill relevant to your task, call `skill_view(name)` to get its SKILL.md — this reveals the exact script paths, parameters, and invocation patterns.
3. Only then proceed to work. A researcher who loads `web-search-scraper` finds the exact `uv run search.py --query "..." --preview` command. A coder who loads `test-driven-development` finds the RED-GREEN-REFACTOR cycle. A reviewer who loads `requesting-code-review` finds the security gates.

**Vault writers — load `vault-frontmatter`:** If your task writes to `/home/hermes/hermes-vault/`, load the `vault-frontmatter` skill **before** creating or editing any .md file. It contains:
- Полный словарь node_type (19 типов) и статусов
- Таблицу угадывания типа по папке
- YAML-шаблоны для каждого типа
- Команду валидации после write_file (`gotham-ensure-frontmatter.py`)
- Fallback при ошибках

```
skill_view('vault-frontmatter')
```

Без этого навыка файлы не пройдут pre-commit hook (G01–G06 проверки).

Without this step, you risk using generic built-in tools (`web_search`, `web_extract`) when your profile has specialized scripts that are faster, more precise, and better suited (e.g. Yandex XML via web-search-scraper instead of generic web_search for Russian-language queries).

## Workspace handling

Your workspace kind determines how you should behave inside `$HERMES_KANBAN_WORKSPACE`:

| Kind | What it is | How to work |
|---|---|---|
| `scratch` | Fresh tmp dir, yours alone | Read/write freely; it gets GC'd when the task is archived. |
| `dir:<path>` | Shared persistent directory | Other runs will read what you write. Treat it like long-lived state. Path is guaranteed absolute (the kernel rejects relative paths). |
| `worktree` | Git worktree at the resolved path | If `.git` doesn't exist, run `git worktree add <path> ${HERMES_KANBAN_BRANCH:-wt/$HERMES_KANBAN_TASK}` from the main repo first, then cd and work normally. Commit work here. |

## Tenant isolation

If `$HERMES_TENANT` is set, the task belongs to a tenant namespace. When reading or writing persistent memory, prefix memory entries with the tenant so context doesn't leak across tenants:

- Good: `business-a: Acme is our biggest customer`
- Bad (leaks): `Acme is our biggest customer`

## Good summary + metadata + artifacts shapes

The `kanban_complete(summary=..., metadata=..., artifacts=[...])` handoff is how downstream workers read what you did. Patterns that work:

**📄 Artifacts (built-in file delivery):** Pass file paths in `artifacts=[]` to auto-send the file as a native attachment in Telegram. The gateway's `_deliver_kanban_artifacts()` reads this list and uploads each file (images as inline photos, videos inline, other formats as downloadable documents). Always pair with a short `summary=` — the first line becomes the notification text.

**Coding task:**
```python
kanban_complete(
    summary="shipped rate limiter — token bucket, keys on user_id with IP fallback, 14 tests pass",
    metadata={
        "changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
        "tests_run": 14,
        "tests_passed": 14,
        "decisions": ["user_id primary, IP fallback for unauthenticated requests"],
    },
)
```

**Coding task that needs human review:**

For code changes, drop structured metadata (changed_files / tests_run / diff_path) into a `kanban_comment` first, then `kanban_complete` with a summary. The review pipeline is managed via **parent links** — the downstream reviewer task is gated on your completion, not on unblocking. Do NOT block — the dependency engine promotes children only when parents reach done.

```python
import json

kanban_comment(
    body="code handoff:\n" + json.dumps({
        "changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
        "tests_run": 14,
        "tests_passed": 14,
        "diff_path": "/path/to/worktree",
        "decisions": ["user_id primary, IP fallback for unauthenticated requests"],
    }, indent=2),
)
kanban_complete(
    summary="shipped rate limiter — token bucket, keys on user_id with IP fallback, 14 tests pass",
    metadata={
        "changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
        "tests_run": 14,
        "tests_passed": 14,
    },
)
```

Use `kanban_block` only for genuine human-decidable ambiguity (missing credentials, UX choice, paywalled source). Technical errors (API failures, parse errors, timeouts) are NOT ambiguity — complete with error summary in metadata.

**Research task (with artifact delivery):**
```python
import os

task_id = os.environ["HERMES_KANBAN_TASK"]
result_path = f"/home/hermes/.hermes/kanban/results/{task_id}.md"

# Save full report to file
with open(result_path, "w") as f:
    f.write(full_report_text)

# Complete — file auto-delivers to subscribed chat as attachment
kanban_complete(
    summary="reviewed 3 libraries: vLLM wins on throughput, SGLang on latency, TRT-LLM on memory",
    metadata={
        "sources_read": 12,
        "recommendation": "vLLM",
        "benchmarks": {"vllm": 1.0, "sglang": 0.87, "trtllm": 0.72},
    },
    artifacts=[result_path],
)
```

**Review task:**
```python
kanban_complete(
    summary="reviewed PR #123; 2 blocking issues found (SQL injection in /search, missing CSRF on /settings)",
    metadata={
        "pr_number": 123,
        "findings": [
            {"severity": "critical", "file": "api/search.py", "line": 42, "issue": "raw SQL concat"},
            {"severity": "high", "file": "api/settings.py", "issue": "missing CSRF middleware"},
        ],
        "approved": False,
    },
)
```

Shape `metadata` so downstream parsers (reviewers, aggregators, schedulers) can use it without re-reading your prose.

## Code quality: typing HARDLINE (coder/reviewer workers)

Стандарт пользователя (закреплён 20.08.2026 в SOUL.md coder §6 и reviewer rules 6-7): **сырые типы-структуры запрещены — только датаклассы.**

- ❌ `Any`, голые `dict`/`list`/`tuple`/`set`, анонимные кортежи как структуры (`tuple[str, int, float]`), словари-структуры (`{"id": ..., "name": ...}`), `**kwargs` для передачи данных
- ✅ `@dataclass` (frozen где можно): `PriceQuote(currency: str, amount: int, rate: float)`, `ClientDTO(id: int, name: str)`
- `dict` — только отображение однородных значений (`dict[str, int]`) или JSON на границе API/БД (сразу маппить в датакласс внутри)
- Магические строки/числа → `Enum`; `Literal` — для ограниченных значений в сигнатурах
- ID-типы → `NewType` (`UserId`, `TenantId`, `SpecialistId`) — не перепутать id разных сущностей
- `TypedDict` — только на границе JSON; `**kwargs` в публичных сигнатурах — запрещено; `Protocol` — для интерфейсов вместо `Any`

Применение:
- **coder**: писать код по этому стандарту; файлы ≤150 строк.
- **reviewer**: нарушение = замечание MEDIUM+ (датакласс обязателен).
- **оркестратор**: в body кодинг-задач давать отсылку к этому правилу.

## Claiming cards you actually created

If your run produced new kanban tasks (via `kanban_create`), pass the ids in `created_cards` on `kanban_complete`. The kernel verifies each id exists and was created by your profile; any phantom id blocks the completion with an error listing what went wrong, and the rejected attempt is permanently recorded on the task's event log. **Only list ids you captured from a successful `kanban_create` return value — never invent ids from prose, never paste ids from earlier runs, never claim cards another worker created.**

```python
# GOOD — capture return values, then claim them.
c1 = kanban_create(title="remediate SQL injection", assignee="security-worker")
c2 = kanban_create(title="fix CSRF middleware", assignee="web-worker")

kanban_complete(
    summary="Review done; spawned remediations for both findings.",
    metadata={"pr_number": 123, "approved": False},
    created_cards=[c1["task_id"], c2["task_id"]],
)
```

```python
# BAD — claiming ids you don't have captured return values for.
kanban_complete(
    summary="Created remediation cards t_a1b2c3d4, t_deadbeef",  # hallucinated
    created_cards=["t_a1b2c3d4", "t_deadbeef"],                   # → gate rejects
)
```

If a `kanban_create` call fails (exception, tool_error), the card was NOT created — do not include a phantom id for it. Retry the create, or omit the id and mention the failure in your summary. The prose-scan pass also catches `t_<hex>` references in your free-form summary that don't resolve; these don't block the completion but show up as advisory warnings on the task in the dashboard.

## Block reasons that get answered fast

Bad: `"stuck"` — the human has no context.

Good: one sentence naming the specific decision you need. Leave longer context as a comment instead.

```python
kanban_comment(
    task_id=os.environ["HERMES_KANBAN_TASK"],
    body="Full context: I have user IPs from Cloudflare headers but some users are behind NATs with thousands of peers. Keying on IP alone causes false positives.",
)
kanban_block(reason="Rate limit key choice: IP (simple, NAT-unsafe) or user_id (requires auth, skips anonymous endpoints)?")
```

The block message is what appears in the dashboard / gateway notifier. The comment is the deeper context a human reads when they open the task.

## Heartbeats worth sending

Good heartbeats name progress: `"epoch 12/50, loss 0.31"`, `"scanned 1.2M/2.4M rows"`, `"uploaded 47/120 videos"`.

Bad heartbeats: `"still working"`, empty notes, sub-second intervals. Every few minutes max; skip entirely for tasks under ~2 minutes.

## Retry scenarios

If you open the task and `kanban_show` returns `runs: [...]` with one or more closed runs, you're a retry. The prior runs' `outcome` / `summary` / `error` tell you what didn't work. Don't repeat that path. Typical retry diagnostics:

- `outcome: "timed_out"` — the previous attempt hit `max_runtime_seconds`. You may need to chunk the work or shorten it.
- `outcome: "crashed"` — OOM or segfault. Reduce memory footprint.
- `outcome: "spawn_failed"` + `error: "..."` — usually a profile config issue (missing credential, bad PATH). Ask the human via `kanban_block` instead of retrying blindly.
- `outcome: "reclaimed"` + `summary: "task archived..."` — operator archived the task out from under the previous run; you probably shouldn't be running at all, check status carefully.
- `outcome: "blocked"` — a previous attempt blocked; the unblock comment should be in the thread by now.
- **terminal() failed (cwd broken, "Cannot execute shell commands")** — the previous run may have been spawned with a broken working directory. This is a transient environment issue, not a logic problem. Retry (unblock + dispatch) often resolves it because the workspace is reset with a fresh cwd. On retry, verify `os.getcwd()` or `pwd` before heavy work. If terminal fails again, fall back to `read_file` + `search_files` for static verification — confirm file content, search patterns, report findings without a shell. Complete with a note about the limitation.

## Notification routing

You can configure the gateway to receive cross-profile Kanban task notifications by adding `notification_sources` to `~/.hermes/config.yaml`.
- `notification_sources: ['*']` accepts subscriptions from all profiles.
- `notification_sources: ['default', 'zilor-ppt']` or `"default,zilor-ppt"` restricts subscriptions to specified profiles.
- Omitting the key keeps the default behavior (profile isolation).

## Do NOT

- Call `delegate_task` as a substitute for `kanban_create`. `delegate_task` is for short reasoning subtasks inside YOUR run; `kanban_create` is for cross-agent handoffs that outlive one API loop.
- Modify files outside `$HERMES_KANBAN_WORKSPACE` unless the task body says to.
- Create follow-up tasks assigned to yourself — assign to the right specialist.
- Complete a task you didn't actually finish with error summary + metadata in `kanban_complete`. Only block for human-decidable choices (missing credentials, UX decisions), never for technical errors.
- **Ignore body instructions in favour of your own tool preference.** If the task body says "use tool X" (e.g. `search.py` from web-search-scraper), use X. Do not silently substitute generic tools (`web_search`, `web_extract`) — you were told which tool to use for a reason.
- **Go to blocked without attempting the specified approach.** Try the approach from the body first. If it fails, try an alternative. Only block after you've tried and can articulate what went wrong. Attach partial results as a comment before blocking — something is better than nothing.

## Save results before kanban_complete — MANDATORY artifacts

Every Kanban worker MUST save its result before completing. **`kanban_complete` without `artifacts=[...]` causes Telegram delivery truncation: the summary text gets cut off (Telegram's ~200-char notification limit), and the full result never reaches the user.**

### Rule: ALWAYS pair `kanban_complete` with `artifacts`

Save result to a known path and pass `artifacts=[...]` to `kanban_complete`. The gateway auto-sends the file as a native attachment to the subscribed chat. This is not optional — without it, the user sees a truncated notification and has no way to view the full result.

**Path A — artifact delivery (MANDATORY, automatic):** Save result to a known path and pass `artifacts=[...]` to `kanban_complete`. The gateway auto-sends the file as a native attachment to the subscribed chat.

```python
import os

task_id = os.environ["HERMES_KANBAN_TASK"]
result_path = f"/home/hermes/.hermes/kanban/results/{task_id}.md"

# Save full result
with open(result_path, "w") as f:
    f.write(report_text)

# Complete with artifact — file arrives in chat automatically
kanban_complete(
    summary="Кратко: готов отчёт по теме X",
    artifacts=[result_path],
)
```

This is the **preferred** method — the file arrives in Telegram alongside the done notification. No extra steps.

**⚠️ CRITICAL: `notify-subscribe` is REQUIRED for artifact delivery.** The gateway notifier (`_deliver_kanban_artifacts` including the fallback patch) only fires for tasks that have a `notify-subscribe` subscription. A task created without subscription will complete silently — no file, no notification. The subscription is automatically created when you create a task from the gateway (`/kanban create`), but NOT when you create via CLI `hermes kanban create`. Always add subscription explicitly.

**Path B — Obsidian vault (legacy):** Each profile has a dedicated directory under `agents-data/<AgentName>/`.

⚠️ Pass content via **stdin**, not argv — long/multi-line content breaks as a shell argument. The script supports `-` for stdin.

```python
import subprocess
import os

result_summary = "..."  # your report/summary
profile = os.environ.get("HERMES_KANBAN_PROFILE", "worker")
subprocess.run(
    ["python3", os.path.expanduser("~/.hermes/scripts/obsidian_save.py"),
     profile.capitalize(), "-"],
    input=result_summary,
    capture_output=True,
    timeout=15,
)
```

This writes `~/hermes-vault/agents-data/<AgentName>/YYYY-MM-DD-topic.md`, commits, and pushes.

**See `references/obsidian-save.md`** for the full agent-directory mapping and exact command syntax.

Pitfall: if you skip BOTH save steps, the result is gone after the workspace is GC'd. Only the kanban_complete summary survives (which may be truncated to 200 chars in notifications). Save FIRST, complete SECOND.

## Fix bugs discovered during routine work — don't escalate

When your task encounters a **foundational bug** in the tool/infra it depends on, fix it yourself rather than creating a separate bug-fix task. Examples:

- `gitmark.py lint --strict` returned exit 0 despite ERR violations (pre-commit hook depends on non-zero exit) → fix gitmark.py's exit handling, verify with a test run, then complete the hook installation
- A script you were told to call is missing from disk → check if it's in a different path, symlink it, then continue
- A config file has wrong default values → patch it, document the fix in summary, then complete your main task

**How to decide if a discovery is a "fix in-situ" vs. "escalate":**

| Fix in-situ | Escalate (new task or block) |
|---|---|
| Bug in a tool YOUR task depends on | Bug in an unrelated system |
| Missing symlink/credential you can create | Missing credentials you don't have access to |
| Wrong default value in config | Architectural design decision |
| CLI bug that breaks your exact workflow | Security-sensitive change |
| Verifiable fix (< 3 file changes) | Multi-module refactor |

**Protocol:**
1. Fix the bug
2. Test that your fix works
3. Test that your original task still works
4. Document the fix in `kanban_complete(summary="... fixed bug X in tool Y while doing main task Z ...")`
5. Do NOT `kanban_block` — the fix is already done, `kanban_complete` with the summary

This pattern is faster and more reliable than creating a separate bug-fix task that must go through the full lifecycle (create → subscribe → approve → dispatch → wait → review). One task does both: fixes the dependency and delivers the original deliverable.

## Pitfalls

**Scratch workspace + filesystem side-effects = files don't persist.** The scratch workspace is ephemeral — it gets GC'd when the task is archived. Any files written via `terminal()` or `write_file()` to paths outside `$HERMES_KANBAN_WORKSPACE` (e.g. `~/.hermes/scripts/`, `~/.hermes/skills/`, `/tmp/...`) **will NOT survive the workspace cleanup**, even if `ls -la` shows them during the run.

**Common patterns that fail:**
- `cp /tmp/gitmark-memory-bank/skills/kb-search/gitmark.py ~/.hermes/scripts/gitmark.py` — files appear during run, vanish on GC
- `patch` on `~/.hermes/skills/gitmark/SKILL.md` — modification is inside the sandbox, not the real tree
- `write_file('~/.hermes/scripts/gitmark.py', ...)` — same sandbox illusion

**Correct approaches:**

| Goal | Do this instead |
|---|---|
| Create/update skill | `skill_manage(action='create')` or `skill_manage(action='patch')` — targets the real `~/.hermes/skills/` tree |
| Write a script | Call `skill_manage(action='write_file', file_path='scripts/gitmark.sh', file_content=...)` which writes to the skill's scripts/ dir — or use `write_file` and verify with `read_file` immediately (the file is in the sandbox, but `skill_manage` writes to real FS) |
| Copy a CLI tool from outside | Use `skill_manage(action='write_file', file_path='scripts/gitmark.sh', file_content=...)` with the tool's source read via `read_file` — inject the content through the tool, not through `terminal('cp ...')` |
| Index a vault/data dir | The index is a derived artifact inside the workspace — write the result (e.g. stat output, search results) to a file in the workspace, pass as `artifacts=[...]` to `kanban_complete`. The real indexing must be re-done outside the workspace. |

**Verification rule:** After ANY write to a path outside `$HERMES_KANBAN_WORKSPACE`, immediately verify with `read_file()` or `ls -la` on the **real** path (not the sandbox-relative one). If the file isn't found, you're in a sandbox — switch to `skill_manage` or `kanban_block` explaining the workspace limitation.

**For task creators (orchestrators):** When creating a Kanban task whose body says "install script X to ~/.hermes/scripts/", or "create a skill", the default `scratch` workspace will frustrate the worker. Consider:
- `--workspace dir:<persistent-path>` to give the worker real filesystem access
- Or structure the body to use `skill_manage()` explicitly (which works across all workspace types)
- Or handle the side-effect yourself after the worker completes (rely on `artifacts` handoff only)

**Task state can change between dispatch and your startup.** Between when the dispatcher claimed and when your process actually booted, the task may have been blocked, reassigned, or archived. Always `kanban_show` first. If it reports `blocked` or `archived`, stop — you shouldn't be running.

**Workspace may have stale artifacts.** Especially `dir:` and `worktree` workspaces can have files from previous runs. Read the comment thread — it usually explains why you're running again and what state the workspace is in.

**Don't rely on the CLI when the guidance is available.** The `kanban_*` tools work across all terminal backends (Docker, Modal, SSH). `hermes kanban <verb>` from your terminal tool will fail in containerized backends because the CLI isn't installed there. When in doubt, use the tool.

**Crash loop: "Error: Unknown skill(s): <name>" from spawn — TWO variants.**  \n\n**Variant A — profile name passed as `--skill`.** If the task was created with `--skill self-improver` (or `coder`, `researcher`, `skill-improver`, etc.), the dispatcher passes a **profile name** as a skill to the worker. The CLI crashes immediately with `Error: Unknown skill(s): self-improver` because profiles are NOT skills. Symptom: `hermes kanban log <task>` shows the error, `hermes kanban show <task>` shows 3-4x `crashed` in runs with "pid not alive". **Fix:** Archive the broken task and create a new one WITHOUT `--skill` (or with a real skill name from `skills_list`). Profile assignment goes in `--assignee`, not `--skill`.\n\n**Variant B — missing kanban-worker symlink (older dispatchers).**  \nIf you're a retry (you see prior crashed runs) and the worker log at `<kanban_root>/logs/<task_id>.log` shows `Error: Unknown skill(s): kanban-worker`, the profile you're running under is missing the kanban-worker skill.\n\n---\n\n**Received a task that's just "run script X on N files"? You're probably overkill.**\n\nIf the task body tells you to run an existing script (e.g. `gotham-ensure-frontmatter.py --all --mode=add-missing`) that processes many files with simple transformations, you are an LLM agent being paid to do what a local script does for free. **Do not iterate file-by-file through LLM.** Instead:\n\n1. Read the script and understand what it does (one `read_file`)\n2. Run it once via `terminal()` on the whole dataset\n3. Verify the result with a follow-up command\n4. Complete with summary\n\n**Bad pattern (expensive, slow):**\n```\nread file 1 → check → patch → read file 2 → check → patch → ... (385 tool calls)\n```\n\n**Good pattern (efficient):**\n```\nread script → run once → verify → complete (3 calls total)\n```\n\nIf the task body describes a bulk operation that should be done by script but the script doesn't exist yet, write the script first (it's cheaper to write a script and run it once than to process each file through LLM), then run it. The user's cost signal is: *"нет я хочу по умному, щас все деньги мне сожрешь"* — they know Kanban LLM agents are expensive for bulk ops.  

**Why this happens:** The dispatcher checks for the skill in the default root (`~/.hermes/skills/`), finds it there, and adds `--skills kanban-worker`. But when `hermes -p <profile>` starts, the CLI resolves skills from the **profile-scoped** skills directory (`<profile_home>/skills/`). If the skill isn't symlinked there, the CLI crashes immediately with exit code 1 before the agent loop even starts. The dispatcher then detects "pid not alive" and retries, creating a crash loop.

**From your perspective as the worker:** you never actually run — the CLI dies before calling `kanban_show`. This looks like "pid not alive" or "crashed" with no meaningful output.

**Two variants of this failure:**

1. **Missing symlink** — the profile's skills/ dir has no kanban-worker symlink at all. Auto-repair should create it, but can fail on older dispatchers.

2. **Broken symlink** — the symlink EXISTS but points to a stale path (hermes update moved the bundled skill). The dispatcher sees the file and doesn't repair. The CLI resolves the symlink, finds nothing, crashes.

**Diagnostic:**
```bash
ls -la ~/.hermes/profiles/<profile>/skills/kanban-worker
readlink -f ~/.hermes/profiles/<profile>/skills/kanban-worker  # empty if broken
```

**Fix:**
```bash
# Quick — regenerate ALL profile symlinks:
python3 ~/.hermes/scripts/sync_profile_skills.py

# Or one-off:
ln -sf ~/.hermes/skills/devops/kanban-worker ~/.hermes/profiles/<profile>/skills/kanban-worker
```

**Do NOT** retry the same profile without fixing the symlink — it will loop.

---

**web_search/Firecrawl credits exhausted: do NOT block — fall back, complete partial.**

If `web_search` returns `Payment Required: Insufficient credits` (Firecrawl budget exhausted), this is a **technical error, not ambiguity**. Do NOT call `kanban_block` — no human can add credits for you mid-run, and the task just sits blocked.

Instead:
1. **Try alternatives** — `terminal("web-tools search ...")` (Rust CLI, Yandex XML/DDG) for search, `terminal("web-tools extract <url> ...")` for extraction, `terminal()` with `curl` for direct page fetches
2. **Use model knowledge** — compile what you know from training data, explicitly marking unverified claims as `[unverified: needs live check]`
3. **Complete with partial results** — save what you have, note the limitation in summary/metadata, and let the parent session finish the rest (it may have working web_search in its own environment).

```python
kanban_complete(
    summary="Research partial: 3/5 sections done. web_search down (credits exhausted on Firecrawl). Remaining from model knowledge only — marked unverified.",
    metadata={
        "completed_sections": ["A", "B", "C"],
        "unverified_sections": ["D", "E"],
        "blocker": "Firecrawl credits exhausted — no live search available",
    },
    artifacts=[result_path],
)
```

---

**Kanban results without artifacts get truncated in Telegram.** `kanban_complete(summary="длинный текст...")` without `artifacts=[path]` sends only the summary as a text notification — Telegram cuts it off at ~200 chars. The user never sees the full result. **Always** save the result to a file and pass it via `artifacts=[result_path]`. Even a short summary needs a file attachment for the full content. Lesson: self-improver returned complete analysis but user received only the first line.

**`~` (tilde) doesn't expand in `terminal()` paths.** Worker subagent processes may not resolve `~` to the home directory — `cd ~/.hermes/skills/...` fails with exit 1 in <1s. Always use absolute paths starting with `/home/hermes/` in `terminal()` calls:
- ❌ `cd ~/.hermes/skills/search/web-search-scraper/scripts && uv run ...`
- ✅ `cd /home/hermes/.hermes/skills/search/web-search-scraper/scripts && uv run ...`

This applies to ALL path arguments in `terminal()` — script directories, file paths, config locations. The `file` tools (`read_file`, `write_file`, `patch`, `search_files`) do resolve `~` correctly, so this pitfall is `terminal()`-only.

**SOUL.md mentions skills you haven't loaded.** Your profile's SOUL.md (injected into every run) lists tools and skills like `crawl4ai skill`, `web-search-scraper skill`, `sub-agents-orchestrator skill`. But SOUL.md is just plain text — seeing the name in your prompt does NOT mean the skill is loaded or that you know its commands. You must explicitly call `skill_view('crawl4ai')` to get the SKILL.md content (script paths, parameters, invocation examples). Without this, you only know the skill exists — not how to use it. Common symptom: a researcher who should use Yandex XML search (fast, Russian-optimized) instead falls back to generic `web_search` (slow, English-biased) because they never loaded `web-search-scraper` to see the `search.py` command.

## CLI fallback (for scripting)

Every tool has a CLI equivalent for human operators and scripts:
- `kanban_show` ↔ `hermes kanban show <id> --json`
- `kanban_complete` ↔ `hermes kanban complete <id> --summary "..." --metadata '{...}'`
- `kanban_block` ↔ `hermes kanban block <id> "reason"`
- `kanban_create` ↔ `hermes kanban create "title" --assignee <profile> [--parent <id>]`
- etc.

Use the tools from inside an agent; the CLI exists for the human at the terminal.
