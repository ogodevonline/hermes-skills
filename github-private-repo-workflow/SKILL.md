---
name: github-private-repo-workflow
description: "Diagnose and resolve 'repo not found' when cloning private repos, especially when the user's local remote URL differs from their authenticated GitHub account."
category: github
---

# Private Repo Cloning Workflow

When a user asks you to clone their private GitHub repo and the initial lookup fails, follow this diagnostic flow.

## Trigger

- User shows `git remote -v` from their local machine with owner A
- `gh repo view A/repo` or API returns 404

## Diagnostic Flow

1. **Don't assume the repo doesn't exist.** The most common scenario: the user pushed/moved the repo to a **different account** (the one you're authenticated as).

2. **Check the authenticated account first:**
   ```bash
   gh repo list --limit 50 --json name --jq '.[].name' | grep -i <reponame>
   ```

3. **If found** → clone from the authenticated account's repo.

4. **If not found** → ask the user directly: "Did you push/move this repo to a different account? Your local remote shows `ownerA`, but my token is for `ownerB`."

## Common Causes

| Symptom | Likely Cause |
|---------|-------------|
| `remote -v` shows `ownerA/repo`, gh returns 404 | User uploaded repo to `ownerB` without updating local remote |
| `ogoclients/repo` doesn't resolve | `ogoclients` may be the original source, user forked/moved to their own account |
| `gh auth login --with-token` fails with `read:org` required | Fine-grained token without org access — use curl instead of gh for API calls |

## Workaround: gh auth with fine-grained tokens

Fine-grained tokens without `read:org` fail `gh auth login --with-token` validation but work fine for:
- `curl` API calls via `Authorization: token $TOKEN`
- `git clone` via credential-embedded URL
- `gh repo clone` (if `gh auth login` was done separately with a classic token)

## Re-auth when the saved token is invalid (check before creating/cloning)

A stale PAT in `~/.config/gh/hosts.yml` or `~/.git-credentials` shows as `X Failed to log in ... token is invalid` in `gh auth status`. Verify which sources actually hold a live token:

```bash
gh auth status                     # → "token is invalid" means re-auth needed
TOKEN=$(grep "github.com" ~/.git-credentials | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
curl -s -H "Authorization: token $TOKEN" https://api.github.com/user \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('login') or 'Bad credentials')"
```

Fix with a fresh classic PAT (scope `repo`):

```bash
echo '<PAT>' | gh auth login --with-token
gh auth status        # ✓ Logged in
```

Don't assume `~/.hermes/.env` GITHUB_TOKEN is populated — it may be empty while `.git-credentials` / `gh hosts.yml` hold the live token (or vice versa). Check all three.

## Creating a new private repo from an existing local dir

```bash
# In the project dir: init, commit, then create+push in one shot
git init -b main && git add -A && git commit -m "chore: initial"
gh repo create <name> --private --source . --push --description "..."
# Verify visibility (PRIVATE!) — public is the default if you forget --private
gh repo view <owner>/<name> --json visibility,url --jq '{visibility, url}'
```

`--source . --push` beats create-then-add-remote: one command, no remote-URL typos, default branch pushed. Check the user's existing repo list first (`gh repo list`) — the project may already exist under their account.

## Pitfalls

- **`ogoclients` is a USER, not an organization** — don't check `gh api orgs/ogoclients`, check `gh api users/ogoclients`
- **User says "я зашрузил"** (I uploaded it) — means they pushed the repo to the authenticated account. Check there first.
- **Never tell the user "this repo doesn't exist"** when they just showed you a remote URL. The repo exists somewhere; you need to find where.
