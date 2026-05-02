# Google Workspace Skill (Updated)

> **Note**: Use this skill for ALL Google services. Use google-workspace, NOT himalaya (deprecated).

## Overview

**Skill**: `google-workspace` | **Version**: 1.0.0 | **License**: MIT

Integrates Gmail, Calendar, Drive, Contacts, Sheets, and Docs through Hermes-managed OAuth2. Uses the Google Workspace CLI (`gws`) when available for broader API coverage; falls back to bundled Python client otherwise.

---

## First-Time Setup

> **⚠️ Installation Issue**: The original scripts have a broken import and corrupted path syntax. See [Installation Fixes](#installation-fixes) below before running commands.

---

## Installation Fixes

> **Problem**: The GitHub raw files have two issues:
> 1. Scripts import `hermes_constants` module that doesn't exist standalone
> 2. Path operators are corrupted (`*** /` instead of proper `/`operator)

> **Fix**: The following files are already patched in `~/.hermes/skills/productivity/google-workspace/`:
> - `scripts/hermes_constants.py` — stub module with Path-based `get_hermes_home()`
> - Patched path operators in `setup.py` and `google_api.py`

> **Venv repair (if `google.oauth2` import fails):** The bundled venv at `~/.hermes/hermes-agent/venv/` may have a broken pip. Fix:
> ```bash
> ~/.hermes/hermes-agent/venv/bin/python3 -m ensurepip --upgrade
> ~/.hermes/hermes-agent/venv/bin/pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
> ```

> **Verify**:
> ```bash
> cd ~/.hermes/skills/productivity/google-workspace/scripts
> python3 setup.py --check
> # Should print "NOT_AUTHENTICATED" (not crash)
> ```

> **If scripts not yet fixed**, apply manually:
> 1. Create `scripts/hermes_constants.py`:
> ```python
> """Hermes constants stub for google-workspace skill"""
> import os
> from pathlib import Path
> 
> def get_hermes_home():
>     return Path(os.path.expanduser("~/.hermes"))
> 
> def display_hermes_home():
>     return "~/.hermes"
> ```
> 2. Patch path operators in `setup.py` and `google_api.py`:
>    - `*** / "file.json"` → `HERMES_HOME / "file.json"`

---

### Step 0: Check if Already Set Up

```bash
cd ~/.hermes/skills/productivity/google-workspace/scripts
python3 setup.py --check
```
If it prints `AUTHENTICATED`, skip to Usage.

### Step 1: Determine Service Needs

| Use Case | Action |
|----------|--------|
| **Email only** | Use `himalaya` skill instead (App Password, no Google Cloud project needed) |
| **Email + Calendar** | Use `--services email,calendar` during auth |
| **Calendar/Drive/Sheets/Docs only** | Use narrower `--services` set |
| **Full Workspace** | Use default `all` service set |

**Advanced Protection Check**: If user's Google account uses hardware security keys, their Workspace admin must allowlist the OAuth client ID before Step 4.

### Step 2: Create OAuth Credentials (~5 minutes)

1. Create/select project: https://console.cloud.google.com/projectselector2/home/dashboard
2. Enable APIs: Gmail API, Google Calendar API, Google Drive API, Google Sheets API, Google Docs API, People API
3. Create OAuth client: https://console.cloud.google.com/apis/credentials → OAuth 2.0 Client ID → Desktop app
4. If app is in Testing, add user as test user: https://console.cloud.google.com/auth/audience
5. Download JSON file

> **CLI Note**: If file path starts with `/`, send it in a sentence (e.g., "The JSON file path is: /home/user/Downloads/client_secret.json") to avoid being mistaken for a slash command.

```bash
$GSETUP --client-secret /path/to/client_secret.json
```

### Step 3: Get Authorization URL

```bash
$GSETUP --auth-url --services email,calendar --format json
$GSETUP --auth-url --services all --format json
```

- Extract `auth_url` field and send exact URL to user
- Tell user browser will fail on `http://localhost:1/` after approval (expected)
- Have them copy the ENTIRE redirected URL from browser address bar
- If they get `Error 403: access_denied`, send them to https://console.cloud.google.com/auth/audience to add as test user

### Step 4: Exchange the Code

```bash
$GSETUP --auth-code "THE_URL_OR_CODE_THE_USER_PASTED" --format json
```

Accepts either full URL (`http://localhost:1/?code=4/0A...&scope=...`) or just the code string. If code expired, returns a fresh `auth_url` — send the new URL immediately.

### Step 5: Verify

```bash
$GSETUP --check
```
Should print `AUTHENTICATED`. Setup complete — token auto-refreshes.

---

## Multiple Accounts (Default: svaaugust)

The skill supports multiple Google accounts via the `--account` flag.

**Default account:** `svaaugust` (changed from `ogodev`). All scripts use `svaaugust` by default unless `--account ogodev` is explicitly passed.

**Token and secret files:**
- Tokens: `~/.hermes/google_token_<account>.json`
- Client secrets: `~/.hermes/google_client_secret_<account>.json` (can be shared across accounts)

**Usage:**
```bash
cd ~/.hermes/skills/productivity/google-workspace/scripts

# Use default (svaaugust)
python3 google_api.py gmail search "is:unread" --max 5

# Explicit account
python3 google_api.py --account ogodev gmail search "is:unread"
python3 tasks_api.py --account svaaugust lists
```

**Setup a new account:**
```bash
# 1. Store client secret (reuse same or different JSON)
python3 setup.py --client-secret /path/to/client_secret.json --account svaaugust

# 2. Get OAuth URL
python3 setup.py --auth-url --account svaaugust

# 3. User authorizes and pastes redirect URL or code
python3 setup.py --auth-code "PASTE_FULL_URL_OR_CODE" --account svaaugust

# 4. Verify
python3 setup.py --check --account svaaugust
```

**Important notes:**
- To use Google Tasks, the `https://www.googleapis.com/auth/tasks` scope must be in SCOPES and the token re-authorized (see skill `google-workspace-reauth-expand-scopes`)
- Brief modules (`brief/gmail.py`, `brief/calendar.py`) explicitly pass `--account svaaugust` in their subprocess calls — this overrides any default and ensures they always use the correct account
- If token missing required scopes, re-run setup with the updated SCOPES (see Re-authorization skill)
- Token files are per-account: `~/.hermes/google_token_<account>.json`, NOT `~/.hermes/google_token.json`


## Usage Commands

Run from the scripts directory:
```bash
cd ~/.hermes/skills/productivity/google-workspace/scripts
GAPI="python3 $(pwd)/google_api.py"
```

Or set shorthand:

### Gmail

```bash
# Search (returns JSON array with id, from, subject, date, snippet)
$GAPI gmail search "is:unread" --max 10
$GAPI gmail search "from:boss@company.com newer_than:1d"
$GAPI gmail search "has:attachment filename:pdf newer_than:7d"

# Read full message
$GAPI gmail get MESSAGE_ID

# Send
$GAPI gmail send --to user@example.com --subject "Hello" --body "Message text"
$GAPI gmail send --to user@example.com --subject "Report" --body "Details..." --html
$GAPI gmail send --to user@example.com --subject "Hello" --from '"Research Agent" ' --body "Message text"

# Reply (automatically threads)
$GAPI gmail reply MESSAGE_ID --body "Thanks, that works for me."

# Labels
$GAPI gmail labels
$GAPI gmail modify MESSAGE_ID --add-labels LABEL_ID
$GAPI gmail modify MESSAGE_ID --remove-labels UNREAD
```

### Calendar

```bash
# List events (defaults to next 7 days)
$GAPI calendar list
$GAPI calendar list --start 2026-03-01T00:00:00Z --end 2026-03-07T23:59:59Z

# Create event (ISO 8601 with timezone required)
$GAPI calendar create --summary "Team Standup" --start 2026-03-01T10:00:00-06:00 --end 2026-03-01T10:30:00-06:00
$GAPI calendar create --summary "Lunch" --start 2026-03-01T12:00:00Z --end 2026-03-01T13:00:00Z --location "Cafe"
$GAPI calendar create --summary "Review" --start 2026-03-01T14:00:00Z --end 2026-03-01T15:00:00Z --attendees "alice@co.com,bob@co.com"

# Delete event
$GAPI calendar delete EVENT_ID
```

### Drive

```bash
$GAPI drive search "quarterly report" --max 10
$GAPI drive search "mimeType='application/pdf'" --raw-query --max 5
```

### Contacts

```bash
$GAPI contacts list --max 20
```

### Sheets

```bash
# Read
$GAPI sheets get SHEET_ID "Sheet1!A1:D10"

# Write
$GAPI sheets update SHEET_ID "Sheet1!A1:B2" --values '[["Name","Score"],["Alice","95"]]'
# Append rows
$GAPI sheets append SHEET_ID "Sheet1!A:C" --values '[["new","row","data"]]'
```

### Docs

```bash
$GAPI docs get DOC_ID
```

### Tasks

```bash
# Lists (task lists)
python3 ~/.hermes/skills/productivity/google-workspace/scripts/tasks_api.py lists

# Tasks in a list
python3 ~/.hermes/skills/productivity/google-workspace/scripts/tasks_api.py tasks LIST_ID

# Add task
python3 ~/.hermes/skills/productivity/google-workspace/scripts/tasks_api.py add "Задача" --notes "заметки" --due "2026-04-20T12:00:00Z"

# Complete task
python3 ~/.hermes/skills/productivity/google-workspace/scripts/tasks_api.py complete TASK_ID --list-id LIST_ID

# Delete task
python3 ~/.hermes/skills/productivity/google-workspace/scripts/tasks_api.py delete TASK_ID --list-id LIST_ID
```

> **Note**: Tasks API requires `https://www.googleapis.com/auth/tasks` scope. Re-authenticate with expanded scope if needed.

---

## Adding New Google APIs

The skill can be extended to support additional Google APIs. Process:

1. **Enable API** in Google Cloud Console → APIs & Services → Enable APIs
2. **Get auth URL** with new scope and user authorizes
3. **Exchange code** for token (auto-refresh handles the rest)
4. **Create CLI script** following pattern of `tasks_api.py`:
   - Use `google.oauth2.credentials.Credentials` with token from `~/.hermes/google_token.json`
   - Use `googleapiclient.discovery.build('service', 'version', credentials=creds)`
   - Parse args, call API, output JSON to stdout

Example: See `scripts/tasks_api.py` (already installed).