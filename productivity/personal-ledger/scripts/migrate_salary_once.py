"""Разовая миграция: конверт-зарплата, вклад, сторонние переводы + план 300к."""
import sqlite3
from pathlib import Path

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"
c = sqlite3.connect(str(DB))

c.executescript("""
-- карта: официальные зачисления работодателя
UPDATE transactions SET category='Зарплата (карта)'
 WHERE payee LIKE '%Заработная плата%';
-- конверт: всё внесённое в банкоматы — по факту зарплата
UPDATE transactions SET category='Зарплата (нал)'
 WHERE sber_cat='Внесение наличных';
-- снятие вклада — не зарплата, отдельный доход
UPDATE transactions SET category='Иной доход (вклад)'
 WHERE payee LIKE '%VKLAD%';
-- сторонние поступления (не от себя)
UPDATE transactions SET category='Переводы от других'
 WHERE payee LIKE '%Перевод из Alfa-Bank%' OR payee LIKE '%Перевод из T-Bank%'
    OR payee LIKE '%Перевод от Г%';
-- план зарплаты 300к с июля
INSERT OR REPLACE INTO plans VALUES ('*','Зарплата','income',300000);
""")
c.commit()
for r in c.execute("""SELECT month,
    SUM(CASE WHEN category LIKE 'Зарплата%' THEN amount ELSE 0 END) sal,
    ROUND(300000 - SUM(CASE WHEN category LIKE 'Зарплата%' THEN amount ELSE 0 END)) gap
    FROM transactions GROUP BY month ORDER BY month"""):
    print(f"{r[0]}  зарплата {r[1]:>10,.0f}  недоплата {r[2]:>10,.0f}")
