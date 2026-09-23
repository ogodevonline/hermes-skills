#!/usr/bin/env python3
"""List all monitored accounts with status."""
import sqlite3
from pathlib import Path

DB = Path.home() / ".insta_flat_parser" / "state.db"
conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT username, is_active, last_error FROM accounts ORDER BY username").fetchall()
if not rows:
    print("No accounts in database")
else:
    print(f"Total: {len(rows)}")
    for r in rows:
        err = r["last_error"] or ""
        icon = "🟢" if r["is_active"] else "🔴"
        extra = f" — {err[:100]}" if err else ""
        print(f"{icon} @{r['username']}{extra}")
