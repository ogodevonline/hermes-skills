"""Пользовательские правила поверх raw-категоризации (22.09, после отката recategorize).

to_cat() даёт 'Подписки/транспорт', 'Спорт и фитнес', 'Авто/бензин' и пр. —
реальные статьи Василия поверх них. Идемпотентно; вызывается из ledger_recategorize.py.
"""
import sqlite3
from pathlib import Path

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"

RULES = [
    # группы Яндекса: поездки => Транспорт; PLUS-подписка уже в MERCHANT_RULES => Подписки
    ("Транспорт", "payee LIKE 'YANDEX%' OR payee LIKE '%Сервисы Яндекса%' OR payee LIKE '%ЯНДЕКС%' "
                  "OR category='Подписки/транспорт' OR category='Авто/бензин' OR payee LIKE 'WHOOSH%'"),
    # пополнение T2 по СБП (ритм раз в месяц 702/710/730) = связь, не транспорт
    ("Связь", "payee LIKE 't2_SBP%'"),
    ("Зал/спорт", "payee LIKE '%DDX FITNESS%' OR category='Спорт и фитнес'"),
    ("Подписки", "payee LIKE '%MOBILE BANK%' OR payee LIKE '%DZENMAN%' OR payee LIKE '%TELEGRAM%' "
                 "OR payee LIKE '%Сервисы Яндекса%' OR payee LIKE 'SBSCR%'"),
    ("Хостинг/техника", "payee LIKE '%VDSKA%' OR payee LIKE '%VDS %' OR payee LIKE '%HOSTING%'"),
    ("Здоровье", "payee LIKE '%АПТЕ%' OR payee LIKE '%APTEKA%' OR payee LIKE '%ЗДОРБ%' "
                 "OR payee LIKE '%ФАРМ%' OR payee LIKE '%36.6%' OR payee LIKE '%ГОРЗДРАВ%' "
                 "OR payee LIKE '%HEALTH%' OR category='Аптека/здоровье' OR category='Здоровье и красота'"),
    ("ЖКХ", "payee LIKE '%TVOI DOM%' OR payee LIKE '%ENERGO%' OR payee LIKE '%ЖКХ%' "
            "OR payee LIKE '%ВОДОКАНА%' OR category='Все для дома' AND payee LIKE '%MASTERKOM%'"),
    ("Продукты", "payee LIKE '%ДИКСИ%' OR payee LIKE '%Дикси%' OR payee LIKE '%ПЯТЕР%' "
                 "OR payee LIKE '%МАГНИТ%'"),
    ("Одежда", "category='Одежда и аксессуары'"),
    ("Дом", "category='Все для дома' AND payee LIKE '%MASTERKOM%'"),
    # Корона: 02.09 = Лиме на одежду (Семья); транзиты помечаем комментарием (Переводы = исключено)
    ("Семья", "payee LIKE 'KORONAPAY%' AND date='2026-09-02'"),
    # ручные (source='manual' в recategorize пропускаются) — фиксированные со слов Василия
    ("Семья", "payee LIKE '%помощь бабушке%'"),
]

PAYEE_MARKS = [
    ("KORONAPAY — нейросети: транзит (пришло за работу → оплата коллегам)",
     "payee='KORONAPAY' AND category='Переводы' AND amount<0 AND date>'2026-09-02'"),
    ("KORONAPAY — перевод Лиме на одежду",
     "payee LIKE 'KORONAPAY%' AND category='Семья'"),
]


def apply(c):
    n = 0
    for cat, cond in RULES:
        cur = c.execute(f"UPDATE transactions SET category=? WHERE ({cond})", (cat,))
        n += cur.rowcount
        if cur.rowcount:
            print(f"  {cat}: {cur.rowcount}")
    for mark, cond in PAYEE_MARKS:
        cur = c.execute(f"UPDATE transactions SET payee=? WHERE ({cond})", (mark,))
        n += cur.rowcount
    return n


if __name__ == "__main__":
    c = sqlite3.connect(str(DB))
    print("обновлено строк:", apply(c))
    c.commit()
    for r in c.execute("SELECT category, COUNT(*), ROUND(SUM(-amount)) FROM transactions "
                       "WHERE amount<0 GROUP BY category ORDER BY 3 DESC"):
        print(" %-22s %3d %10s" % r)
