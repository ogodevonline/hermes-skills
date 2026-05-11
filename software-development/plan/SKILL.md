---
name: plan
description: "Plan mode: write markdown plan to .hermes/plans/, no exec."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [planning, plan-mode, implementation, workflow]
    related_skills: [writing-plans, subagent-driven-development]
---

# Plan Mode

Use this skill when the user wants a plan instead of execution.

## Core behavior

For this turn, you are planning only.

- Do not implement code.
- Do not edit project files except the plan markdown file.
- Do not run mutating terminal commands, commit, push, or perform external actions.
- You may inspect the repo or other context with read-only commands/tools when needed.
- Your deliverable is a markdown plan saved inside the active workspace under `.hermes/plans/`.

## Output requirements

Write a markdown plan that is concrete and actionable.

Include, when relevant:
- Goal
- Current context / assumptions
- Proposed approach
- Step-by-step plan
- Files likely to change
- Tests / validation
- Risks, tradeoffs, and open questions

If the task is code-related, include exact file paths, likely test targets, and verification steps.

## Save location

Save the plan with `write_file` under:
- `.hermes/plans/YYYY-MM-DD_HHMMSS-<slug>.md`

Treat that as relative to the active working directory / backend workspace. Hermes file tools are backend-aware, so using this relative path keeps the plan with the workspace on local, docker, ssh, modal, and daytona backends.

**Before writing, ensure the directory exists:**
- Run `mkdir -p .hermes/plans/` or `mkdir -p ~/.hermes/plans/` first if write_file fails due to missing directory.

If the runtime provides a specific target path, use that exact path.
If not, create a sensible timestamped filename yourself under `.hermes/plans/`.

### Fallback if write_file fails

If write_file (or any file tool) fails — e.g. directory not found, permission denied, or tool interruption — present the full plan directly in your response output. State the attempted file path so the user can copy it manually if they want. Do not silently skip saving; always attempt first, then fall back.

## Interaction style

- If the request is clear enough, write the plan directly.
- If no explicit instruction accompanies `/plan`, infer the task from the current conversation context.
- If it is genuinely underspecified, ask a brief clarifying question instead of guessing.
- After saving the plan, reply briefly with what you planned and the saved path.
- You may do read-only research (web_search, web_extract) to inform the plan — this is not "execution" and is allowed.

## Pitfalls

1. **Missing .hermes/plans/ directory.** Always create it first (`mkdir -p .hermes/plans/`) before attempting write_file. The tool may not auto-create parent directories.
2. **Tool interruptions mid-save.** If terminal or file tools keep getting interrupted, fall back to presenting the plan inline in the response.
3. **Research scope creep.** Plan mode allows read-only research, but don't over-research. 3-5 web searches is enough context for most plans. If the research doesn't yield useful data after 3 attempts, present what you have and flag the gaps.
4. **Non-code plans can skip code-specific sections.** The "Files likely to change", "Tests / validation", and exact file paths are for code plans. For travel, life, or process plans, replace those with domain-specific sections (e.g. budget, timeline, legal steps).
