"""Пересчёт category для всех строк по обновлённым правилам (без пересоздания БД)."""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ledger_import import to_cat
from ledger_rules import apply

c = sqlite3.connect(str(Path.home() / ".hermes" / "ledger" / "ledger.db"))
n = 0
for row in c.execute("SELECT id, sber_cat, payee, category, source FROM transactions").fetchall():
    if row[4] == "manual":
        continue  # ручные статьи — только со слов Василия, не трогать
    new = to_cat(row[1], row[2])
    if new != row[3]:
        c.execute("UPDATE transactions SET category=? WHERE id=?", (new, row[0]))
        n += 1
n += apply(c)  # пользовательские правила поверх (Яндекс=Транспорт, Вкусно=Кафе, ...)
c.commit()
print(f"обновлено категорий: {n}")
for cat, s in c.execute("""SELECT category, ROUND(SUM(-amount)) FROM transactions
    WHERE amount<0 GROUP BY category ORDER BY 2 DESC LIMIT 14"""):
    print(f"  {cat:24} {s:>11,.0f}")
