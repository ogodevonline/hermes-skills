"""Миграция 5b: добить 'Прочее' аптекой и Дикси (21.09)."""
import sqlite3
from pathlib import Path
import ledger_balances

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"
c = sqlite3.connect(str(DB))
print(c.execute("UPDATE transactions SET category='Здоровье' WHERE payee LIKE '%Аптечная сеть%' AND category='Прочее'").rowcount, "-> Здоровье")
print(c.execute("UPDATE transactions SET category='Продукты' WHERE payee LIKE '%Дикси%' AND category='Прочее'").rowcount, "-> Продукты")
c.commit()
print(c.execute("SELECT date,payee,amount FROM transactions WHERE category='Прочее' AND amount<0").fetchall())
c.close()
ledger_balances.main()
