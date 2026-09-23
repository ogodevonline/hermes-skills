"""Балансы счетов на дату/время каждой операции -> transactions.balance_of (json).

Идемпотентно; вызывается из ledger_add.py / ledger_import.py (и миграциями).
Алгоритм на каждый дебетовый счёт (кредитка не участвует — её balance=лимит):
- идём по операциям счёта хронологично: дни по дате, внутри дня банковские
  строки (balance_after=не NULL) в порядке id (= порядок выписки), ручные —
  по своему времени после банковских строк того же дня без времени;
- строка с balance_after = якорь-истина (cur := balance_after);
- ручная строка без якоря: cur += amount (цепочка от последнего якоря);
- row_val[id] = cur после этой строки; конец дня = cur после последней строки.
CASH: остаток = accounts.CASH.balance на свою asof-дату, дельты ручных наличных
после asof откатываются, дальше роллим по дням; показываем «после операции».
"""
import json
import sqlite3
from pathlib import Path

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"
CASH_KEY = "CASH"


def _order_key(t):
    # банковские строки без времени идут раньше ручных того же дня
    return (0, t["id"]) if not t["time"] else (1, t["id"])


def _account_snapshots(tx, acc):
    """cur-цепочка по счёту: возвращает (row_val {id: остаток_после}, day_end {date: остаток})."""
    row_val, day_end = {}, {}
    cur = None
    days = {}
    for t in tx:
        if t["account"] == acc:
            days.setdefault(t["date"], []).append(t)
    for d in sorted(days):
        for t in sorted(days[d], key=_order_key):
            if t["balance_after"] is not None:
                cur = t["balance_after"]
            elif cur is not None:
                cur = cur + t["amount"]
            if cur is not None:
                row_val[t["id"]] = round(cur, 2)
        day_end[d] = cur
    return row_val, day_end


def main() -> None:
    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    if not any(r["name"] == "balance_of" for r in con.execute("PRAGMA table_info(transactions)")):
        con.execute("ALTER TABLE transactions ADD COLUMN balance_of TEXT")

    debit = {r["account"] for r in con.execute(
        "SELECT account FROM accounts WHERE account!='CASH' AND debt IS NULL")}
    tx = [dict(r) for r in con.execute(
        "SELECT id,date,account,time,amount,balance_after FROM transactions ORDER BY date,id")]

    vals, ends = {}, {}
    for acc in debit:
        vals[acc], ends[acc] = _account_snapshots(tx, acc)

    # наличные
    accrow = con.execute("SELECT balance,asof FROM accounts WHERE account='CASH'").fetchone()
    cash_delta: dict[str, float] = {}
    for t in tx:
        if t["account"] == CASH_KEY:
            cash_delta[t["date"]] = cash_delta.get(t["date"], 0.0) + t["amount"]
    base = (accrow["balance"] if accrow and accrow["balance"] is not None else 0.0) or 0.0
    if accrow and accrow["asof"]:
        a = str(accrow["asof"])[:10]
        asof = f"{a[8:10]}.{a[5:7]}.{a[0:4]}" if a[4] == "." else a
        for d in sorted(cash_delta, reverse=True):
            if d > asof:
                base -= cash_delta[d]
            else:
                break
    cash, run = {}, base
    for d in sorted(cash_delta):
        run += cash_delta[d]
        cash[d] = round(run, 2)
    # остаток кармана после каждой CASH-операции: база + дельты дня в порядке id
    cash_row = {}
    cur = base
    for t in [x for x in tx if x["account"] == CASH_KEY]:  # tx отсортирован по date,id
        cur += t["amount"]
        cash_row[t["id"]] = round(cur, 2)

    upd = 0
    for t in tx:
        snap = {}
        acc = t["account"]
        for a2 in debit:
            if a2 == acc and t["id"] in vals[a2]:
                snap[a2] = vals[a2][t["id"]]          # свой счёт: остаток ПОСЛЕ этой операции
            else:
                v = _last_before(ends[a2], t["date"])
                if v is not None:
                    snap[a2] = v                       # чужой: срез на конец дня
        if acc == CASH_KEY:
            snap[CASH_KEY] = cash_row.get(t["id"], base)
        else:
            v = _last_before(cash, t["date"])
            if v is not None:
                snap[CASH_KEY] = v
        con.execute("UPDATE transactions SET balance_of=? WHERE id=?",
                    (json.dumps(snap, separators=(",", ":")), t["id"]))
        upd += 1
    con.commit()
    print(f"✓ balance_of: {upd} операций")


def _last_before(day_end, date):
    d = max((k for k, v in day_end.items() if k <= date and v is not None), default=None)
    return round(day_end[d], 2) if d else None


if __name__ == "__main__":
    main()
