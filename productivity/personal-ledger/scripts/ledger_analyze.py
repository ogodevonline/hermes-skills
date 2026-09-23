"""Аналитика для гипотез/советов: тренды, группы, будни/вых, чек, повторы, выбросы.

ВСЕ срезы динамические: месяцы берутся из данных, незавершённый текущий месяц
(МСК) считается до сегодняшнего дня. НИКОГДА не хардкодь месяцы/даты —
прошлый опыт: DAYS={'2026-07':31,...} ослепил сценарий на следующий месяц.
Категории должны быть ЧИСТЫМИ (после ledger_rules.apply) — иначе гипотезы на мусоре.
"""
import calendar
import datetime
import sqlite3
import statistics as st
from collections import defaultdict
from pathlib import Path

MSK = datetime.timezone(datetime.timedelta(hours=3))
TODAY = datetime.datetime.now(MSK).date()
CUR_M = TODAY.isoformat()[:7]

db = sqlite3.connect(f"file:{Path.home()}/.hermes/ledger/ledger.db?mode=ro", uri=True)
EXCL = {"Переводы", "Возврат"}
OBLIG = ["Нейросети", "Связь", "Подписки", "Транспорт", "Зал/спорт", "Здоровье",
         "ЖКХ", "Хостинг/техника"]
BYT = ["Продукты", "Кафе и рестораны", "Прочее"]
cur = db.execute("SELECT date,category,payee,amount FROM transactions")
cols = [d[0] for d in cur.description]
rows = [dict(zip(cols, r)) for r in cur]
exp = [r for r in rows if r["amount"] < 0 and r["category"] not in EXCL]
inc = [r for r in rows if r["amount"] > 0 and r["category"] not in EXCL
       and "Перевод от" not in (r["payee"] or "")]
months = sorted({r["date"][:7] for r in rows})


def ndays(m):
    """Дней в срезе: полный месяц или до сегодня для текущего (МСК)."""
    full = calendar.monthrange(int(m[:4]), int(m[5:7]))[1]
    return min(TODAY.day, full) if m == CUR_M else full


def s(rs, m=None, cats=None):
    return sum(abs(r["amount"]) for r in rs
               if (m is None or r["date"].startswith(m))
               and (cats is None or r["category"] in cats))


total_days = sum(ndays(m) for m in months)

print(f"=== расход и доход по месяцам ({len(months)} мес, {total_days} дн) ===")
for m in months:
    d = ndays(m)
    mark = " *частично" if d < calendar.monthrange(int(m[:4]), int(m[5:7]))[1] else ""
    sav = 100 * (1 - s(exp, m) / max(s(inc, m), 1))
    print(f"{m}{mark}: расход {s(exp,m):>9,.0f} ({s(exp,m)/d:>6,.0f}/д)  "
          f"доход {s(inc,m):>9,.0f}  сбережение {sav:.0f}%")

print("\n=== группы: обязательное / быт / остальное по месяцам ===")
other = sorted({r["category"] for r in exp} - set(OBLIG) - set(BYT))
for m in months:
    print(f"{m}: обяз. {s(exp,m,OBLIG):>8,.0f} | быт {s(exp,m,BYT):>8,.0f} | "
          f"прочее {s(exp,m,other):>8,.0f}")

print("\n=== будни vs выходные (расход на день) ===")
tot = defaultdict(float)
nd = {"буд": 0, "вых": 0}
for r in exp:
    dt = datetime.date.fromisoformat(r["date"])
    tot["вых" if dt.weekday() >= 5 else "буд"] += -r["amount"]
for m in months:
    for day in range(1, ndays(m) + 1):
        k = "вых" if datetime.date(int(m[:4]), int(m[5:7]), day).weekday() >= 5 else "буд"
        nd[k] += 1
for k in ("буд", "вых"):
    v = tot[k] / nd[k] if nd[k] else 0
    print(f"{k}: {tot[k]:>9,.0f} за {nd[k]} дн = {v:>6,.0f}/день")

print("\n=== средний чек и ритм покупок ===")
for c in ("Продукты", "Кафе и рестораны"):
    v = sorted(-r["amount"] for r in exp if r["category"] == c)
    if not v:
        print(f"{c}: нет данных")
        continue
    days = len({r["date"] for r in exp if r["category"] == c})
    print(f"{c}: {len(v)} покупок, медиана {st.median(v):,.0f}, средн {st.mean(v):,.0f}, "
          f"макс {v[-1]:,.0f}; дней с покупкой {days} из {total_days} "
          f"(~каждый {total_days/max(days,1):.1f} дн)")

print("\n=== регулярные мелкие (та же сумма у того же продавца >=2) ===")
g = defaultdict(list)
for r in exp:
    g[(round(-r["amount"]), (r["payee"] or "")[:12])].append(r["date"])
for (amt, p), ds in sorted(g.items()):
    if len(ds) >= 2 and amt <= 3000:
        print(f"{amt:>7,.0f} x {len(ds)}  {p:14} {sorted(ds)}")

print("\n=== выбросы (> 3x медианы категории) ===")
bycat = defaultdict(list)
for r in exp:
    bycat[r["category"]].append(r)
for c, rs in bycat.items():
    v = sorted(-r["amount"] for r in rs)
    if len(v) < 4:
        continue
    med = st.median(v)
    for r in rs:
        if -r["amount"] > max(med * 3, 3000):
            print(f"{r['date']}  {-r['amount']:>9,.0f}  {c:14} {(r['payee'] or '')[:36]}")

print(f"\n=== неделя за неделей ({CUR_M}) ===")
wk = defaultdict(float)
for r in exp:
    if r["date"].startswith(CUR_M):
        dt = datetime.date.fromisoformat(r["date"])
        wk[dt.isocalendar().week] += -r["amount"]
for w, v in sorted(wk.items()):
    print(f"неделя {w}: {v:>8,.0f}")

print("\n=== транспорт: каршеринг/такси/самокаты/метро ===")
tr = [r for r in exp if r["category"] == "Транспорт"]
kind = defaultdict(float)
for r in tr:
    p = (r["payee"] or "").upper()
    k = ("каршеринг" if "DRIVE" in p else "такси" if "GO" in p or "TAXI" in p
         else "самокат" if "SCOOTER" in p or "WHOOSH" in p
         else "метро/ППК" if "PPK" in p or "NOAUTH" in p or p == "MOS" else "прочее")
    kind[k] += -r["amount"]
for k, v in sorted(kind.items(), key=lambda x: -x[1]):
    print(f"{k:12} {v:>8,.0f}")

print("\n=== наличные: учтены ли траты CASH? ===")
cash_n, cash_s = db.execute(
    "SELECT COUNT(*), COALESCE(ROUND(SUM(-amount)),0) FROM transactions "
    "WHERE account='CASH' AND amount<0").fetchone()
print(f"CASH-трат в базе: {cash_n} на {cash_s:,.0f} ₽ — если Василий платит налом "
      "чаще, это дыра учёта (спросить)")
