"""Графики ledger -> PNG в Telegram."""
import sqlite3
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"
OUT = Path("/tmp/ledger_charts.png")
c = sqlite3.connect(str(DB))

TRANSFERS = ("Переводы", "Переводы между своими", "QR–коду СБП")
rows = c.execute("""SELECT category, ROUND(SUM(-amount)) s FROM transactions
    WHERE amount<0 AND date>='2026-07-01'
      AND category NOT IN ('Переводы','Внесение наличных','Прочие операции')
    GROUP BY category HAVING s>500 ORDER BY s DESC LIMIT 9""").fetchall()

# по дням (расходы без переводов)
days = defaultdict(float)
for d, a in c.execute("""SELECT date, amount FROM transactions WHERE amount<0
    AND category NOT IN ('Переводы','Внесение наличных')"""):
    days[d] += -a
import datetime as dt
start, end = dt.date(2026, 7, 1), dt.date(2026, 9, 21)
xs, ys, cum = [], [], 0
cur = start
weekly = defaultdict(float)
while cur <= end:
    v = days.get(cur.isoformat(), 0)
    cum += v
    weekly[cur - dt.timedelta(days=cur.weekday())] += v
    if cur.day % 2 == 1:
        xs.append(cur); ys.append(v)
    cur += dt.timedelta(days=1)

fig, axes = plt.subplots(2, 2, figsize=(13, 9))
fig.suptitle("Личный бюджет — Сбер, июль–сентябрь 2026 (без внутренних переводов)", fontsize=13)

ax = axes[0][0]
cats, vals = [r[0] for r in rows], [r[1] for r in rows]
colors = plt.cm.Set2([i / len(cats) for i in range(len(cats))])
ax.pie(vals, labels=cats, autopct=lambda p: f"{p:.0f}%" if p > 3 else "",
       colors=colors, textprops={"fontsize": 8})
ax.set_title("Куда ушло за 3 мес")

ax = axes[0][1]
months = c.execute("""SELECT month, -SUM(amount) FROM transactions WHERE amount<0
    AND category NOT IN ('Переводы','Внесение наличных')
    GROUP BY month ORDER BY month""").fetchall()
ax.bar([m[0] for m in months], [m[1] / 1000 for m in months], color="#c94f4f")
for i, m in enumerate(months):
    ax.text(i, m[1] / 1000 + 400, f"{m[1]/1000:.0f}к", ha="center", fontsize=9)
ax.set_title("Расходы по месяцам, тыс. ₽")

ax = axes[1][0]
ax.plot(xs, ys, color="#4f7dc9", linewidth=0.8, alpha=0.6)
ax.plot(xs, [cum * 0 for _ in xs], alpha=0)
run = 0; rx, ry = [], []
cur = start
while cur <= end:
    run += days.get(cur.isoformat(), 0)
    if cur.day % 2 == 1:
        rx.append(cur); ry.append(run)
    cur += dt.timedelta(days=1)
ax.plot(rx, ry, color="#2a9d8f", linewidth=1.6)
ax.set_title("Накопительный расход с 1 июля")
ax.grid(alpha=0.3)

ax = axes[1][1]
wk = sorted(weekly.items())
ax.bar([k.isoformat()[5:] for k, _ in wk], [v / 1000 for _, v in wk], color="#e9c46a")
ax.set_title("Недельные расходы, тыс. ₽")
ax.tick_params(axis="x", rotation=45, labelsize=7)

plt.tight_layout()
plt.savefig(OUT, dpi=110)
total = c.execute("""SELECT ROUND(SUM(-amount)) FROM transactions WHERE amount<0
    AND category NOT IN ('Переводы','Внесение наличных')""").fetchone()[0]
print(OUT)
print(f"итого 3мес расход (без переводов): {total:,.0f}")
