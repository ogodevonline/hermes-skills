#!/usr/bin/env python3
"""Google Workspace OAuth2 setup for Hermes Agent.

Fully non-interactive — designed to be driven by the agent via terminal commands.
The agent mediates between this script and the user (works on CLI, Telegram, Discord, etc.)

Commands:
  setup.py --check [--account ogodev]             # Is auth valid? Exit 0 = yes, 1 = no
  setup.py --client-secret /path/to.json [--account ogodev]  # Store OAuth client credentials
  setup.py --auth-url [--account ogodev]          # Print the OAuth URL for user to visit
  setup.py --auth-code CODE [--account ogodev]    # Exchange auth code for token
  setup.py --revoke [--account ogodev]            # Revoke and delete stored token
  setup.py --install-deps                          # Install Python dependencies only

Agent workflow:
  1. Run --check. If exit 0, auth is good — skip setup.
  2. Ask user for client_secret.json path. Run --client-secret PATH.
  3. Run --auth-url. Send the printed URL to the user.
  4. User opens URL, authorizes, gets redirected to a page with a code.
  5. User pastes the code. Agent runs --auth-code CODE.
  6. Run --check to verify. Done.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    from hermes_constants import display_hermes_home, get_hermes_home
except ModuleNotFoundError:
    HERMES_AGENT_ROOT = Path(__file__).resolve().parents[4]
    if HERMES_AGENT_ROOT.exists():
        sys.path.insert(0, str(HERMES_AGENT_ROOT))
    from hermes_constants import display_hermes_home, get_hermes_home

HERMES_HOME = get_hermes_home()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/tasks",
]

REQUIRED_PACKAGES = ["google-api-python-client", "google-auth-oauthlib", "google-auth-httplib2"]

# OAuth redirect for "out of band" manual code copy flow.
REDIRECT_URI = "http://localhost:1"

def get_token_path(account: str) -> Path:
    return HERMES_HOME / f"google_token_{account}.json"

def get_client_secret_path(account: str) -> Path:
    return HERMES_HOME / f"google_client_secret_{account}.json"

def get_pending_auth_path(account: str) -> Path:
    return HERMES_HOME / f"google_oauth_pending_{account}.json"

def _normalize_authorized_user_payload(payload: dict) -> dict:
    normalized = dict(payload)
    if not normalized.get("type"):
        normalized["type"] = "authorized_user"
    return normalized

def _load_token_payload(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

def _missing_scopes_from_payload(payload: dict) -> list[str]:
    raw = payload.get("scopes") or payload.get("scope")
    if not raw:
        return []
    granted = {s.strip() for s in (raw.split() if isinstance(raw, str) else raw) if s.strip()}
    return sorted(scope for scope in SCOPES if scope not in granted)

def _format_missing_scopes(missing_scopes: list[str]) -> str:
    bullets = "\n".join(f"  - {scope}" for scope in missing_scopes)
    return (
        "Token is valid but missing required Google Workspace scopes:\n"
        f"{bullets}\n"
        "Run the Google Workspace setup again from this same Hermes profile to refresh consent."
    )

def install_deps():
    try:
        import googleapiclient  # noqa: F401
        import google_auth_oauthlib  # noqa: F401
        print("Dependencies already installed.")
        return True
    except ImportError:
        pass

    print("Installing Google API dependencies...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet"] + REQUIRED_PACKAGES,
            stdout=subprocess.DEVNULL,
        )
        print("Dependencies installed.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to install dependencies: {e}")
        print(f"Try manually: {sys.executable} -m pip install {' '.join(REQUIRED_PACKAGES)}")
        return False

def _ensure_deps():
    try:
        import googleapiclient  # noqa: F401
        import google_auth_oauthlib  # noqa: F401
    except ImportError:
        if not install_deps():
            sys.exit(1)

def check_auth(account: str):
    token_path = get_token_path(account)
    if not token_path.exists():
        print(f"NOT_AUTHENTICATED: No token at {token_path}")
        return False

    _ensure_deps()
    from google.oauth2.credentials import Credentials

    try:
        creds = Credentials.from_authorized_user_file(str(token_path))
    except Exception as e:
        print(f"TOKEN_CORRUPT: {e}")
        return False

    payload = _load_token_payload(token_path)
    if creds.valid:
        missing_scopes = _missing_scopes_from_payload(payload)
        if missing_scopes:
            print(f"AUTHENTICATED (partial): Token valid but missing {len(missing_scopes)} scopes:")
            for s in missing_scopes:
                print(f"  - {s}")
        print(f"AUTHENTICATED: Token valid at {token_path}")
        return True

    if creds.expired and creds.refresh_token:
        try:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            token_path.write_text(
                json.dumps(
                    _normalize_authorized_user_payload(json.loads(creds.to_json())),
                    indent=2,
                )
            )
            missing_scopes = _missing_scopes_from_payload(_load_token_payload(token_path))
            if missing_scopes:
                print(f"AUTHENTICATED (partial): Token refreshed but missing {len(missing_scopes)} scopes:")
                for s in missing_scopes:
                    print(f"  - {s}")
            print(f"AUTHENTICATED: Token refreshed at {token_path}")
            return True
        except Exception as e:
            print(f"REFRESH_FAILED: {e}")
            return False

    print("TOKEN_INVALID: Re-run setup.")
    return False

def store_client_secret(path: str, account: str):
    src = Path(path).expanduser().resolve()
    if not src.exists():
        print(f"ERROR: File not found: {src}")
        sys.exit(1)

    try:
        data = json.loads(src.read_text())
    except json.JSONDecodeError:
        print("ERROR: File is not valid JSON.")
        sys.exit(1)

    if "installed" not in data and "web" not in data:
        print("ERROR: Not a Google OAuth client secret file (missing 'installed' key).")
        print("Download the correct file from: https://console.cloud.google.com/apis/credentials")
        sys.exit(1)

    dest = get_client_secret_path(account)
    dest.write_text(json.dumps(data, indent=2))
    print(f"OK: Client secret saved to {dest}")

def _save_pending_auth(*, state: str, code_verifier: str, account: str):
    PENDING_AUTH_PATH = get_pending_auth_path(account)
    PENDING_AUTH_PATH.write_text(
        json.dumps(
            {
                "state": state,
                "code_verifier": code_verifier,
                "redirect_uri": REDIRECT_URI,
            },
            indent=2,
        )
    )

def _load_pending_auth(account: str) -> dict:
    PENDING_AUTH_PATH = get_pending_auth_path(account)
    if not PENDING_AUTH_PATH.exists():
        print("ERROR: No pending OAuth session found. Run --auth-url first.")
        sys.exit(1)

    try:
        data = json.loads(PENDING_AUTH_PATH.read_text())
    except Exception as e:
        print(f"ERROR: Could not read pending OAuth session: {e}")
        print("Run --auth-url again to start a fresh OAuth session.")
        sys.exit(1)

    if not data.get("state") or not data.get("code_verifier"):
        print("ERROR: Pending OAuth session is missing PKCE data.")
        print("Run --auth-url again to start a fresh OAuth session.")
        sys.exit(1)

    return data

def _extract_code_and_state(code_or_url: str) -> tuple[str, str | None]:
    if not code_or_url.startswith("http"):
        return code_or_url, None

    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(code_or_url)
    params = parse_qs(parsed.query)
    if "code" not in params:
        print("ERROR: No 'code' parameter found in URL.")
        sys.exit(1)

    state = params.get("state", [None])[0]
    return params["code"][0], state

def get_auth_url(account: str):
    client_secret_path = get_client_secret_path(account)
    if not client_secret_path.exists():
        print(f"ERROR: No client secret stored for account '{account}'. Run --client-secret first.")
        sys.exit(1)

    _ensure_deps()
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_secrets_file(
        str(client_secret_path),
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        autogenerate_code_verifier=True,
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )
    _save_pending_auth(state=state, code_verifier=flow.code_verifier, account=account)
    print(auth_url)

def exchange_auth_code(code: str, account: str):
    client_secret_path = get_client_secret_path(account)
    if not client_secret_path.exists():
        print(f"ERROR: No client secret stored for account '{account}'. Run --client-secret first.")
        sys.exit(1)

    pending_auth = _load_pending_auth(account)
    code, returned_state = _extract_code_and_state(code)
    if returned_state and returned_state != pending_auth["state"]:
        print("ERROR: OAuth state mismatch. Run --auth-url again to start a fresh session.")
        sys.exit(1)

    _ensure_deps()
    from google_auth_oauthlib.flow import Flow
    from urllib.parse import parse_qs, urlparse

    if returned_state and "scope" in parse_qs(urlparse(code).query if isinstance(code, str) and code.startswith("http") else {}):
        granted_scopes = parse_qs(urlparse(code).query)["scope"][0].split()
    else:
        if isinstance(code, str) and code.startswith("http"):
            params = parse_qs(urlparse(code).query)
            if "scope" in params:
                granted_scopes = params["scope"][0].split()
            else:
                granted_scopes = SCOPES
        else:
            granted_scopes = SCOPES

    flow = Flow.from_client_secrets_file(
        str(client_secret_path),
        scopes=granted_scopes,
        redirect_uri=pending_auth.get("redirect_uri", REDIRECT_URI),
        state=pending_auth["state"],
        code_verifier=pending_auth["code_verifier"],
    )

    try:
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
        flow.fetch_token(code=code)
    except Exception as e:
        print(f"ERROR: Token exchange failed: {e}")
        print("The code may have expired. Run --auth-url to get a fresh URL.")
        sys.exit(1)

    creds = flow.credentials
    token_payload = _normalize_authorized_user_payload(json.loads(creds.to_json()))

    actually_granted = list(creds.granted_scopes or []) if hasattr(creds, "granted_scopes") and creds.granted_scopes else []
    if actually_granted:
        token_payload["scopes"] = actually_granted
    elif granted_scopes != SCOPES:
        token_payload["scopes"] = granted_scopes

    missing_scopes = _missing_scopes_from_payload(token_payload)
    if missing_scopes:
        print(f"WARNING: Token missing some Google Workspace scopes: {', '.join(missing_scopes)}")
        print("Some services may not be available.")

    token_path = get_token_path(account)
    token_path.write_text(json.dumps(token_payload, indent=2))
    get_pending_auth_path(account).unlink(missing_ok=True)
    print(f"OK: Authenticated. Token saved to {token_path}")
    print(f"Profile-scoped token location: {display_hermes_home()}/google_token_{account}.json")

def revoke(account: str):
    token_path = get_token_path(account)
    if not token_path.exists():
        print("No token to revoke.")
        return

    _ensure_deps()
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        import urllib.request
        urllib.request.urlopen(
            urllib.request.Request(
                f"https://oauth2.googleapis.com/revoke?token={creds.token}",
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        )
        print("Token revoked with Google.")
    except Exception as e:
        print(f"Remote revocation failed (token may already be invalid): {e}")

    token_path.unlink(missing_ok=True)
    get_pending_auth_path(account).unlink(missing_ok=True)
    print(f"Deleted {token_path}")

def main():
    parser = argparse.ArgumentParser(description="Google Workspace OAuth setup for Hermes")
    parser.add_argument("--account", default="svaaugust", help="Account identifier (ogodev or svaaugust)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Check if auth is valid (exit 0=yes, 1=no)")
    group.add_argument("--client-secret", metavar="PATH", help="Store OAuth client_secret.json")
    group.add_argument("--auth-url", action="store_true", help="Print OAuth URL for user to visit")
    group.add_argument("--auth-code", metavar="CODE", help="Exchange auth code for token")
    group.add_argument("--revoke", action="store_true", help="Revoke and delete stored token")
    group.add_argument("--install-deps", action="store_true", help="Install Python dependencies")
    args = parser.parse_args()

    account = args.account

    if args.check:
        sys.exit(0 if check_auth(account) else 1)
    elif args.client_secret:
        store_client_secret(args.client_secret, account)
    elif args.auth_url:
        get_auth_url(account)
    elif args.auth_code:
        exchange_auth_code(args.auth_code, account)
    elif args.revoke:
        revoke(account)
    elif args.install_deps:
        sys.exit(0 if install_deps() else 1)

if __name__ == "__main__":
    main()
