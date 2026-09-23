# Profile Setup Checklist for Kanban Workers

When creating a new Hermes profile that will receive Kanban tasks, four things must be configured. Missing any of them causes silent failures (dispatcher spawns the worker but it crashes immediately).

## 1. Create the profile

```bash
hermes profile create <name>
```

This creates `~/.hermes/profiles/<name>/` with default config, .env, SOUL.md, and bundled skills.

## 2. Skills — auto-repair covers it, but manual is safer

The dispatcher (v3.3+) auto-creates symlinks for any skill referenced via `--skills` that exists in the default root `~/.hermes/skills/`. This happens on the very first spawn — so **manual symlinking is not strictly required**.

However, for reliability and to avoid the first-spawn crash-repair cycle, symlink upfront:

```bash
ln -sf ~/.hermes/skills/devops/kanban-worker ~/.hermes/profiles/<name>/skills/kanban-worker
```

The auto-repair fallback (`_ensure_profile_skill()`) handles any skill generically — not just `kanban-worker`. But pre-symlinking means zero delay on first use.

**⚠️ Broken symlinks after updates.** Auto-repair does NOT detect or fix broken symlinks created by `hermes update` (which may move or rename bundled skills). If a kanban worker crashes repeatedly with `Error: Unknown skill(s): kanban-worker`, run the fix script:

```bash
python3 ~/.hermes/scripts/sync_profile_skills.py
```

## 3. Symlink other needed skills (auto-repair covers it)

Each profile may need domain-specific skills. Modern dispatchers (v3.3+) auto-create symlinks on first spawn via `_ensure_profile_skill()`, so manual symlinking is optional. This table documents the canonical mapping used on the user's system — the dispatcher searches the default root across all category subdirectories, so it finds these automatically:

| Profile | Needed skills | Toolset hints |
|---------|--------------|--------------|
| **orchestrator** | `kanban-orchestrator`, `writing-plans`, `subagent-driven-development` | kanban, delegation — no terminal/file/web |
| **architect** | `writing-plans`, `architecture-diagram` | file, terminal — write specs and SVG diagrams |
| **coder** | `test-driven-development`, `subagent-driven-development`, `writing-plans`, `requesting-code-review`, `git-init-before-edits` | terminal, file — TDD in git worktree, max_turns=50. Debugging is handled by a separate `debugger` profile. |
| **reviewer** | `requesting-code-review`, `github-code-review` | file, terminal (read-only) — must `kanban_complete`, not `kanban_block`; max_turns=40 |
| **debugger** | `systematic-debugging`, `test-driven-development` | file, terminal — find root causes, write regression tests. Does NOT write new features. max_turns=40 |
| **researcher** | `web-search-scraper`, `crawl4ai`, `sub-agents-orchestrator` | web, search, terminal (for crawl scripts) |
| **ask** | `web-search-scraper` | web, search — quick answers, no terminal/file |
| **skill-writer** | `hermes-agent-skill-authoring`, `writing-plans`, `kanban-worker` | file, terminal — create/update SKILL.md files. Created manually, not via `hermes profile create`. max_turns=25 |

```bash
find ~/.hermes/skills -name "SKILL.md" -path "*/<skill-name>/SKILL.md" | head -1 | xargs dirname
ln -sf <source_dir> ~/.hermes/profiles/<name>/skills/<skill-name>
```

## 4. Configure config.yaml

Minimal config for a worker profile:

```yaml
model:
  default: deepseek/deepseek-v4-flash
  provider: kilocode
  base_url: https://api.kilo.ai/api/gateway

agent:
  max_turns: 30  # lower for short tasks, higher for coding
  api_max_retries: 3
  reasoning_effort: high
  verbose: false
  image_input_mode: disabled

toolsets:
  - terminal
  - file
  - skills
  - memory
  - session_search
  - kanban
  - todo
  - delegation

terminal:
  backend: local
  cwd: .
  timeout: 300

memory:
  memory_enabled: true
  user_profile_enabled: true

stt:
  enabled: false
tts:
  enabled: false
```

Key differences by profile:
- **orchestrator**: needs `kanban` + `delegation` + `todo` + `skills`, does NOT need `terminal`/`file`/`web`/`search`. Has `writing-plans` + `subagent-driven-development` loaded.
- **coder**: needs `terminal` + `file`, does NOT need `web`/`search`. max_turns=50. Debugging is out of scope — use `debugger` for that.
- **reviewer**: needs `file` + `terminal` (read-only), does NOT need `web`/`search`. max_turns=40. Must complete (not block) in pipeline mode.
- **debugger**: needs `file` + `terminal`. max_turns=40. Systematic debugging: understand → root cause → fix → regression test. Never writes new features.
- **researcher**: needs `web` + `search`, may also need `terminal` (for crawl scripts).
- **ask**: needs `web` + `search`, does NOT need `terminal`/`file`.
- **architect**: needs `file` + `terminal` (write specs), does NOT need `web`.
- **skill-writer**: needs `file` + `terminal` + `skills`, does NOT need `web`/`search`. max_turns=25.

## 5. Copy .env if missing

```bash
cp ~/.hermes/.env ~/.hermes/profiles/<name>/.env
```

Profiles inherit env from shell if missing, but explicit copy is safer.

## 6. Write SOUL.md

Each profile needs a SOUL.md describing its purpose and rules. See `/home/hermes/.hermes/profiles/coder/SOUL.md` etc. for examples.

## Verification

```bash
# Check profile exists and can be seen
hermes profile list
hermes profile show <name>

# Check skills are available (manual symlinks optional — auto-repair handles this)
ls ~/.hermes/profiles/<name>/skills/ 2>/dev/null || echo "No manual symlinks — dispatcher will auto-create on first spawn"

# Create a test task
hermes kanban create "Test" --assignee <name> --body "If you see this, the setup works."
hermes kanban dispatch
sleep 60
hermes kanban list | grep <name>
```