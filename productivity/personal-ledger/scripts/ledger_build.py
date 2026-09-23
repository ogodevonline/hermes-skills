"""Сборка ledger.html. Модули <=150 строк: ledger_data.py + js/*.js."""
import json
from pathlib import Path

from ledger_data import load

HERE = Path(__file__).parent
OUT = Path.home() / ".hermes" / "ledger" / "ledger.html"

d = load()
html = (HERE / "ledger_template.html").read_text()
js = "\n".join((HERE / "js" / f).read_text().rstrip() + "\n"
               for f in ["core.js", "charts2.js", "days.js", "salary.js", "budget.js", "plan.js"])
for k, v in [("TX", d["tx"]), ("PLANS", d["plans"]), ("ACCOUNTS", d["accounts"]),
             ("NAMES", d["names"]), ("PAYMENTS", d["payments"]), ("GOALS", d["goals"])]:
    html = html.replace(f"__{k}__", json.dumps(v, ensure_ascii=False, separators=(",", ":")))
for k, v in [("TODAY", d["today"]), ("YEST", d["yest"]), ("WEEK0", d["week0"])]:
    html = html.replace(f"__{k}__", v)  # в шаблоне кавычки уже есть: "__TODAY__"
html = html.replace("__STAMP__", d["stamp"])
html = html.replace("__JS__", js)
OUT.write_text(html)
print(OUT, f"{len(html)} байт:", len(d["tx"]), "транзакций,",
      len(d["plans"]), "планов,", len(d["accounts"]), "счетов")
