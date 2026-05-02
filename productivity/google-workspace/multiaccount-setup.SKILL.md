---
name: google-workspace-multiaccount
description: Multi-account OAuth setup for Google Workspace — parameterized token paths, --account flag, default account migration
---

# Google Workspace Multi-Account Setup

## Purpose

Extend the `google-workspace` skill to support multiple Google accounts (e.g., `ogodev`, `svaaugust`) with a configurable default account. Tokens are stored per-account: `google_token_<account>.json`.

## When to Use

- Need to access multiple Gmail/Calendar/Drive accounts from Hermes
- Switching default account (e.g., migrate from `ogodev` to `svaaugust`)
- Setting up a new Google account for automation

## Approach

### 1. Parameterize token paths

In `setup.py`, `google_api.py`, `tasks_api.py`:

```python
def get_token_path(account: str) -> Path:
    return HERMES_HOME / f"google_token_{account}.json"

def get_client_secret_path(account: str) -> Path:
    return HERMES_HOME / f"google_client_secret_{account}.json"
```

Replace all `TOKEN_PATH` literal usages with `get_token_path(account)`.

### 2. Add `--account` argument

```python
parser.add_argument("--account", default="svaaugust", help="Account identifier (ogodev or svaaugust)")
```

Store account globally after parsing:

```python
args = parser.parse_args()
global ACCOUNT
ACCOUNT = args.account if args.account else "svaaugust"
```

### 3. Propagate account through all operations

Every function that touches token or client secret must accept `account` parameter:

```python
def check_auth(account: str):
    token_path = get_token_path(account)
    # ...

def store_client_secret(path: str, account: str):
    dest = get_client_secret_path(account)
    # ...

def get_auth_url(account: str):
    client_secret_path = get_client_secret_path(account)
    # ...
```

### 4. Fix common pitfalls

**Path operator corruption:** Some repo files use `*** /` instead of `/` — patch them:
```bash
# Replace in setup.py/google_api.py
*** / "google_token.json" → HERMES_HOME / f"google_token_{account}.json"
```

**Syntax error — global before assignment:** `global ACCOUNT` must appear *before* `ACCOUNT = ...` in main block, or omit entirely in module scope.

**Subprocess PYTHONPATH:** When calling `google_api.py` via shell, prepend PYTHONPATH to the command, don't wrap in `python3 -c "cmd"`:

```python
# WRONG
subprocess.run(f'python3 -c "cd ... && python3 google_api.py ..."', shell=True)

# CORRECT
cmd = f'cd ... && PYTHONPATH=... python3 google_api.py --account svaaugust ...'
subprocess.run(cmd, shell=True)
```

### 5. Update brief modules

In `brief/gmail.py` and `brief/calendar.py`, add explicit `--account svaaugust` flag:

```python
cmd = f'cd {GOOGLE_WORKSPACE_SCRIPTS} && PYTHONPATH={GOOGLE_SITE_PACKAGES}:. /usr/bin/python3 google_api.py --account svaaugust gmail search "is:unread" --max 7'
```

### 6. Add missing scopes and re-auth

If a service (e.g., Tasks) returns "Not authenticated" or missing scopes:

- Add the scope to `SCOPES` in `setup.py` and `google_api.py`
- Re-run auth flow:
  ```bash
  python3 setup.py --auth-url --account svaaugust
  # paste new redirect URL
  python3 setup.py --auth-code "FULL_URL" --account svaaugust
  ```

## Verification

```bash
# Check auth
python3 setup.py --check --account svaaugust

# Test Gmail
python3 google_api.py --account svaaugust gmail search "is:unread" --max 3

# Test Calendar
python3 google_api.py --account svaaugust calendar list

# Test Tasks (requires tasks scope)
python3 tasks_api.py --account svaaugust lists
```

## Files Modified

- `setup.py`: added `--account`, parameterized paths, updated SCOPES
- `google_api.py`: same + fixed subprocess calls
- `tasks_api.py`: same
- `brief/gmail.py`: explicit `--account svaaugust`
- `brief/calendar.py`: explicit `--account svaaugust`
