# no_agent cron scripts — patterns and pitfalls

## Absolute paths ONLY

no_agent cron scripts have NO shell environment — no `$PATH`, no `$HOME`, no aliases. Every tool must be referenced by absolute path.

**Bad:**
```bash
SCRIPTDIR=/home/hermes/scripts
python3 "$SCRIPTDIR/gitmark.py" lint --strict    # если gitmark.py не в этом dir — крах
```

**Good:**
```bash
GITMARK=/home/hermes/.hermes/scripts/gitmark.py
ENSURE=/home/hermes/scripts/gotham-ensure-frontmatter.py
STALE=/home/hermes/scripts/gotham-stale-status.py

OUTPUT=$(python3 "$GITMARK" lint --strict 2>&1)
FM_OUTPUT=$(python3 "$ENSURE" --all --mode=add-missing 2>&1)
STALE_OUTPUT=$(python3 "$STALE" --set=archived --confirm-after=90d 2>&1)
```

## Script location for cron jobs

Cron jobs (`cronjob(action='create', script='name')`) expect scripts relative to `~/.hermes/scripts/`. Cron resolves relative paths against `~/.hermes/scripts/` (not cwd).

```bash
# Create script in the right place
mv /home/hermes/scripts/myscript.sh /home/hermes/.hermes/scripts/myscript.sh

# Then create cron job — pass just the filename
cronjob(action='create', name='my-job', schedule='0 3 * * *', script='myscript.sh', no_agent=True)
```

## The report-file chicken-and-egg

If the script creates a report file that itself lacks frontmatter, `gitmark.py lint --strict` will find it as ERR on the first run. The ensure-frontmatter script must run AFTER the report is created to fix it. Pattern:

```bash
LOGFILE="$VAULT/System/Gotham/report-$(date +%Y-%m-%d).md"
echo "# Report" > "$LOGFILE"

# Lint — the report file itself causes ERR
OUTPUT=$(python3 "$GITMARK" lint --strict 2>&1)

# Fix — ensure-frontmatter patches the report too
if echo "$OUTPUT" | grep -q "ERR"; then
    python3 "$ENSURE" --all --mode=add-missing
fi
```

## Pre-commit hook interaction

If the vault has a pre-commit hook that runs `gitmark.py lint --strict`, any `git commit` in the nightly script will be blocked unless ALL ERR are resolved first. The nightly script must fix ERR before attempting to commit.

The script flow should be:
1. Lint → detect ERR
2. If ERR → run ensure-frontmatter + stale-status
3. Then git add + git commit (now ERR=0, hook passes)

## Testing

Always run the script manually before relying on the cron schedule:
```bash
cd /home/hermes/hermes-vault && bash /home/hermes/.hermes/scripts/myscript.sh
```

Then check the report file and git log to verify it worked.
