"""Миграция 3: статьи расходов (нейросети/семья/зал/транспорт), планы, лимит быта 20к."""
import sqlite3
from pathlib import Path

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"
c = sqlite3.connect(str(DB))

# --- перекатегоризация существующего ---
c.executescript("""
UPDATE transactions SET category='Семья'
 WHERE (payee LIKE 'KORONAPAY%' AND date='2026-09-02') OR category='Помощь семье';
UPDATE transactions SET category='Зал/спорт' WHERE payee LIKE '%DDX FITNESS%';
UPDATE transactions SET category='Транспорт'
 WHERE payee LIKE 'YANDEX%' OR payee LIKE '%Сервисы Яндекса%' OR category='Подписки/транспорт'
   OR category='Авто/бензин';
UPDATE transactions SET category='Подписки' WHERE payee LIKE '%MOBILE BANK%';
""")

# --- ручные статьи: нейросети 20к (дата — сегодня, поправим если иначе) ---
c.execute("SELECT 1 FROM transactions WHERE category='Нейросети' LIMIT 1") if False else None
if not c.execute("SELECT id FROM transactions WHERE category='Нейросети' LIMIT 1").fetchone():
    c.execute("""INSERT INTO transactions (date,time,account,card,category,amount,payee,source)
        VALUES ('2026-09-21','','','другая карта','Нейросети',-20000,
        'оплата ИИ-сервисов (нейросети)','manual')""")

# --- планы: обязательное / быт / семья / прочее ---
plans = [
    ("Нейросети", 20000), ("Связь", 1000), ("Подписки", 2000),
    ("Транспорт", 4000), ("Зал/спорт", 2000), ("Аптека/здоровье", 1500),
    ("Продукты", 12000), ("Кафе и рестораны", 2000), ("Прочее", 2500),
    ("Семья", 20000), ("Путешествия", 30000), ("Быт", 20000),  # Быт = суммарный лимит жизни
]
for cat, amt in plans:
    c.execute("INSERT OR REPLACE INTO plans (month,category,kind,amount) VALUES ('*',?,'expense',?)", (cat, amt))
c.commit()
for q in ("SELECT ROUND(SUM(-amount)) FROM transactions WHERE date LIKE '2026-09%' AND amount<0 AND category NOT IN ('Переводы','Возврат')",):
    print("сентябрь расход:", q and c.execute(q).fetchone()[0])
print(c.execute("SELECT category, ROUND(SUM(-amount)) FROM transactions WHERE date LIKE '2026-09%' AND amount<0 GROUP BY category ORDER BY 2 DESC").fetchall())
