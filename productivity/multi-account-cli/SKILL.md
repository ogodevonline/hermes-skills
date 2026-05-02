---
name: multi-account-cli
description: Паттерн для поддержки нескольких аккаунтов в CLI-скриптах через флаг --account
---

# Multi-Account CLI Pattern

**Reusable pattern** for adding per-account isolation to CLI tools. Each account gets its own config/token files via filename templating.

## When to Use

- Scripts need to operate on behalf of multiple user accounts (Google, GitHub, Telegram, etc.)
- You want to avoid mixing credentials and data between accounts
- Default account should be configurable

## Core Idea

1. **Add global `ACCOUNT` variable** (default: `<default_account>`)
2. **Parameterize all file paths** using `f"prefix_{ACCOUNT}.json"` or similar
3. **Add `--account` flag** to CLI argument parser
4. **Set `ACCOUNT` in `main()`** after parsing args: `ACCOUNT = args.account if args.account else "<default>"`
5. **Helper function** `get_config_path(suffix: str) -> Path` returns `HERMES_HOME / f"{suffix}_{ACCOUNT}.json"`

## Example Implementation

```python
import argparse
from pathlib import Path

ACCOUNT = "default"  # default account

def get_token_path() -> Path:
    return HERMES_HOME / f"token_{ACCOUNT}.json"

def get_config_path() -> Path:
    return HERMES_HOME / f"config_{ACCOUNT}.json"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default="default", help="Account identifier")
    sub = parser.add_subparsers()
    # ... subcommands ...
    args = parser.parse_args()
    global ACCOUNT
    ACCOUNT = args.account if args.account else "default"
    # ... rest of program using get_token_path() ...
```

## File Naming Convention

- Tokens: `~/.hermes/<service>_token_<account>.json`
- Client secrets: `~/.hermes/<service>_client_secret_<account>.json`
- Configs: `~/.hermes/<service>_config_<account>.json`
- Pending auth: `~/.hermes/<service>_pending_<account>.json`

## Applied Examples

- `google-workspace` — Gmail, Calendar, Drive, Tasks (accounts: `ogodev`, `svaaugust`; default: `svaaugust`)
-未来的技能: `himalaya` (если понадобится multi-account для почты)

## Migration from Single-Account

1. Rename existing file: `token.json` → `token_<olddefault>.json`
2. Update all path references to use templated filename
3. Add `--account` flag and global `ACCOUNT` variable
4. Update docs and cron jobs to explicitly pass `--account` if non-default

## Pitfalls

- **`global` keyword**: Only needed inside functions that assign to the global variable. In module-level code (outside functions), `global` is NOT allowed — just assign directly. In `main()`, use `global ACCOUNT` before `ACCOUNT = ...` only if you later modify it in nested functions; otherwise simple assignment works if no nested function writes to it.
- **Order of operations**: Set `ACCOUNT` immediately after `parse_args()` before any function that relies on it is called.
- **Default switching**: Changing the default account requires updating all places where `ACCOUNT = "..."` appears (typically 3 locations: top-level default, `main()` fallback, and docs).
- **Legacy scripts**: Old cron jobs or scripts that don't pass `--account` will silently switch to the new default — verify desired behavior.
