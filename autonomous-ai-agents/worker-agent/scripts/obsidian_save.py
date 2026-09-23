#!/usr/bin/env python3
"""Сохранить результат агента в Obsidian и запушить.

Usage:
    python3 obsidian_save.py <AgentName> "содержание"

Example:
    python3 obsidian_save.py Researcher "Price Report: iPhone от 72 986 ₽..."
    python3 obsidian_save.py Coder "feat: added caching layer"

Creates: agents-data/<AgentName>/YYYY-MM-DD-<topic>.md
Then: git add + git commit + git push
"""
import os, sys, subprocess, re
from datetime import date

VAULT = os.path.expanduser("~/hermes-vault")

def sanitize(text: str) -> str:
    s = text.strip().split("\n")[0][:60]
    s = re.sub(r'[^\w\s-]', '', s)
    return re.sub(r'[-\s]+', '-', s).strip('-').lower()[:50] or 'untitled'

agent = sys.argv[1]
content = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else sys.stdin.read()
today = date.today().isoformat()
topic = sanitize(content)
rel = f"agents-data/{agent}/{today}-{topic}.md"
abs_path = os.path.join(VAULT, rel)

os.makedirs(os.path.dirname(abs_path), exist_ok=True)
with open(abs_path, "w") as f:
    f.write(content)

for cmd in [
    ["git", "add", "-A"],
    ["git", "commit", "-m", f"{agent}: {topic[:40]}"],
    ["git", "push"],
]:
    try:
        subprocess.run(cmd, cwd=VAULT, capture_output=True, timeout=30)
    except Exception:
        pass

print(f"Saved: {rel}")
