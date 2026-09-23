#!/usr/bin/env python3
"""Reactivate all inactive accounts and clear their errors."""
import sqlite3
from pathlib import Path

DB = Path.home() / ".insta_flat_parser" / "state.db"
conn = sqlite3.connect(str(DB))

inactive = conn.execute("SELECT username FROM accounts WHERE is_active = 0").fetchall()
if not inactive:
    print("No inactive accounts to reactivate")
else:
    for (u,) in inactive:
        conn.execute("UPDATE accounts SET is_active = 1, last_error = NULL WHERE username = ?", (u,))
    conn.commit()
    print(f"✅ Reactivated {len(inactive)} accounts:")
    for (u,) in inactive:
        print(f"   @{u}")
