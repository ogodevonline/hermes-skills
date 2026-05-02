#!/usr/bin/env python3
"""Google Workspace API CLI for Hermes Agent.

Supports multiple accounts via --account flag (ogodev|svaaugust).
Uses gws CLI when available, falls back to Python client libraries.
"""

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from pathlib import Path

HERMES_HOME = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
ACCOUNT = "svaaugust"  # default, will be overridden in main()

def get_token_path() -> Path:
    return HERMES_HOME / f"google_token_{ACCOUNT}.json"

def get_client_secret_path() -> Path:
    return HERMES_HOME / f"google_client_secret_{ACCOUNT}.json"

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

def _normalize_authorized_user_payload(payload: dict) -> dict:
    normalized = dict(payload)
    if not normalized.get("type"):
        normalized["type"] = "authorized_user"
    return normalized

def _ensure_authenticated():
    if not get_token_path().exists():
        print("Not authenticated. Run the setup script first:", file=sys.stderr)
        print(f"  python {Path(__file__).parent / 'setup.py'} --account {ACCOUNT}", file=sys.stderr)
        sys.exit(1)

def _stored_token_scopes() -> list[str]:
    try:
        data = json.loads(get_token_path().read_text())
    except Exception:
        return list(SCOPES)
    scopes = data.get("scopes")
    if isinstance(scopes, list) and scopes:
        return scopes
    return list(SCOPES)

def _gws_binary() -> str | None:
    override = os.getenv("HERMES_GWS_BIN")
    if override:
        return override
    return shutil.which("gws")

def _gws_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE"] = str(get_token_path())
    return env

def _run_gws(parts: list[str], *, params: dict | None = None, body: dict | None = None):
    binary = _gws_binary()
    if not binary:
        raise RuntimeError("gws not installed")

    _ensure_authenticated()

    cmd = [binary, *parts]
    if params is not None:
        cmd.extend(["--params", json.dumps(params)])
    if body is not None:
        cmd.extend(["--json", json.dumps(body)])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=_gws_env(),
    )
    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip() or "Unknown gws error"
        print(err, file=sys.stderr)
        sys.exit(result.returncode or 1)

    stdout = result.stdout.strip()
    if not stdout:
        return {}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        print("ERROR: Unexpected non-JSON output from gws:", file=sys.stderr)
        print(stdout, file=sys.stderr)
        sys.exit(1)

def _headers_dict(msg: dict) -> dict[str, str]:
    return {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

def _extract_message_body(msg: dict) -> str:
    body = ""
    payload = msg.get("payload", {})
    if payload.get("body", {}).get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    elif payload.get("parts"):
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                break
        if not body:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    break
    return body

def _extract_doc_text(doc: dict) -> str:
    text_parts = []
    for element in doc.get("body", {}).get("content", []):
        paragraph = element.get("paragraph", {})
        for pe in paragraph.get("elements", []):
            text_run = pe.get("textRun", {})
            if text_run.get("content"):
                text_parts.append(text_run["content"])
    return "".join(text_parts)

def _datetime_with_timezone(value: str) -> str:
    if not value:
        return value
    if "T" not in value:
        return value
    if value.endswith("Z"):
        return value
    tail = value[10:]
    if "+" in tail or "-" in tail:
        return value
    return value + "Z"

def get_credentials():
    _ensure_authenticated()
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    creds = Credentials.from_authorized_user_file(str(get_token_path()), _stored_token_scopes())
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        get_token_path().write_text(
            json.dumps(
                _normalize_authorized_user_payload(json.loads(creds.to_json())),
                indent=2,
            )
        )
    if not creds.valid:
        print("Token is invalid. Re-run setup.", file=sys.stderr)
        sys.exit(1)
    return creds

def build_service(api, version):
    from googleapiclient.discovery import build
    return build(api, version, credentials=get_credentials())

# =========================================================================
# Gmail
# =========================================================================

def gmail_search(args):
    if _gws_binary():
        results = _run_gws(
            ["gmail", "users", "messages", "list"],
            params={"userId": "me", "q": args.query, "maxResults": args.max},
        )
        messages = results.get("messages", [])
        output = []
        for msg_meta in messages:
            msg = _run_gws(
                ["gmail", "users", "messages", "get"],
                params={
                    "userId": "me",
                    "id": msg_meta["id"],
                    "format": "metadata",
                    "metadataHeaders": ["From", "To", "Subject", "Date"],
                },
            )
            headers = _headers_dict(msg)
            output.append(
                {
                    "id": msg["id"],
                    "threadId": msg["threadId"],
                    "from": headers.get("From", ""),
                    "to": headers.get("To", ""),
                    "subject": headers.get("Subject", ""),
                    "date": headers.get("Date", ""),
                    "snippet": msg.get("snippet", ""),
                    "labels": msg.get("labelIds", []),
                }
            )
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    service = build_service("gmail", "v1")
    results = service.users().messages().list(
        userId="me", q=args.query, maxResults=args.max
    ).execute()
    messages = results.get("messages", [])
    if not messages:
        print("No messages found.")
        return

    output = []
    for msg_meta in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_meta["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
        ).execute()
        headers = _headers_dict(msg)
        output.append({
            "id": msg["id"],
            "threadId": msg["threadId"],
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "labels": msg.get("labelIds", []),
        })
    print(json.dumps(output, indent=2, ensure_ascii=False))

def gmail_get(args):
    if _gws_binary():
        msg = _run_gws(
            ["gmail", "users", "messages", "get"],
            params={"userId": "me", "id": args.message_id, "format": "full"},
        )
        headers = _headers_dict(msg)
        result = {
            "id": msg["id"],
            "threadId": msg["threadId"],
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "labels": msg.get("labelIds", []),
            "body": _extract_message_body(msg),
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    service = build_service("gmail", "v1")
    msg = service.users().messages().get(
        userId="me", id=args.message_id, format="full"
    ).execute()
    headers = _headers_dict(msg)
    result = {
        "id": msg["id"],
        "threadId": msg["threadId"],
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "labels": msg.get("labelIds", []),
        "body": _extract_message_body(msg),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))

def gmail_send(args):
    if _gws_binary():
        message = MIMEText(args.body, "html" if args.html else "plain")
        message["to"] = args.to
        message["subject"] = args.subject
        if args.cc:
            message["cc"] = args.cc
        if args.from_header:
            message["from"] = args.from_header

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {"raw": raw}
        if args.thread_id:
            body["threadId"] = args.thread_id

        result = _run_gws(
            ["gmail", "users", "messages", "send"],
            params={"userId": "me"},
            body=body,
        )
        print(json.dumps({"status": "sent", "id": result["id"], "threadId": result.get("threadId", "")}, indent=2))
        return

    service = build_service("gmail", "v1")
    message = MIMEText(args.body, "html" if args.html else "plain")
    message["to"] = args.to
    message["subject"] = args.subject
    if args.cc:
        message["cc"] = args.cc
    if args.from_header:
        message["from"] = args.from_header

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw}
    if args.thread_id:
        body["threadId"] = args.thread_id

    result = service.users().messages().send(userId="me", body=body).execute()
    print(json.dumps({"status": "sent", "id": result["id"], "threadId": result.get("threadId", "")}, indent=2))

def gmail_reply(args):
    if _gws_binary():
        original = _run_gws(
            ["gmail", "users", "messages", "get"],
            params={
                "userId": "me",
                "id": args.message_id,
                "format": "metadata",
                "metadataHeaders": ["From", "Subject", "Message-ID"],
            },
        )
        headers = _headers_dict(original)

        subject = headers.get("Subject", "")
        if not subject.startswith("Re:"):
            subject = f"Re: {subject}"

        message = MIMEText(args.body)
        message["to"] = headers.get("From", "")
        message["subject"] = subject
        if args.from_header:
            message["from"] = args.from_header
        if headers.get("Message-ID"):
            message["In-Reply-To"] = headers["Message-ID"]
            message["References"] = headers["Message-ID"]

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = _run_gws(
            ["gmail", "users", "messages", "send"],
            params={"userId": "me"},
            body={"raw": raw, "threadId": original["threadId"]},
        )
        print(json.dumps({"status": "sent", "id": result["id"], "threadId": result.get("threadId", "")}, indent=2))
        return

    service = build_service("gmail", "v1")
    original = service.users().messages().get(
        userId="me", id=args.message_id, format="metadata",
        metadataHeaders=["From", "Subject", "Message-ID"],
    ).execute()
    headers = _headers_dict(original)

    subject = headers.get("Subject", "")
    if not subject.startswith("Re:"):
        subject = f"Re: {subject}"

    message = MIMEText(args.body)
    message["to"] = headers.get("From", "")
    message["subject"] = subject
    if args.from_header:
        message["from"] = args.from_header
    if headers.get("Message-ID"):
        message["In-Reply-To"] = headers["Message-ID"]
        message["References"] = headers["Message-ID"]

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw, "threadId": original["threadId"]}

    result = service.users().messages().send(userId="me", body=body).execute()
    print(json.dumps({"status": "sent", "id": result["id"], "threadId": result.get("threadId", "")}, indent=2))

def gmail_labels(args):
    if _gws_binary():
        results = _run_gws(["gmail", "users", "labels", "list"], params={"userId": "me"})
        labels = [{"id": l["id"], "name": l["name"], "type": l.get("type", "")} for l in results.get("labels", [])]
        print(json.dumps(labels, indent=2))
        return

    service = build_service("gmail", "v1")
    results = service.users().labels().list(userId="me").execute()
    labels = [{"id": l["id"], "name": l["name"], "type": l.get("type", "")} for l in results.get("labels", [])]
    print(json.dumps(labels, indent=2))

def gmail_modify(args):
    body = {}
    if args.add_labels:
        body["addLabelIds"] = args.add_labels.split(",")
    if args.remove_labels:
        body["removeLabelIds"] = args.remove_labels.split(",")

    if _gws_binary():
        result = _run_gws(
            ["gmail", "users", "messages", "modify"],
            params={"userId": "me", "id": args.message_id},
            body=body,
        )
        print(json.dumps({"id": result["id"], "labels": result.get("labelIds", [])}, indent=2))
        return

    service = build_service("gmail", "v1")
    result = service.users().messages().modify(userId="me", id=args.message_id, body=body).execute()
    print(json.dumps({"id": result["id"], "labels": result.get("labelIds", [])}, indent=2))

# =========================================================================
# Calendar
# =========================================================================

def calendar_list(args):
    now = datetime.now(timezone.utc)
    time_min = _datetime_with_timezone(args.start or now.isoformat())
    time_max = _datetime_with_timezone(args.end or (now + timedelta(days=7)).isoformat())

    if _gws_binary():
        results = _run_gws(
            ["calendar", "events", "list"],
            params={
                "calendarId": args.calendar,
                "timeMin": time_min,
                "timeMax": time_max,
                "maxResults": args.max,
                "singleEvents": True,
                "orderBy": "startTime",
            },
        )
        events = []
        for e in results.get("items", []):
            events.append({
                "id": e["id"],
                "summary": e.get("summary", "(no title)"),
                "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "")),
                "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date", "")),
                "location": e.get("location", ""),
                "description": e.get("description", ""),
                "status": e.get("status", ""),
                "htmlLink": e.get("htmlLink", ""),
            })
        print(json.dumps(events, indent=2, ensure_ascii=False))
        return

    service = build_service("calendar", "v3")
    results = service.events().list(
        calendarId=args.calendar, timeMin=time_min, timeMax=time_max,
        maxResults=args.max, singleEvents=True, orderBy="startTime",
    ).execute()

    events = []
    for e in results.get("items", []):
        events.append({
            "id": e["id"],
            "summary": e.get("summary", "(no title)"),
            "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "")),
            "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date", "")),
            "location": e.get("location", ""),
            "description": e.get("description", ""),
            "status": e.get("status", ""),
            "htmlLink": e.get("htmlLink", ""),
        })
    print(json.dumps(events, indent=2, ensure_ascii=False))

def calendar_create(args):
    start_dt = _datetime_with_timezone(args.start)
    end_dt = _datetime_with_timezone(args.end)

    event_body = {
        "summary": args.summary,
        "start": {"dateTime": start_dt},
        "end": {"dateTime": end_dt},
    }
    if args.location:
        event_body["location"] = args.location
    if args.description:
        event_body["description"] = args.description
    if args.attendees:
        event_body["attendees"] = [{"email": e.strip()} for e in args.attendees.split(",")]

    if _gws_binary():
        result = _run_gws(
            ["calendar", "events", "insert"],
            params={"calendarId": args.calendar},
            body=event_body,
        )
        print(json.dumps({"id": result.get("id"), "htmlLink": result.get("htmlLink", "")}, indent=2))
        return

    service = build_service("calendar", "v3")
    result = service.events().insert(calendarId=args.calendar, body=event_body).execute()
    print(json.dumps({"id": result.get("id"), "htmlLink": result.get("htmlLink", "")}, indent=2))

def calendar_delete(args):
    if _gws_binary():
        _run_gws(
            ["calendar", "events", "delete"],
            params={"calendarId": args.calendar, "eventId": args.event_id},
        )
        print(json.dumps({"deleted": True}))
        return

    service = build_service("calendar", "v3")
    service.events().delete(calendarId=args.calendar, eventId=args.event_id).execute()
    print(json.dumps({"deleted": True}))

# =========================================================================
# Drive
# =========================================================================

def drive_search(args):
    if _gws_binary():
        results = _run_gws(
            ["drive", "files", "list"],
            params={"q": args.query, "pageSize": args.max},
        )
        files = results.get("files", [])
        output = [{"id": f["id"], "name": f.get("name", ""), "mimeType": f.get("mimeType", "")} for f in files]
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    service = build_service("drive", "v3")
    results = service.files().list(
        q=args.query,
        pageSize=args.max,
        fields="files(id, name, mimeType)",
    ).execute()
    files = results.get("files", [])
    output = [{"id": f["id"], "name": f.get("name", ""), "mimeType": f.get("mimeType", "")} for f in files]
    print(json.dumps(output, indent=2, ensure_ascii=False))

# =========================================================================
# Contacts
# =========================================================================

def contacts_list(args):
    if _gws_binary():
        results = _run_gws(
            ["people", "connections", "list"],
            params={"resourceName": "people/me", "pageSize": args.max},
        )
        connections = results.get("connections", [])
        output = []
        for person in connections:
            names = person.get("names", [])
            emails = person.get("emailAddresses", [])
            output.append({
                "id": person.get("resourceName", ""),
                "name": names[0].get("displayName", "") if names else "",
                "email": emails[0].get("value", "") if emails else "",
            })
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    from googleapiclient.discovery import build as build_contacts
    creds = get_credentials()
    service = build_contacts("people", "v1", credentials=creds)
    results = service.people().connections().list(
        resourceName="people/me",
        pageSize=args.max,
        personFields="names,emailAddresses",
    ).execute()
    connections = results.get("connections", [])
    output = []
    for person in connections:
        names = person.get("names", [])
        emails = person.get("emailAddresses", [])
        output.append({
            "id": person.get("resourceName", ""),
            "name": names[0].get("displayName", "") if names else "",
            "email": emails[0].get("value", "") if emails else "",
        })
    print(json.dumps(output, indent=2, ensure_ascii=False))

# =========================================================================
# Sheets
# =========================================================================

def sheets_get(args):
    service = build_service("sheets", "v4")
    result = service.spreadsheets().values().get(
        spreadsheetId=args.sheet_id,
        range=args.range,
    ).execute()
    values = result.get("values", [])
    print(json.dumps(values, indent=2, ensure_ascii=False))

def sheets_update(args):
    service = build_service("sheets", "v4")
    body = {"values": args.values}
    result = service.spreadsheets().values().update(
        spreadsheetId=args.sheet_id,
        range=args.range,
        valueInputOption="RAW",
        body=body,
    ).execute()
    print(json.dumps({"updatedCells": result.get("updatedCells")}, indent=2))

def sheets_append(args):
    service = build_service("sheets", "v4")
    body = {"values": args.values}
    result = service.spreadsheets().values().append(
        spreadsheetId=args.sheet_id,
        range=args.range,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()
    print(json.dumps({"updatedCells": result.get("updatedCells")}, indent=2))

# =========================================================================
# Docs
# =========================================================================

def docs_get(args):
    service = build_service("docs", "v1")
    doc = service.documents().get(documentId=args.doc_id).execute()
    text = _extract_doc_text(doc)
    print(json.dumps({"docId": args.doc_id, "text": text}, indent=2, ensure_ascii=False))

# =========================================================================
# Main
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description="Google Workspace API CLI")
    parser.add_argument("--account", default="svaaugust", help="Account identifier (ogodev or svaaugust)")
    sub = parser.add_subparsers(dest="command")

    # Gmail
    gmail = sub.add_parser("gmail", help="Gmail operations")
    gmail_sub = gmail.add_subparsers(dest="gmail_cmd")

    gs = gmail_sub.add_parser("search", help="Search messages")
    gs.add_argument("query", help="Gmail query")
    gs.add_argument("--max", type=int, default=10, help="Max results")
    gs.set_defaults(func=lambda a: gmail_search(a))

    gg = gmail_sub.add_parser("get", help="Get message")
    gg.add_argument("message_id", help="Message ID")
    gg.set_defaults(func=lambda a: gmail_get(a))

    gsend = gmail_sub.add_parser("send", help="Send message")
    gsend.add_argument("--to", required=True, help="Recipient")
    gsend.add_argument("--subject", required=True, help="Subject")
    gsend.add_argument("--body", required=True, help="Body text")
    gsend.add_argument("--html", action="store_true", help="Send as HTML")
    gsend.add_argument("--cc", help="CC recipients")
    gsend.add_argument("--from-header", dest="from_header", help="From header")
    gsend.add_argument("--thread-id", dest="thread_id", help="Thread ID")
    gsend.set_defaults(func=lambda a: gmail_send(a))

    gr = gmail_sub.add_parser("reply", help="Reply to message")
    gr.add_argument("message_id", help="Message ID to reply to")
    gr.add_argument("--body", required=True, help="Reply body")
    gr.add_argument("--from-header", dest="from_header", help="From header")
    gr.set_defaults(func=lambda a: gmail_reply(a))

    gl = gmail_sub.add_parser("labels", help="List labels")
    gl.set_defaults(func=lambda a: gmail_labels(a))

    gm = gmail_sub.add_parser("modify", help="Modify message labels")
    gm.add_argument("message_id", help="Message ID")
    gm.add_argument("--add-labels", help="Comma-separated label IDs to add")
    gm.add_argument("--remove-labels", help="Comma-separated label IDs to remove")
    gm.set_defaults(func=lambda a: gmail_modify(a))

    # Calendar
    cal = sub.add_parser("calendar", help="Calendar operations")
    cal_sub = cal.add_subparsers(dest="cal_cmd")

    cl = cal_sub.add_parser("list", help="List events")
    cl.add_argument("--start", help="Start datetime (ISO 8601)")
    cl.add_argument("--end", help="End datetime (ISO 8601)")
    cl.add_argument("--calendar", default="primary", help="Calendar ID")
    cl.add_argument("--max", type=int, default=100, help="Max results")
    cl.set_defaults(func=lambda a: calendar_list(a))

    cc = cal_sub.add_parser("create", help="Create event")
    cc.add_argument("--summary", required=True, help="Event title")
    cc.add_argument("--start", required=True, help="Start datetime (ISO 8601)")
    cc.add_argument("--end", required=True, help="End datetime (ISO 8601)")
    cc.add_argument("--location", help="Location")
    cc.add_argument("--description", help="Description")
    cc.add_argument("--attendees", help="Comma-separated emails")
    cc.add_argument("--calendar", default="primary", help="Calendar ID")
    cc.set_defaults(func=lambda a: calendar_create(a))

    cdel = cal_sub.add_parser("delete", help="Delete event")
    cdel.add_argument("event_id", help="Event ID")
    cdel.add_argument("--calendar", default="primary", help="Calendar ID")
    cdel.set_defaults(func=lambda a: calendar_delete(a))

    # Drive
    drv = sub.add_parser("drive", help="Drive operations")
    drv_sub = drv.add_subparsers(dest="drv_cmd")

    ds = drv_sub.add_parser("search", help="Search files")
    ds.add_argument("query", help="Search query")
    ds.add_argument("--max", type=int, default=10, help="Max results")
    ds.set_defaults(func=lambda a: drive_search(a))

    # Contacts
    cnt = sub.add_parser("contacts", help="Contacts operations")
    cnt_sub = cnt.add_subparsers(dest="cnt_cmd")

    clst = cnt_sub.add_parser("list", help="List contacts")
    clst.add_argument("--max", type=int, default=20, help="Max results")
    clst.set_defaults(func=lambda a: contacts_list(a))

    # Sheets
    sh = sub.add_parser("sheets", help="Sheets operations")
    sh_sub = sh.add_subparsers(dest="sh_cmd")

    shg = sh_sub.add_parser("get", help="Read range")
    shg.add_argument("sheet_id", help="Spreadsheet ID")
    shg.add_argument("range", help="Range (e.g. Sheet1!A1:D10)")
    shg.set_defaults(func=lambda a: sheets_get(a))

    shu = sh_sub.add_parser("update", help="Update range")
    shu.add_argument("sheet_id", help="Spreadsheet ID")
    shu.add_argument("range", help="Range")
    shu.add_argument("--values", required=True, help="JSON array of arrays")
    shu.set_defaults(func=lambda a: sheets_update(a))

    sha = sh_sub.add_parser("append", help="Append rows")
    sha.add_argument("sheet_id", help="Spreadsheet ID")
    sha.add_argument("range", help="Range (e.g. Sheet1!A:C)")
    sha.add_argument("--values", required=True, help="JSON array of arrays")
    sha.set_defaults(func=lambda a: sheets_append(a))

    # Docs
    dc = sub.add_parser("docs", help="Docs operations")
    dc_sub = dc.add_subparsers(dest="dc_cmd")

    dg = dc_sub.add_parser("get", help="Get document text")
    dg.add_argument("doc_id", help="Document ID")
    dg.set_defaults(func=lambda a: docs_get(a))

    args = parser.parse_args()
    global ACCOUNT
    ACCOUNT = args.account if args.account else "svaaugust"

    if hasattr(args, 'func') and args.func:
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
