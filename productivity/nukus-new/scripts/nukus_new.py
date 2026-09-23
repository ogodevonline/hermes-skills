#!/usr/bin/env python3
"""Новые объявления домов в Нукусе из nukus.db."""
import sqlite3, os
from datetime import datetime, timedelta

DB = "/home/hermes/nukus-houses/nukus.db"

def main():
    if not os.path.exists(DB):
        print("❌ База nukus.db не найдена")
        return

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    cur.execute("""
        SELECT url, title, price_sum, first_seen
        FROM listings
        WHERE status = 'active' AND first_seen >= ?
        ORDER BY first_seen DESC
    """, (week_ago,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("🏠 Новых домов в Нукусе за 7 дней нет")
        return

    print("🏠 **Новые дома Нукус (7 дней):**")
    for i, r in enumerate(rows, 1):
        title = (r['title'] or '')[:50]
        price = f"{r['price_sum']/1e6:.0f} млн"
        print(f"{i}. {title} — {price}")

if __name__ == '__main__':
    main()