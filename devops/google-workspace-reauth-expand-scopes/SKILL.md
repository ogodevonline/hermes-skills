---
name: google-workspace-reauth-expand-scopes
description: Re-authorize Google OAuth token with additional scopes (e.g., adding Tasks after initial setup)
---

# Google Workspace: Re-authorization for Scope Expansion

When you need to add new API scopes to an existing Google OAuth token (e.g., adding `https://www.googleapis.com/auth/tasks` after initial Gmail/Calendar setup), you must re-authorize the account. The existing token is not automatically expanded.

## Prerequisites

- OAuth client JSON saved: `~/.hermes/google_client_secret_<account>.json`
- Token exists: `~/.hermes/google_token_<account>.json`
- `setup.py` SCOPES updated to include the new scope(s)

## Step-by-Step

### 1. Verify Current Token Scopes

Check what scopes the current token has:

```bash
cd ~/.hermes/skills/productivity/google-workspace/scripts
python3 setup.py --check --account <account>
```

Test the API that requires the new scope (e.g., `tasks_api.py lists`) — if it fails with permission error, scope is missing.

### 2. Ensure SCOPES in setup.py Includes New Scope

Open `scripts/setup.py` and confirm `SCOPES` list includes the new scope:

```python
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/contacts.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/tasks',  # ← added
]
```

### 3. Generate Fresh OAuth Authorization URL

```bash
python3 setup.py --auth-url --account <account> --format json
```

Extract the `auth_url` from the JSON output.

**Important:** Use this NEW URL — do not reuse an old URL. The new URL contains the updated scope list.

### 4. User Authorizes

1. Open the auth URL in browser
2. Sign in as the correct Google account (`<account>@gmail.com`)
3. Review permissions — ensure all scopes (including new one) are listed
4. Approve
5. Browser redirects to `http://localhost:1/?code=...` (fails to load — that's expected)
6. Copy the **entire URL** from the browser address bar

### 5. Exchange Code for New Token

```bash
python3 setup.py --auth-code "PASTE_FULL_URL_HERE" --account <account>
```

The script extracts the code and saves a new token to `~/.hermes/google_token_<account>.json` with the expanded scopes and a new refresh token.

### 6. Verify

```bash
# Check token file
python3 setup.py --check --account <account>

# Test the previously failing API
python3 tasks_api.py lists --account <account>
```

Expected: non-empty output (JSON array of task lists).

## Pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: No module named 'google.oauth2'` | venv missing google-auth | Run `python3 -m ensurepip --upgrade` then `pip install google-api-python-client google-auth-oauthlib google-auth-httplib2` in the venv |
| `setup.py` not found | Wrong path | Use `~/.hermes/skills/productivity/google-workspace/scripts/` |
| Token still missing scope after re-auth | Used old auth URL | Regenerate auth URL with updated SCOPES and repeat |
| `Error 403: access_denied` | OAuth client in Testing mode, user not added as test user | Add user at https://console.cloud.google.com/auth/audience |

## Automation Note

For scripted re-auth, pass just the code (not full URL):

```bash
python3 setup.py --auth-code "4/0A..." --account svaaugust
```

The `setup.py` parser extracts the code from either a full URL or a bare code string.

## Related

- Skill: `google-workspace` — general usage of Gmail, Calendar, Drive, Tasks APIs
- Skill: `morning-brief-pipeline` — integrates Google APIs into daily brief
