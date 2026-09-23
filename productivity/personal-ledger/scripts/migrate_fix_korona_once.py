"""Миграция 5 (21.09 вечер, со слов Василия):
1. Удалить ложную ручную запись 'Нейросети' -20000 от 21.09 (её не было —
   ошибка migrate_categories_once.py).
2. KORONAPAY 02.09 -10942.53 = перевод Лиме на одежду -> комментарий в payee
   (категория 'Семья' уже верная).
3. KORONAPAY ПОСЛЕ 02.09 = транзит по нейросетям: приходили деньги за работу,
   Василий оплачивал коллегам; пара переводов была лично ему. В бюджет-расходы
   НЕ идут (категория 'Переводы' исключена) — помечаем комментарием в payee.
   (Входящие 'Перевод от С' 11.09 +13 250, 16.09 +10 000 — та же цепочка.)
"""
import sqlite3
from pathlib import Path
import ledger_balances

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"
c = sqlite3.connect(str(DB))

n = c.execute("DELETE FROM transactions WHERE category='Нейросети' AND source='manual' AND date='2026-09-21'").rowcount
print(f"удалено ложных 'Нейросети': {n}")

c.execute("UPDATE transactions SET payee='KORONAPAY — перевод Лиме на одежду' "
          "WHERE id=211")
rows = c.execute("SELECT id,date,amount FROM transactions WHERE payee LIKE 'KORONAPAY%' "
                 "AND category='Переводы' AND amount<0 AND date>'2026-09-02' ORDER BY date").fetchall()
for i, d, a in rows:
    c.execute("UPDATE transactions SET payee='KORONAPAY — нейросети: транзит (пришло за работу → оплата коллегам)' WHERE id=?", (i,))
print(f"помечено транзитов по нейросетям: {len(rows)} на {sum(a for _,_,a in rows):,.0f} ₽")
c.commit()
ledger_balances.main()
