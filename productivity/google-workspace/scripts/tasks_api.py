#!/usr/bin/env python3
"""Google Tasks API CLI"""
import argparse
import json
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

import os
HERMES_HOME = Path(os.path.expanduser("~/.hermes"))
ACCOUNT = "svaaugust"  # default, override via --account

def get_token_path() -> Path:
    return HERMES_HOME / f"google_token_{ACCOUNT}.json"

def get_service():
    if not get_token_path().exists():
        print("Not authenticated. Run setup.py first.", file=sys.stderr)
        sys.exit(1)
    creds = Credentials.from_authorized_user_info(
        json.loads(get_token_path().read_text()),
        scopes=['https://www.googleapis.com/auth/tasks']
    )
    return build('tasks', 'v1', credentials=creds)

def cmd_lists(args):
    service = get_service()
    result = service.tasklists().list().execute()
    items = result.get('items', [])
    if not items:
        print("[]")
        return
    for item in items:
        print(json.dumps({
            "id": item.get("id"),
            "title": item.get("title"),
            "updated": item.get("updated")
        }, ensure_ascii=False))

def cmd_tasks(args):
    service = get_service()
    result = service.tasks().list(tasklist=args.list_id or "@default").execute()
    items = result.get('items', [])
    for item in items:
        print(json.dumps({
            "id": item.get("id"),
            "title": item.get("title"),
            "status": item.get("status"),
            "due": item.get("due"),
            "completed": item.get("completed")
        }, ensure_ascii=False))

def cmd_add(args):
    service = get_service()
    body = {"title": args.title}
    if args.notes:
        body["notes"] = args.notes
    if args.due:
        body["due"] = args.due
    result = service.tasks().insert(tasklist=args.list_id or "@default", body=body).execute()
    print(json.dumps({"id": result.get("id"), "title": result.get("title")}, ensure_ascii=False))

def cmd_complete(args):
    service = get_service()
    result = service.tasks().patch(
        tasklist=args.list_id or "@default",
        task=args.task_id,
        body={"status": "completed"}
    ).execute()
    print(json.dumps({"id": result.get("id"), "status": result.get("status")}, ensure_ascii=False))

def cmd_delete(args):
    service = get_service()
    service.tasks().delete(tasklist=args.list_id or "@default", task=args.task_id).execute()
    print(json.dumps({"deleted": True}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Tasks CLI")
    parser.add_argument("--account", default="svaaugust", help="Account identifier (ogodev or svaaugust)")
    sub = parser.add_subparsers()
    
    p = sub.add_parser("lists", help="List task lists")
    p.set_defaults(cmd=cmd_lists)
    
    p = sub.add_parser("tasks", help="List tasks in a list")
    p.add_argument("list_id", nargs="?", help="Task list ID (default: @default)")
    p.set_defaults(cmd=cmd_tasks)
    
    p = sub.add_parser("add", help="Add a task")
    p.add_argument("title", help="Task title")
    p.add_argument("--notes", help="Task notes")
    p.add_argument("--due", help="Due date (ISO 8601)")
    p.add_argument("--list-id", help="Task list ID")
    p.set_defaults(cmd=cmd_add)
    
    p = sub.add_parser("complete", help="Mark task as completed")
    p.add_argument("task_id", help="Task ID")
    p.add_argument("--list-id", help="Task list ID")
    p.set_defaults(cmd=cmd_complete)
    
    p = sub.add_parser("delete", help="Delete a task")
    p.add_argument("task_id", help="Task ID")
    p.add_argument("--list-id", help="Task list ID")
    p.set_defaults(cmd=cmd_delete)
    
    args = parser.parse_args()
    ACCOUNT = args.account if args.account else "svaaugust"
    
    if hasattr(args, 'cmd'):
        args.cmd(args)
    else:
        parser.print_help()
