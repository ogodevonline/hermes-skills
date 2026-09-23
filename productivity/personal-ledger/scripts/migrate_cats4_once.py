"""Миграция 4: расширяем категории (21.09 вечер) + планы по новым статьям.

Правила — по sber_cat + payee. 'Прочее' оставляем только реально неопознанному.
Здоровье и Аптека/здоровье сливаем в одну статью 'Здоровье' (план уже 1500).
"""
import sqlite3
from pathlib import Path

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"
c = sqlite3.connect(str(DB))

RULES = [
    # техника/серверы — не «Прочее»
    ("Хостинг/техника", "payee LIKE '%VDSKA%' OR payee LIKE '%VDS %' OR payee LIKE '%HOSTING%'"),
    # аптеки, провалившиеся через QR в Прочее
    ("Здоровье", "payee LIKE '%АПТЕ%' OR payee LIKE '%APTEKA%' OR payee LIKE '%ЗДОРБ%' "
                 "OR payee LIKE '%ФАРМ%' OR payee LIKE '%36.6%' OR payee LIKE '%ГОРЗДРАВ%' "
                 "OR payee LIKE '%HEALTH%'"),
    # ЖКХ
    ("ЖКХ", "payee LIKE '%TVOI DOM%' OR payee LIKE '%ENERGO%' OR payee LIKE '%ЖКХ%' OR payee LIKE '%ВОДОКАНА%'"),
    # продукты, провалившиеся в QR-прочее
    ("Продукты", "payee LIKE '%ДИКСИ%' OR payee LIKE '%ПЯТЕР%' OR payee LIKE '%МАГНИТ%'"),
    # подписки: Zenman (ИИ-подписка), Telegram Premium
    ("Подписки", "payee LIKE '%DZENMAN%' OR payee LIKE '%TELEGRAM%'"),
    # merging дублей
    ("Здоровье", "category='Аптека/здоровье' OR category='Здоровье и красота' OR sber_cat='Здоровье и красота'"),
    ("Одежда", "category='Одежда и аксессуары'"),
    ("Дом", "category='Все для дома'"),
]
for cat, cond in RULES:
    cur = c.execute(f"UPDATE transactions SET category=? WHERE ({cond})", (cat,))
    if cur.rowcount:
        print(f"  {cat}: {cur.rowcount}")

# планы по новым статьям
for cat, amt in [("Хостинг/техника", 4000), ("ЖКХ", 3000), ("Дом", 1000)]:
    c.execute("INSERT OR REPLACE INTO plans (month,category,kind,amount) VALUES ('*',?,'expense',?)", (cat, amt))
# переименование плана под слитую категорию
c.execute("UPDATE plans SET category='Здоровье' WHERE category='Аптека/здоровье'")
c.commit()
print("осталось Прочее (расход):", c.execute(
    "SELECT COUNT(*) FROM transactions WHERE category='Прочее' AND amount<0").fetchone()[0])
for r in c.execute("SELECT category, COUNT(*), ROUND(SUM(-amount)) FROM transactions "
                   "WHERE amount<0 GROUP BY category ORDER BY 3 DESC"):
    print(" %-22s %3d %10s" % r)
