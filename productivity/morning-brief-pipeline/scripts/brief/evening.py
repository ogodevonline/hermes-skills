#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Вечерний бриф — подведение итогов дня."""
import sys, os
sys.path.insert(0, '/home/hermes/.hermes/scripts')
os.chdir('/home/hermes/.hermes/scripts/brief')

from brief import generate_brief
from hermes_tools import terminal

def evening_brief():
    # Основной бриф
    brief = generate_brief()

    import yaml
    from pathlib import Path
    tasks_path = Path.home() / ".hermes" / "tasks" / "tasks.yml"
    with open(tasks_path) as f:
        data = yaml.safe_load(f) or {}

    today = data.get("today", [])
    completed = sum(1 for t in today if "зал" in str(t).lower())

    print("=" * 60)
    print("🌅 УТРЕННИЙ БРИФ")
    print("=" * 60)
    print(brief)

    print("\n" + "─" * 60)
    print("📊 ИТОГИ ДНЯ")
    print("-" * 60)
    print(f"✅ Выполнено: {completed}")
    print(f"⏳ В работе:  {len(today) - completed}")

    tomorrow = data.get("tomorrow", [])
    if tomorrow:
        print("\n📅 ЗАВТРА:")
        for t in tomorrow:
            print(f"  • {t.get('name', '')}")

    print("\n" + "_" * 60)

if __name__ == "__main__":
    evening_brief()
