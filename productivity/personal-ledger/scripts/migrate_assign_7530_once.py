"""Миграция 6 (21.09): две ручные покупки 21.09 (CH77216 -474.68, VV_9246_KCO_4 -507)
сделаны с карты 7530 (арифметика сходится копейка в копейку: 89181.11-474.68-507=88199.43
= итоговый баланс выписки). Приписываем account/card.
"""
import sqlite3
from pathlib import Path
import ledger_balances

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"
ACC = "40817 810 1 3826 6966221"
c = sqlite3.connect(str(DB))
n = c.execute("UPDATE transactions SET account=?, card='МИР Классическая •••• 7530' "
              "WHERE id IN (263,264) AND source='manual' AND account=''", (ACC,)).rowcount
print(f"приписано к 7530: {n}")
c.commit(); c.close()
ledger_balances.main()
