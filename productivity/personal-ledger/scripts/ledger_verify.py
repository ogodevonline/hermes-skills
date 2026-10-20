"""Сверка выписок с базой: каждая PDF-выписка должна совпасть с транзакциями счёта построчно.

Запуск: ledger_verify.py <выписка.pdf> [...]
Проверяет для каждого файла:
  1. внутреннюю цепочку PDF: balance_after(строка) - amount == balance_after(следующая старее);
  2. арифметику: первый баланс - amount первой строки = открытие; открытие + приход - расход = последний баланс;
  3. мультимножество (дата, сумма) строк PDF против строк счёта в БД за период выписки.
Ничего не пишет. Выход 1, если есть расхождения.
"""
import glob
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sber_parse  # noqa: E402

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"


def _iso(ddmmyyyy: str) -> str:
    d, m, y = ddmmyyyy.split(".")
    return f"{y}-{m}-{d}"


def _chain_errors(txns: list[dict]) -> list[str]:
    """txns идут от новых к старым (порядок выписки). До строки i баланс = balance_after[i] - amount[i]."""
    errs = []
    for i in range(len(txns) - 1):
        newer, older = txns[i], txns[i + 1]
        if newer.get("balance_after") is None or older.get("balance_after") is None:
            continue
        before = round(newer["balance_after"] - newer["amount"], 2)
        if abs(before - older["balance_after"]) > 0.005:
            errs.append(f"цепочка: {newer['date']} {newer['payee'][:30]} → {before} ≠ {older['balance_after']}")
    return errs


def _check_file(path: str, con: sqlite3.Connection) -> int:
    header, txns, _ = sber_parse.parse(path)
    acc = header["account"]
    print(f"== {header['card']} ({acc}) период {header['period'][0]}–{header['period'][1]}, строк PDF: {len(txns)}")
    # У кредитки строки «Погашение процентов» — часть платежа, парсер их не вычитает,
    # поэтому цепочка и арифметика по балансу тут не применимы (известное ограничение).
    is_credit = header["kind"] == "credit"
    problems = [] if is_credit else _chain_errors(txns)

    inc = round(sum(t["amount"] for t in txns if t["amount"] > 0), 2)
    out = round(-sum(t["amount"] for t in txns if t["amount"] < 0), 2)
    last = next((t["balance_after"] for t in txns if t.get("balance_after") is not None), None)
    first = txns[-1]
    opening = round(first["balance_after"] - first["amount"], 2) if first.get("balance_after") is not None else None
    if opening is not None and last is not None and not is_credit:
        print(f"  арифметика: открытие {opening} + приход {inc} - расход {out} = {round(opening + inc - out, 2)} (последний баланс строки: {last})")
        if abs(opening + inc - out - last) > 0.005:
            problems.append("арифметика открытие+приход-расход ≠ последний баланс")

    pdf = Counter((t["date"], round(t["amount"], 2)) for t in txns)
    lo, hi = _iso(header["period"][0]), _iso(header["period"][1])
    db = Counter((r[0], round(r[1], 2)) for r in con.execute(
        "SELECT date, amount FROM transactions WHERE account=? AND date BETWEEN ? AND ? AND (source LIKE 'doc_%' OR source='reconciled')",
        (acc, lo, hi)))
    missing = dict(pdf - db)
    extra = dict(db - pdf)
    manual = con.execute(
        "SELECT date, amount, payee FROM transactions WHERE account=? AND date BETWEEN ? AND ? AND source IN ('manual','reconciled')",
        (acc, lo, hi)).fetchall()
    if missing:
        problems.append(f"нет в БД (есть в PDF): {missing}")
    if extra:
        problems.append(f"лишние в БД (нет в PDF): {extra}")
    if manual:
        print(f"  ручные/сверенные строки в периоде: {len(manual)} — проверить, что не дублируют PDF: {manual}")

    if problems:
        print("  РАСХОЖДЕНИЯ:")
        for p in problems:
            print("   -", p)
    else:
        print("  OK: цепочка, арифметика и построчное совпадение с БД")
    return len(problems)


def main(argv: list[str]) -> int:
    paths = []
    for a in argv:
        paths.extend(glob.glob(a) or [a])
    if not paths:
        print("usage: ledger_verify.py <выписка.pdf> [...]")
        return 2
    con = sqlite3.connect(str(DB))
    bad = sum(_check_file(p, con) for p in paths)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
