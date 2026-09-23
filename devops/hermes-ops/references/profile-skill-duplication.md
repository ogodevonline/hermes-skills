# Profile Skill Duplication — Diagnostics & Fix

## The Problem

Each Hermes named profile maintains its own `skills/` directory. Heavy skills like `search` (crawl4ai + web-search-scraper) bundle **Playwright + Chromium** inside `.venv` — ~1.4 GB + ~826 MB per profile.

Most profiles don't need browser-based crawling, but the `.venv` gets installed anyway when the skill is loaded as a copy rather than a symlink.

## Quick Diagnostics

```bash
# Per-profile total skills size
for p in ~/.hermes/profiles/*/; do
  name=$(basename "$p")
  size=$(du -sh "$p/skills" 2>/dev/null | cut -f1)
  echo "$name: $size"
done

# Find any remaining heavy .venv across ALL profiles
find ~/.hermes/profiles -maxdepth 6 -name ".venv" -type d -exec du -sh {} \; 2>/dev/null | sort -rh

# Drill into a specific profile
du -sh ~/.hermes/profiles/<profile>/skills/*/ | sort -rh | head -10
```

## Full Audit: Symlinks vs Copies

Not all profiles are created equal — some skills are symlinks (light) and some are full copies (heavy, especially with `.venv`).

```bash
for p in ~/.hermes/profiles/*/; do
  name=$(basename "$p")
  copies=""; links=""
  for item in "$p"skills/*; do
    [ -e "$item" ] || continue
    if [ -L "$item" ]; then links="$links $(basename "$item")"
    else copies="$copies $(basename "$item")"; fi
  done
  echo "$name: 🔗$links  📀$copies"
done
```

### Symlink reference (who has what):

| Profile | Symlinked skills |
|---------|-----------------|
| architect | architecture-diagram, writing-plans |
| ask | web-search-scraper |
| coach | growth-coach, kanban-orchestrator |
| coder | git-init-before-edits, requesting-code-review, subagent-driven-development, test-driven-development, writing-plans |
| debugger | git-init-before-edits, kanban-worker, requesting-code-review, systematic-debugging, writing-plans |
| explorer | crawl4ai, web-search-scraper |
| learning | codegraph-cli, english-lesson, ielts-prep |
| orchestrator | kanban-orchestrator, subagent-driven-development, writing-plans |
| realtor | crawl4ai, maps, sub-agents-orchestrator, web-search-scraper |
| researcher | crawl4ai, kanban-worker, sub-agents-orchestrator, web-search-scraper |
| reviewer | github-code-review, requesting-code-review |
| scout | crawl4ai, ocr-and-documents, web-search-scraper |
| skill-writer | hermes-agent-skill-authoring, writing-plans |
| others | no symlinks (all copies) |

### Copy-only profiles (all skills are full copies, ~6 MB each):

self-improver, skill-improver, worker

### Total waste from copies: ~83 MB across all profiles (negligible — just SKILL.md files, no .venv).

The ONLY case where copies caused real disk bloat was when heavy `.venv` directories were present.

## Coach Profile Cleanup (May 2026)

Coach profile had 2.3 GB in `skills/search/` — the worst offender:

| Sub-skill | Size | What it was |
|-----------|------|-------------|
| crawl4ai/scripts/.venv | 1.4 GB | Playwright + Chromium |
| web-search-scraper/scripts/.venv | 826 MB | Playwright deps |

**Root cause:** The skills were installed as full **copies** (not symlinks) into the coach profile. Nearly all other profiles that need search skills use symlinks instead.

**Fix applied:**
```bash
# 1. Remove .venv directories (~2.3 GB freed)
rm -rf ~/.hermes/profiles/coach/skills/search/crawl4ai/scripts/.venv
rm -rf ~/.hermes/profiles/coach/skills/search/web-search-scraper/scripts/.venv

# 2. Replace copies with symlinks to main profile
rm -rf ~/.hermes/profiles/coach/skills/search/crawl4ai
rm -rf ~/.hermes/profiles/coach/skills/search/web-search-scraper
ln -s ~/.hermes/skills/search/crawl4ai ~/.hermes/profiles/coach/skills/search/crawl4ai
ln -s ~/.hermes/skills/search/web-search-scraper ~/.hermes/profiles/coach/skills/search/web-search-scraper
```

**Result:** coach/skills/search went from 2.3 GB → 0 (just symlinks).

**⚠️ Both `rm -rf` calls trigger approval gate** — user must explicitly confirm.

**Recovery (if symlinked skill needs its own venv):**
```bash
cd ~/.hermes/profiles/coach/skills/search/crawl4ai/scripts
uv sync
```

## Architecture Notes

- The `skills/` directory at `~/.hermes/skills/` is the **canonical source** of all skills.
- Profiles should reference skills via **symlinks** → `~/.hermes/skills/<category>/<name>`.
- 17 profiles exist as of May 2026 (architect, ask, coach, coder, debugger, explorer, learning, orchestrator, realtor, refactoring-guru, researcher, reviewer, scout, self-improver, skill-improver, skill-writer, worker).
- Each profile has a SOUL.md documenting its purpose and a config.yaml with model/toolset settings.
- There is NO central spec documenting which profile should have which skills — it's grown organically.
- Copies vs symlinks inconsistency happened because some profiles were created manually (symlinks) while others were created via Hermes tooling (copies).

## Why This Happens (Architecture)

Hermes profiles support both copies and symlinks for skills. A profile created via `hermes` tooling makes **copies** by default. Manually created profiles with `ln -s` use symlinks.

For profiles that only need SKILL.md metadata (not heavy dependencies like Playwright), copies are fine — ~6 MB is negligible. The issue is ONLY when heavy skills with `.venv` are duplicated.