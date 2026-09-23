"""Миграция 2: наличные траты не-зарплата, баланс карманных наличных."""
import sqlite3
from pathlib import Path

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"
c = sqlite3.connect(str(DB))
c.executescript("""
UPDATE transactions SET category='Помощь семье' WHERE id=262;
-- из конвертов за период: 575 150 внесено/потрачено налом; остаток в кармане:
INSERT OR REPLACE INTO accounts (account, card, balance, debt, credit_limit, asof, source)
  VALUES ('CASH','Наличные (карманные)', 41750, NULL, NULL, '2026-09-21', 'manual');
""")
c.commit()
r = c.execute("SELECT balance FROM accounts WHERE account='CASH'").fetchone()
print("cash на руках:", r[0])
