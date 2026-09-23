"""Планировщик: ledger_plan.py — платежи (payments) и цели (goals).

  ledger_plan.py pay-ls
  ledger_plan.py pay-add ДЕНЬ "заголовок" СУММА [категория] [группа]   — каждый мес.
  ledger_plan.py pay-once YYYY-MM-DD "заголовок" СУММА [категория]     — разово
  ledger_plan.py pay-rm ID
  ledger_plan.py goal-ls
  ledger_plan.py goal-add "имя" СУММА YYYY-MM [заметка]
  ledger_plan.py goal-rm "имя"
"""
import sqlite3
import sys
from pathlib import Path

DB = Path.home() / ".hermes" / "ledger" / "ledger.db"


def conn():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def num(s):
    return float(str(s).replace(" ", "").replace(",", "."))


def pay_ls(c):
    rows = list(c.execute("SELECT * FROM payments ORDER BY repeat='none', day, date"))
    for r in rows:
        sched = f"кажд.мес. д{r['day']}" if r["repeat"] == "monthly" \
            else (r["date"] + " разово")
        print(f"#{r['id']:3} {r['grp'] or '—':12} {r['title']:28} "
              f"{r['amount']:>10,.0f}  {sched}  {r['category'] or ''}")
    print(f"итого строк: {len(rows)}")


def pay_add(c, day, title, amount, cat=None, grp=None):
    c.execute("INSERT INTO payments(day,title,amount,category,grp,repeat) "
              "VALUES(?,?,?,?,?,'monthly')",
              (int(day), title, num(amount), cat, grp))
    print(f"OK платёж: каждый месяц {day} числа — {title} {amount}")


def pay_once(c, date, title, amount, cat=None):
    c.execute("INSERT INTO payments(day,title,amount,category,grp,repeat,date) "
              "VALUES(0,?,?,?,NULL,'none',?)", (title, num(amount), cat, date))
    print(f"OK разовый: {date} — {title} {amount}")


def pay_rm(c, pid):
    print("удалено:", c.execute("DELETE FROM payments WHERE id=?", (int(pid),)).rowcount)


def goal_ls(c):
    for r in c.execute("SELECT * FROM goals"):
        print(f"{r['name']:20} {r['target']:>12,.0f}  до {r['deadline']}  {r['note'] or ''}")


def goal_add(c, name, target, deadline, note=None):
    assert len(deadline) == 7 and deadline[4] == "-", "deadline: YYYY-MM"
    c.execute("INSERT OR REPLACE INTO goals(name,target,deadline,note) VALUES(?,?,?,?)",
              (name, num(target), deadline, note))
    print(f"OK цель: {name} {target} к {deadline}")


def goal_rm(c, name):
    print("удалено:", c.execute("DELETE FROM goals WHERE name=?", (name,)).rowcount)


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    op = a[0].replace("_", "-")
    c = conn()
    if op == "pay-ls":
        pay_ls(c)
    elif op == "pay-add":
        pay_add(c, *a[1:6])
    elif op == "pay-once":
        pay_once(c, *a[1:5])
    elif op == "pay-rm":
        pay_rm(c, a[1])
    elif op == "goal-ls":
        goal_ls(c)
    elif op == "goal-add":
        goal_add(c, *a[1:5])
    elif op == "goal-rm":
        goal_rm(c, a[1])
    else:
        print("не знаю:", op)
    c.commit()


if __name__ == "__main__":
    main()
