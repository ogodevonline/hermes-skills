"""Запросы к ledger.db -> данные для шаблона. (модуль personal-ledger)"""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

MSK = timezone(timedelta(hours=3))
DB = Path.home() / ".hermes" / "ledger" / "ledger.db"


def _c():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def load():
    c = _c()
    tx = [dict(r) for r in c.execute(
        "SELECT date, time, account, card, category, amount, payee, source, balance_of "
        "FROM transactions")]
    for t in tx:  # json -> dict на стороне Python, JS-getter не нужен
        try:
            t["bal"] = json.loads(t.pop("balance_of") or "{}")
        except (TypeError, json.JSONDecodeError):
            t["bal"] = {}
    plans = [dict(r) for r in c.execute("SELECT * FROM plans")]
    payments = [dict(r) for r in c.execute(
        "SELECT day,title,amount,category,grp,repeat,date FROM payments ORDER BY day")]
    goals = [dict(r) for r in c.execute(
        "SELECT name,target,deadline,note FROM goals")]
    accounts = [dict(r) for r in c.execute(
        "SELECT account, card, balance, debt, credit_limit, asof FROM accounts")]
    for a in accounts:  # asof: ISO или д.м.г -> "дд.мм"
        d = (a["asof"] or "").strip()
        a["asof"] = f"{d[8:10]}.{d[5:7]}" if len(d) == 10 and d[4] == "-" else d[:5]
    # account(номер счёта) -> короткое имя карты для колонок баланса
    names = {a["account"]: (a["card"] or a["account"][-4:]) for a in accounts}
    names["CASH"] = "нал"
    now = datetime.now(MSK)
    today = now.date()
    return {
        "tx": tx, "plans": plans, "payments": payments, "goals": goals,
        "accounts": accounts, "names": names,
        "today": today.isoformat(),
        "yest": (today - timedelta(days=1)).isoformat(),
        "week0": (today - timedelta(days=6)).isoformat(),
        "stamp": now.strftime("%d.%m.%Y %H:%M МСК"),
    }
