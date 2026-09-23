"""Схема планирования: payments (запланированные платежи) + goals (цели). Идемпотентно."""
import sqlite3
from pathlib import Path

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"

SEED_PAY = [
    (3, "Подписка Dzenmani", 249, "Подписки", "Обязательное"),
    (5, "Telegram Premium", 299, "Подписки", "Обязательное"),
    (7, "Связь T2", 730, "Связь", "Обязательное"),
    (8, "Хостинг VDSKA", 1615, "Хостинг/техника", "Обязательное"),
    (14, "ЖКХ «Твои Ворота»", 1160, "ЖКХ", "Обязательное"),
    (21, "Комиссия Сбер Мобильный банк", 99, "Подписки", "Обязательное"),
]

if __name__ == "__main__":
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS payments(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      day INTEGER NOT NULL, title TEXT NOT NULL, amount REAL NOT NULL,
      category TEXT, grp TEXT,
      repeat TEXT NOT NULL DEFAULT 'monthly',   -- monthly|yearly|none
      date TEXT                                  -- разовая дата YYYY-MM-DD (repeat=none)
    );
    CREATE TABLE IF NOT EXISTS goals(
      name TEXT PRIMARY KEY, target REAL NOT NULL,
      deadline TEXT NOT NULL, note TEXT          -- deadline YYYY-MM
    );
    """)
    # разовые платежи из легаси plans(kind='once') -> payments (если колонки уже есть)
    moved = 0
    cols = {r[1] for r in con.execute("PRAGMA table_info(plans)")}
    if {"dom", "grp", "title"} <= cols:
        moved = con.execute(
            "INSERT INTO payments(day,title,amount,category,grp,repeat,date) "
            "SELECT dom, COALESCE(title,category), amount, category, grp, 'none', "
            "       month||'-'||printf('%02d',dom) FROM plans "
            "WHERE kind='once' AND month!='*' "
            "  AND NOT EXISTS(SELECT 1 FROM payments WHERE repeat='none')").rowcount
    if con.execute("SELECT COUNT(*) FROM payments").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO payments(day,title,amount,category,grp) VALUES(?,?,?,?,?)",
            SEED_PAY)
        print(f"payments засеяно: {len(SEED_PAY)}")
    print("goals:", con.execute("SELECT COUNT(*) FROM goals").fetchone()[0],
          "| moved once:", moved, "| payments:",
          con.execute("SELECT COUNT(*) FROM payments").fetchone()[0])
    con.commit()
