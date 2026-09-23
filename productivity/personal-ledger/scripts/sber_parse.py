"""Парсер PDF-выписок Сбербанка (дебет/счёт/кредитка). v2.

Блоки страницы группируются по y (±3pt) — строка таблицы может быть разбита
на несколько блоков. Сумма распознётся только с копейками (код авторизации — нет).
Знак: '+...' = пополнение/возврат; без знака = списание.
"""
import re
import pymupdf
from datetime import datetime

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")
CODE_RE = re.compile(r"^\d{5,6}$")
MONEY_RE = re.compile(r"^[+]?\d[\d\s\u00A0]*[.,]\d{2}$")

NOISE_SUBSTR = ("www.sber", "Заказано", "Вавилова", "Страница", "ОСТАТОК СРЕДСТВ",
                "КАТЕГОРИЯ", "СУММА В", "Дата обработки", "и код авторизации",
                "Описание операции", "Сумма в валюте", "В валюте", "операции²",
                "операции2", "ДАТА ОПЕРАЦИИ", "Расшифровка", "ИТОГО ПО", "Печать")

def num(s):
    return float(s.replace("\u00A0", "").replace(" ", "").replace(",", "."))

def _is_noise(line):
    return any(k in line for k in NOISE_SUBSTR)

def _row_blocks(page):
    """[(y, [lines...])] — блоки, сгруппированные по вертикали."""
    rows = {}
    for b in sorted(page.get_text("blocks"), key=lambda x: x[1]):
        y = round(b[1])
        key = next((k for k in rows if abs(k - y) <= 3), y)
        for l in b[4].split("\n"):
            l = l.strip()
            if l and not _is_noise(l):
                rows.setdefault(key, []).append(l)
    return sorted(rows.items())

def parse(path):
    doc = pymupdf.open(path)
    head = doc[0].get_text()
    kind = ("credit" if "кредитной карты" in head
            else "account" if "платёжному счёту" in head else "debit")
    m = re.search(r"((?:МИР|Кредитная СберКарта)[^\n]*?•+\s*\d{4})", head)
    card = m.group(1).strip() if m else ""
    m = re.search(r"(\d{5}\s\d{3}\s\d\s\d+\s\d+)", head)
    account = m.group(1).replace("\u00A0", " ") if m else ""
    end_balance = end_date = debt = limit_ = None
    for m in re.finditer(r"Остаток на (\d{2}\.\d{2}\.\d{4})\s*\n?([\d\s\u00A0]+[\d,]{2})", head):
        end_date, end_balance = m.group(1), num(m.group(2))
    m = re.search(r"Общая задолженность на\s*\n?([\d.]+)\s*\n?([\d\s\u00A0]+[\d,]{2})", head)
    if m:
        end_date, debt = m.group(1), num(m.group(2))
    m = re.search(r"Кредитный лимит\s*\n?([\d\s\u00A0]+[\d,]{2})", head)
    if m:
        limit_ = num(m.group(1))
    m = re.search(r"За период (\d{2}\.\d{2}\.\d{4})\s*[—-]\s*(\d{2}\.\d{2}\.\d{4})", head)
    period = m.groups() if m else ("", "")
    # заявленные итоги для самопроверки
    stated_inc = stated_out = None
    m = re.search(r"Пополнение\s*\n?([\d\s\u00A0]+[\d,]{2})\n", head)
    if m:
        stated_inc = num(m.group(1))
    m = re.search(r"Списание[^\n]*\n([\d\s\u00A0]+[\d,]{2})\n", head)
    if m:
        stated_out = num(m.group(1))

    txns, skipped = [], []
    for page in doc:
        for y, lines in _row_blocks(page):
            if not lines or not DATE_RE.match(lines[0]):
                continue
            if lines[0] == period[0] and any("Остаток на" in l for l in lines):
                continue
            monies = [l for l in lines if MONEY_RE.match(l)]
            nonmoney = [l for l in lines
                        if not DATE_RE.match(l) and not TIME_RE.match(l)
                        and not CODE_RE.match(l) and not MONEY_RE.match(l)]
            if not monies:
                skipped.append(" ".join(lines)[:100])
                continue
            category = nonmoney[0] if nonmoney and len(nonmoney[0]) < 40 and not any(c.isdigit() for c in nonmoney[0]) else ""
            desc = " ".join(nonmoney[1:] if category else nonmoney)
            desc = re.sub(r"\s*Операция по[^\n]*", "", desc).strip()
            amount = abs(num(monies[0])) * (1 if monies[0].startswith("+") else -1)
            balance = num(monies[-1]) if len(monies) >= 2 and not monies[-1].startswith("+") else None
            txns.append({
                "date": datetime.strptime(lines[0], "%d.%m.%Y").date().isoformat(),
                "category": category or "Прочие операции",
                "amount": amount,
                "balance_after": balance,
                "payee": desc.split(".")[0][:80],
            })
    header = {"kind": kind, "card": card, "account": account, "period": period,
              "stated_income": stated_inc, "stated_outcome": stated_out,
              "end_balance": end_balance, "end_date": end_date,
              "debt": debt, "credit_limit": limit_}
    return header, txns, skipped

if __name__ == "__main__":
    import sys, json
    hdr, tx, skipped = parse(sys.argv[1])
    inc = sum(t["amount"] for t in tx if t["amount"] > 0)
    out = -sum(t["amount"] for t in tx if t["amount"] < 0)
    print(json.dumps(hdr, ensure_ascii=False))
    print(f"n={len(tx)} in={inc:,.2f} out={out:,.2f}")
    ok_in = hdr["stated_income"] is None or abs(inc - hdr["stated_income"]) < 0.01
    ok_out = hdr["stated_outcome"] is None or abs(out - hdr["stated_outcome"]) < 0.01
    din = "" if ok_in else f" (получено {inc:,.2f} vs заявлено {hdr['stated_income']:,.2f})"
    dout = "" if ok_out else f" (получено {out:,.2f} vs заявлено {hdr['stated_outcome']:,.2f})"
    print(f"СВЕРКА: in={'OK' if ok_in else 'РАСХОЖДЕНИЕ' + din}  out={'OK' if ok_out else 'РАСХОЖДЕНИЕ' + dout}")
    for s in skipped[:6]:
        print("  ⚠ skipped:", s)
