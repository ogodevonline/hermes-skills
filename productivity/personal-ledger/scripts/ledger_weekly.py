"""Еженедельная выжимка для finance-крона: ledger_weekly.py -> stdout (маркдаун-данные).

Скрипт собирает ФАКТЫ; гипотезы/советы формулирует агент. Пишет в vault сам — не здесь.
"""
import datetime
import sqlite3
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from zoneinfo import ZoneInfo

MSK = ZoneInfo("Europe/Moscow")
now = datetime.datetime.now(MSK)
DB = Path.home() / ".hermes" / "ledger" / "ledger.db"
HERE = Path(__file__).parent

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
EXCL = {"Переводы", "Возврат"}
cur = con.execute("SELECT date,category,payee,amount FROM transactions")
cols = [d[0] for d in cur.description]
rows = [dict(zip(cols, r)) for r in cur]
exp = [r for r in rows if r["amount"] < 0 and r["category"] not in EXCL]
inc = [r for r in rows if r["amount"] > 0 and r["category"] not in EXCL
       and "Перевод от" not in (r["payee"] or "")]

# --- неделя (last 7 days ending today) ---
w0 = (now - datetime.timedelta(days=6)).date().isoformat()
t0 = now.date().isoformat()
w_exp = [r for r in exp if w0 <= r["date"] <= t0]
w_inc = [r for r in inc if w0 <= r["date"] <= t0]
tot_w = sum(-r["amount"] for r in w_exp)

print(f"# Данные на {t0} (МСК). Неделя: {w0}..{t0}")
print("\n## Неделя")
bycat = defaultdict(float)
for r in w_exp:
    bycat[r["category"]] += -r["amount"]
print(f"расход недели: {tot_w:,.0f} ₽ | доход (зарплата/внесения): {sum(r['amount'] for r in w_inc):,.0f} ₽")
for c, v in sorted(bycat.items(), key=lambda x: -x[1])[:8]:
    print(f"- {c}: {v:,.0f}")

# --- месяц: план/факт/темп ---
m0 = t0[:7]
dim = int(t0[8:10])
import calendar
D = calendar.monthrange(int(m0[:4]), int(m0[5:7]))[1]
m_exp = sum(-r["amount"] for r in exp if r["date"].startswith(m0))
m_inc = sum(r["amount"] for r in inc if r["date"].startswith(m0))
pl = dict(con.execute("SELECT category,amount FROM plans WHERE kind='expense'"))
byt = sum(-r["amount"] for r in exp if r["date"].startswith(m0)
          and r["category"] in ("Продукты", "Кафе и рестораны", "Прочее"))
print("\n## Текущий месяц")
print(f"потрачено {m_exp:,.0f} за {dim} дн (~{m_exp/dim:,.0f}/дн) | прогноз {m_exp/dim*D:,.0f} vs план ~{sum(pl.values()):,.0f}")
print(f"доход месяца: {m_inc:,.0f} | сбережение: {(m_inc-m_exp)/max(m_inc,1)*100:.0f}%")
print(f"быт {byt:,.0f} vs лимит {pl.get('Быт',0):,.0f}")
for g in con.execute("SELECT name,target,deadline FROM goals"):
    print(f"цель {g[0]}: {g[1]:,.0f} к {g[2]}")

# --- нетто/балансы ---
acc = list(con.execute("SELECT account,card,balance,debt FROM accounts"))
deb = sum(a[2] for a in acc if a[2] is not None and a[3] is None and a[0] != "CASH")
cash = next((a[2] for a in acc if a[0] == "CASH"), 0)
debt = sum(a[3] or 0 for a in acc)
print(f"\n## Счета\nкарты дебет: {deb:,.0f} | нал: {cash:,.0f} | доступно: {deb+cash:,.0f} | долг кредитки: {debt:,.0f} | нетто: {deb+cash-debt:,.0f}")

# --- new transactions since last digest marker ---
mark = Path.home() / ".hermes/ledger/.weekly_last"
last = mark.read_text().strip() if mark.exists() else w0
nw = [r for r in rows if r["date"] > last and r["date"] <= t0]
print(f"\n## Операций с прошлой сводки (с {last}): {len(nw)}")
susp = [r for r in nw if r["amount"] < -3000 or (r["category"] == "Прочее" and r["amount"] < 0)
        or "COMMISSION" in (r["payee"] or "").upper()]
for r in sorted(susp, key=lambda r: r["amount"])[:12]:
    print(f"- {r['date']} {r['amount']:,.0f} {r['category']} {(r['payee'] or '')[:36]}")
mark.write_text(t0)
print("\n(полный недельный разбор категорий: запуск `python3 ~/.hermes/venvs/ledger/bin/python3 ~/.hermes/skills/productivity/personal-ledger/scripts/ledger_analyze.py`)")
