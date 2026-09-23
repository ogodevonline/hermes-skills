#!/usr/bin/env python3
"""Generate interactive HTML report for Nukus houses from DB (no HTTP)."""
import sqlite3, os, sys
from datetime import date, datetime
from nukus_html_builder import build_html

DB = "/home/hermes/nukus-houses/nukus.db"
OUT = "/home/hermes/.hermes/cache/documents/nukus_report.html"

# Ensure we can import the builder (same directory)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
    SELECT l.property_type, l.title, l.price_sum, l.price_rub, l.rooms,
           l.area_sqm, l.district, l.first_seen, l.url,
           l.wall_material, l.gas, l.water, l.description, l.phone,
           s.name as source
    FROM listings l JOIN sources s ON l.source_id = s.id
    WHERE l.status = 'active' AND s.name = 'olx'
    ORDER BY l.first_seen DESC
""")
rows = [dict(r) for r in cur.fetchall()]
total = len(rows)

now = datetime.now()
for r in rows:
    r["prop_type"] = "house" if r.get("property_type") in ("house", "houses") else r.get("property_type", "")
    if r.get("first_seen"):
        try:
            fd = datetime.strptime(r["first_seen"][:10], "%Y-%m-%d")
            r["days_online"] = (now - fd).days
        except Exception:
            r["days_online"] = 0
    else:
        r["days_online"] = 0

prices = [r["price_sum"] for r in rows if r["price_sum"]]
avg_price = sum(prices) / len(prices) / 1e6 if prices else 0
areas = [r["area_sqm"] for r in rows if r["area_sqm"]]
avg_area = sum(areas) / len(areas) if areas else 0
price_dist = {"-200": 0, "200-250": 0, "250-300": 0, "300+": 0}
for p in prices:
    if p < 200e6:
        price_dist["-200"] += 1
    elif p < 250e6:
        price_dist["200-250"] += 1
    elif p < 300e6:
        price_dist["250-300"] += 1
    else:
        price_dist["300+"] += 1

all_rooms = sorted(set(r["rooms"] for r in rows if r["rooms"] and r["rooms"] > 0))
all_dist = sorted(set(r["district"] for r in rows if r["district"]))
all_types = sorted(set(r["prop_type"] for r in rows if r["prop_type"]))
with_gas = sum(1 for r in rows if r.get("gas"))
with_phone = sum(1 for r in rows if r.get("phone"))
today_str = date.today().isoformat()

html = build_html(total, avg_price, avg_area, price_dist, with_gas, with_phone,
                  rows, all_rooms, all_dist, all_types, today_str)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"OK|{OUT}|{os.path.getsize(OUT)} bytes|{total} listings")
