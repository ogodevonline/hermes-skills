# Post-Update Conflict Resolution (Rebase + Stash)

`hermes update` uses `git pull --rebase` internally. When you have local patches (kanban fixes, hub command, terminal tool patches), the rebase can leave conflicts. This reference documents the resolution workflow.

## Detection

```bash
cd ~/.hermes/hermes-agent
git status
# → "interactive rebase in progress; onto <SHA>"
# → "both modified: ..." under Unmerged paths
```

## Diagnostic Commands

```bash
# Which files have conflicts?
git diff --name-only --diff-filter=U

# What are the conflict markers?
grep -n '<<<<<<<\|=======\|>>>>>>>' <file>

# What is the local commit being applied?
cat .git/rebase-merge/done

# What version are we rebasing ONTO?
cat .git/rebase-merge/onto
git log --oneline -1 $(cat .git/rebase-merge/onto)

# Was our local patch already merged upstream?
git log --oneline origin/main -- <conflicting-file> | head -10
```

## Resolution Strategy

| Situation | Choice | Command |
|-----------|--------|---------|
| Core Hermes file (gateway/run.py, tools/terminal_tool.py, cli.py) — upstream added features | `--ours` (upstream — the newer version) | `git checkout --ours <file>` |
| Local-only patch (kanban_db.py, custom commands) — not in upstream | `--theirs` (your version) | `git checkout --theirs <file>` |
| Both sides have changes you want | Manual merge in editor | Resolve conflict markers by hand |

### The `--ours` / `--theirs` meaning in rebase context

During `git rebase`:
- **`--ours`** = version being rebased ONTO (upstream/main, the newer Hermes release)
- **`--theirs`** = version of the commit being applied (your local patch)

This is the **OPPOSITE** of merge conflict semantics — be careful!

### After resolving all file conflicts

```bash
git add <file1> <file2> ...
# Check no more conflicts
git diff --name-only --diff-filter=U  # should be empty
git rebase --continue
```

If the rebase continues, watch for:
- `ERROR: anchor pattern not found in <file> -- patch may already be different` — harmless, usually means a post-rebase script tried to patch a now-updated file. The rebase itself succeeded.
- `Successfully rebased and updated refs/heads/main` — confirmed.

## Stash Conflicts (After Rebase)

If local changes were auto-stashed before `hermes update`:

```bash
git stash pop
# → CONFLICT (content): Merge conflict in <file>
```

The stash usually contains changes NOT in the rebased commit (e.g., hub command, config changes).

### Decision matrix for stash conflicts

| Conflict | Resolution |
|----------|-----------|
| Stash adds code, upstream also adds code in the same area | Merge both — keep upstream's AND stash's additions |
| Stash adds a new method, upstream doesn't touch that area | Take stash (it's the only meaningful change) |
| Stash adds a command, upstream adds different commands nearby | Keep both — combine in the right order |

### Pattern for combining both sides

```python
<<<<<<< Updated upstream
        elif canonical == "moa":
            # ... upstream's new code ...
        elif canonical == "subgoal":
            self._handle_subgoal_command(cmd_original)
=======
        elif canonical == "hub":
            self._handle_hub_command()
>>>>>>> Stashed changes
```

→ Resolve to:
```python
        elif canonical == "moa":
            # ... upstream's new code ...
        elif canonical == "subgoal":
            self._handle_subgoal_command(cmd_original)
        elif canonical == "hub":
            self._handle_hub_command()
```

### After resolving stash conflicts

```bash
git add <all conflicted files>
git commit -m "feat: <description of stash changes>"
git stash drop   # only if stash pop left it (it does when conflicts occurred)
```

⚠️ **`git stash pop` with conflicts leaves the stash intact.** When `git stash pop` hits conflicts, it does NOT remove the stash entry — it keeps it so you can retry. After you commit the resolved changes, you MUST `git stash drop` explicitly, or the stale stash will remain forever.

## Post-Resolution Cleanup

### Add generated files to .gitignore

After rebase + stash resolution, untracked files may appear that were created by Hermes during runtime:

```bash
git status --short
# → ?? .gitmark/          # GitMark index cache
# → ?? gateway_healthcheck.sh  # Generated per-env
```

Add them to `.gitignore`:

```gitignore
# GitMark index cache
.gitmark/

# Gateway healthcheck (generated per-env)
gateway_healthcheck.sh
```

After adding, `git status` will show `M .gitignore` — commit it if desired, or leave as a local change. The ignored files won't appear in future `git status`.

## Post-Resolution Verification

```bash
# Git status
git status --short          # should show only untracked files

# Log
git log --oneline -5

# Import check (gatway/run.py is the heaviest — most likely to break)
python -c "import gateway.run" 2>&1 | grep -v Deprecated

# Import check (commands/cli)
python -c "import hermes_cli.commands; print('OK')"
```

## Common Patterns

### Pattern 1: Only gateway/run.py conflicts (44+ conflicts)

Typical when upstream refactored gateway and your local commit modified it too. All conflicts look like:
```
<<<<<<< HEAD
... new upstream code (functions, imports, classes) ...
=======
>>>>>>> local-commit (empty — your commit deleted the code)
```

**Resolution:** `git checkout --ours gateway/run.py` — take all upstream changes.

### Pattern 2: Stash has /hub command or other CLI additions

Stored in stash as 3-file patch (cli.py, gateway/run.py, hermes_cli/commands.py). After rebase, stash pop creates conflicts because upstream also modified those files.

**Resolution:** Merge both sides — keep upstream's new commands AND add hub/hub handler.

### Pattern 3: terminal_tool.py shows as conflicted but has no markers

Git marks the file as "both modified" but grep shows no `<<<<<<<` markers. This means the files were auto-merged.

**Resolution:** `git add tools/terminal_tool.py` — git will accept it as resolved.
