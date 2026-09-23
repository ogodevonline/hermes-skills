"""Ручной ввод операций в ledger (source='manual').

Hermes вызывает это из чата: «кофе 250» -> ledger_add.py 250 Кофе "кофе CH77".
При следующем импорте выписки запись склеивается с банковской (reconcile в
ledger_import.py) — дубля не будет. Наличные (--cash) не сверяются, живут сами.
"""
import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"
MSK = ZoneInfo("Europe/Moscow")

def main():
    p = argparse.ArgumentParser(description="Добавить операцию вручную")
    p.add_argument("amount", type=float, help="сумма в рублях (положительная)")
    p.add_argument("category", help="категория: Продукты, Кафе, Транспорт...")
    p.add_argument("payee", nargs="?", default="", help="что/где")
    p.add_argument("-d", "--date", default=datetime.now(MSK).date().isoformat())
    p.add_argument("--income", action="store_true", help="доход, не расход")
    p.add_argument("--cash", action="store_true", help="наличные (не с карты)")
    a = p.parse_args()

    amount = abs(a.amount) * (1 if a.income else -1)
    account = "CASH" if a.cash else ""
    c = sqlite3.connect(str(DB))
    cur = c.execute(
        """INSERT INTO transactions (date, month, account, card, sber_cat,
             category, amount, balance_after, payee, source)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (a.date, a.date[:7], account, "наличные" if a.cash else "",
         "Ручной ввод", a.category, amount, None, a.payee, "manual"))
    c.commit()
    c.close()
    print(f"✓ [{cur.lastrowid}] {a.date} {amount:+,.0f} {a.category} {a.payee}")
    import ledger_balances
    ledger_balances.main()  # пересечь balance_of для колонок «на счёте»

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main()
