"""Ledger: импорт sber-выписок в SQLite + сводки.
ledger.db: transactions (date, account, card, category, amount, payee, raw),
budgets (category, monthly_limit).
"""
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sber_parse import parse

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"
DB.parent.mkdir(parents=True, exist_ok=True)

# Сберовская категория -> наша
CAT_MAP = {
    "Супермаркеты": "Продукты", "Рестораны и кафе": "Кафе и рестораны",
    "Перевод на карту": "Переводы", "Перевод с карты": "Переводы",
    "Перевод СБП": "Переводы", "Внесение наличных": "Наличка/пополнение",
    "Снятие наличных": "Наличные", "Прочие расходы": "Прочее",
    "Прочие операции": "Прочее", "Транспорт": "Транспорт",
    "Связь и интернет": "Связь", "Развлечения": "Развлечения",
    "Здоровье": "Здоровье", "Красота": "Красота", "Одежда и обувь": "Одежда",
    "Образование": "Образование", "Коммунальные услуги": "ЖКХ",
    "Платежи и переводы": "Переводы", "Финансовые услуги": "Проценты/комиссии",
    "Страхование": "Страхование", "Туризм": "Путешествия",
    "Мебель и интерьер": "Дом", "Товары для дома": "Дом",
    "Электроника и антенны": "Электроника", "Бытовая техника": "Электроника",
    "Детские товары": "Дети", "Товары для детей": "Дети",
    "Зоотовары": "Дом", "Культура и искусство": "Развлечения",
    "Цифровые услуги": "Подписки", "Комиссия банка": "Проценты/комиссии",
    "Пенсионные взносы": "Налоги/взносы", "Госпошлины": "Налоги/взносы",
    "Штрафы": "Налоги/взносы", "Благотворительность": "Благотворительность",
    "Авиа and железнодорожные билеты": "Путешествия",
    "Доход": "Доход", "Возврат по операции": "Возврат",
    "Внесение наличных": "Зарплата (нал)",
}
MERCHANT_RULES = [
    # доходы: конверт-зарплата, вклад, чужие переводы (свои "от/для С. Василий" = Переводы)
    (re.compile(r"Заработная плата", re.I), "Зарплата (карта)"),
    (re.compile(r"VKLAD", re.I), "Иной доход (вклад)"),
    (re.compile(r"Перевод из (Alfa|T-Bank|Т-Банк)", re.I), "Переводы от других"),
    (re.compile(r"KUPIBILET|Uzbekistan Airways|АЭРОФЛОТ|S7|ПОБЕДА|Ж/Д|РЖД|ОЗУ", re.I), "Путешествия"),
    (re.compile(r"VKUSNOITOCH|ВКУСНО|SHAKE|KFC|Burger|СУШИ|ПИЦЦ", re.I), "Кафе и рестораны"),
    # Яндекс-ПОДПИСКА Плюс = Подписки (Василий 22.09); в выписке она идёт как
    # 'SBSCR_Сервисы Яндекса' или 'YANDEX*...PLUS' — поездки (GO/DRIVE/Скутеры) = Транспорт
    (re.compile(r"SBSCR|Сервисы Яндекса|YANDEX.*(PLUS|ПЛЮС)", re.I), "Подписки"),
    (re.compile(r"YANDEX.*(DRIVE|TAXI)|CITMOB|WEGO|MAXIM", re.I), "Подписки/транспорт"),
    (re.compile(r"BEELINE|MTS|MTC|MEGAFON|TELE2|ROSTELECOM|T2\b", re.I), "Связь"),
    (re.compile(r"OZON|WB\b|WILDBERR|ALIEXPRESS|ЯНДЕКС.МАРКЕТ|YAMART|XMLstock", re.I), "Маркетплейсы"),
    (re.compile(r"\bVK\b|VK MUSIC|VKMUSIC|MUSIC|SPOTIFY|NETFLIX|KILO|CHATGPT|OPENAI|GOOGLE.*100GB|STORAGE", re.I), "Подписки"),
    (re.compile(r"APTEKA|ЗДОРБ|РГ-ФАРМ|ГОРЗДРАВ|36\.6|HEALTH|АПТЕЧ", re.I), "Здоровье"),
    (re.compile(r"PIRELLI|ШИП|AUTO|CAR|БЕНЗ|Lukoil|GAZPROM.*NEF|TATNEF|SHELL|BP\b", re.I), "Авто/бензин"),
    (re.compile(r"HAGZ| HARD |ДИСКОНТ|ПЯТЕР|МАГНИТ|ЛЕНТА|SPAR|DIXY|ДИКСИ|АШАН|METRO", re.I), "Продукты"),
    (re.compile(r"FAMILIA", re.I), "Одежда"),
    # 21.09 вечер: серверы, ЖКХ, ИИ-подписки (расширение категорий)
    (re.compile(r"VDSKA|VDS\b|HOSTING", re.I), "Хостинг/техника"),
    (re.compile(r"TVOI DOM|ENERGO\b|ЖКХ|ВОДОКАНА", re.I), "ЖКХ"),
    (re.compile(r"DZENMAN|TELEGRAM", re.I), "Подписки"),
]

def to_cat(sber_cat, payee):
    for rx, cat in MERCHANT_RULES:
        if rx.search(payee):
            return cat
    if sber_cat == "Оплата по QR–коду СБП":
        return "Прочее"
    return CAT_MAP.get(sber_cat, sber_cat or "Прочее")

def init_db():
    c = sqlite3.connect(str(DB))
    c.executescript("""
    CREATE TABLE IF NOT EXISTS transactions(
      id INTEGER PRIMARY KEY, date TEXT, month TEXT, account TEXT, card TEXT,
      sber_cat TEXT, category TEXT, amount REAL, balance_after REAL,
      payee TEXT, source TEXT, UNIQUE(date, account, amount, payee)
    );
    CREATE TABLE IF NOT EXISTS budgets(category TEXT PRIMARY KEY, monthly REAL);
    CREATE TABLE IF NOT EXISTS accounts(
      account TEXT PRIMARY KEY, card TEXT, balance REAL, debt REAL,
      credit_limit REAL, asof TEXT, source TEXT);
    CREATE TABLE IF NOT EXISTS plans(
      month TEXT NOT NULL DEFAULT '*', category TEXT NOT NULL,
      kind TEXT NOT NULL DEFAULT 'expense', amount REAL NOT NULL,
      PRIMARY KEY(month, category, kind));
    """)
    return c

def import_file(c, path):
    """Банковская строка: 1) сверить с ручной (manual) — поглотив её;
    2) иначе INSERT. Ручная запись = черновик, выписка = истина."""
    hdr, tx, skipped = parse(path)
    n_new = n_rec = 0
    if hdr.get("end_balance") is not None or hdr.get("debt") is not None:
        c.execute("""INSERT OR REPLACE INTO accounts
                     (account, card, balance, debt, credit_limit, asof, source)
                     VALUES (?,?,?,?,?,?,?)""",
                  (hdr["account"], hdr["card"], hdr.get("end_balance"),
                   hdr.get("debt"), hdr.get("credit_limit"), hdr["period"][1],
                   Path(path).name))
    for t in tx:
        # сверка: та же сумма/направление, ТОЧНО та же дата (ручная запись
        # всегда за текущий день МСК — см. ledger_add.py), ещё не сверена
        m = c.execute(
            """SELECT id, category FROM transactions
               WHERE source='manual' AND account=''
                 AND date=? AND ROUND(amount,2)=ROUND(?,2)
               LIMIT 1""",
            (t["date"], t["amount"])).fetchone()
        if m:
            # банковская строка уже в базе (ручная опоздала)? -> manual удалить,
            # но категорию пользователя перенести на банковскую строку
            bank = c.execute(
                """SELECT id FROM transactions WHERE source!='manual'
                     AND date=? AND account=? AND ROUND(amount,2)=ROUND(?,2)
                     AND payee LIKE ?""",
                (t["date"], hdr["account"], t["amount"], t["payee"][:20] + "%")).fetchone()
            if bank:
                if m[1] not in ("Прочее", None):
                    c.execute("UPDATE transactions SET category=? WHERE id=?", (m[1], bank[0]))
                c.execute("DELETE FROM transactions WHERE id=?", (m[0],))
                n_rec += 1
                continue
            cat = m[1] if m[1] not in ("Прочее", None) else to_cat(t["category"], t["payee"])
            c.execute(
                """UPDATE transactions SET date=?, month=?, account=?, card=?,
                       sber_cat=?, category=?, balance_after=?, payee=?, source='reconciled'
                   WHERE id=?""",
                (t["date"], t["date"][:7], hdr["account"], hdr["card"], t["category"],
                 cat, t["balance_after"], t["payee"], m[0]))
            n_rec += 1
            continue
        cur = c.execute(
            """INSERT OR IGNORE INTO transactions
               (date, month, account, card, sber_cat, category, amount,
                balance_after, payee, source) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (t["date"], t["date"][:7], hdr["account"], hdr["card"], t["category"],
             to_cat(t["category"], t["payee"]), t["amount"], t["balance_after"],
             t["payee"], Path(path).name))
        n_new += cur.rowcount
    return hdr, n_new, len(skipped), n_rec

def report(c):
    print(f"Всего транзакций: {c.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]}")
    print("\n== Месяц: доход / расход ==")
    for m, inc, out in c.execute("""SELECT month,
        SUM(CASE WHEN amount>0 THEN amount ELSE 0 END),
        -SUM(CASE WHEN amount<0 THEN amount ELSE 0 END)
        FROM transactions GROUP BY month ORDER BY month"""):
        print(f"  {m}: +{inc:,.0f} / -{out:,.0f}")
    print("\n== Категории за 3 мес (расходы) ==")
    for cat, s in c.execute("""SELECT category, ROUND(SUM(-amount)) FROM transactions
        WHERE amount<0 GROUP BY category ORDER BY 2 DESC LIMIT 12"""):
        print(f"  {cat:22} {s:>12,.0f}")

def report_file():
    import sqlite3 as _s
    con = _s.connect(str(DB))
    try:
        report(con)
    finally:
        con.close()

if __name__ == "__main__":
    c = init_db()
    for p in sys.argv[1:]:
        hdr, n_new, n_skip, n_rec = import_file(c, p)
        print(f"✓ {hdr['card'] or hdr['account']}: +{n_new} новых, сверено с ручными: {n_rec} (блоков пропущено: {n_skip})")
    c.commit()
    c.close()
    report_file()
    import ledger_balances
    ledger_balances.main()  # balance_of для колонок «на счёте» в дашборде
