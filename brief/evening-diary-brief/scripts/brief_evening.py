#!/usr/bin/env python3
"""Вечерний бриф — через SQLite CLI `t`.

Режимы:
- --send (или not TTY): формирует бриф и отправляет в Telegram
- TTY (интерактив): сводка + опрос задач + рефлексия
"""
import sys, os, datetime, subprocess, json
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".hermes" / "skills" / "brief"))
from obsidian_utils import write_note, commit_all, get_vault_path

LIFE_SPHERES = [
    ("🧑‍💻", "Карьера", "30bit, деньги, проекты"),
    ("❤️", "Лима", "отношения с ней"),
    ("👨‍👩‍👧", "Семья/Родные", "родители, близкие"),
    ("🧠", "Развитие", "английский, Python, навыки"),
    ("💪", "Здоровье/Спорт", "зал, сон, еда"),
    ("🏠", "Быт/Финансы", "бюджет, порядок, дом"),
    ("🤝", "Друзья/Люди", "общение вне семьи"),
    ("🎮", "Хобби/Отдых", "пинг-понг, время для себя"),
]

def build_spheres_block():
    """Блок оценки сфер жизни."""
    lines = ["", "🌱 Баланс жизни:"]
    for emoji, name, desc in LIFE_SPHERES:
        lines.append(f"  {emoji} {name}: _ — ({desc})")
    lines.append("")
    return "\n".join(lines)


DIARY_DIR = get_vault_path() / "Дневник"


def dotenv_get(key):
    """Прочитать переменную из ~/.hermes/.env (пропуская комментарии)."""
    env_file = Path.home() / ".hermes" / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.strip()
    return None


def run_t(*args):
    """Выполнить команду t, вернуть stdout."""
    result = subprocess.run(["t", *args], capture_output=True, text=True, timeout=15)
    return result.stdout.strip()

def get_summary():
    """Сводка: статус + задачи + привычки + периодика."""
    status = run_t("status")
    tasks = run_t("list")
    habits = run_t("habits")
    periodic = run_t("periodic")
    return status, tasks, habits, periodic

def build_brief_msg():
    """Сформировать текст брифа."""
    status, tasks, habits, periodic = get_summary()
    today = datetime.date.today().isoformat()
    lines = [
        f"🌙 Вечерний бриф — {today}",
        f"⏰ {datetime.datetime.now().strftime('%H:%M')} МСК",
        "",
        f"📊 {status}",
        "",
        "📋 Задачи:",
        tasks,
        "",
        "🔁 Привычки:",
        habits,
    ]
    if periodic and "Нет" not in periodic:
        lines.append("")
        lines.append("🔄 Периодические напоминания:")
        lines.append(periodic)
    lines.append(build_spheres_block())
    lines.extend([
        "",
        "---",
        "Напиши «подведи итоги» — пройдёмся по каждой задаче.",
    ])
    return "\n".join(lines)

def save_diary_template():
    """Сохранить шаблон дневника."""
    today = datetime.date.today().isoformat()
    status, tasks, habits, periodic = get_summary()

    lines = [
        f"# 📖 Вечерний дневник — {today}",
        "",
        f"**{status}**",
        "",
        "## 📋 Задачи",
        tasks,
        "",
        "## 🔁 Привычки",
        habits,
    ]
    if periodic and "Нет" not in periodic:
        lines.append("")
        lines.append("## 🔄 Периодические напоминания")
        lines.append(periodic)
    lines.append(build_spheres_block())
    lines.extend([
        "",
        "## 💭 Рефлексия",
        "",
        "**1. Что сегодня прошло ХОРОШО?**",
        "  _ _",
        "",
        "**2. Где облажался / можно лучше?**",
        "  _ _",
        "",
        "**3. Главный урок / инсайт дня:**",
        "  _ _",
        "",
        "**4. На что обратить внимание завтра?**",
        "  _ _",
        "",
        "**5. Deep Work (фокус-время):**",
        "  _ _",
        "",
        f"_Создано: {datetime.datetime.now().strftime('%H:%M МСК')}_",
    ])
    content = "\n".join(lines)
    fpath = DIARY_DIR / f"{today}.md"
    write_note(f"Дневник/{today}.md", content)
    commit_all(f"diary {today}: template")
    return fpath

def send_telegram(text):
    """Отправить в Telegram через Bot API."""
    bot_token = dotenv_get("TELEGRAM_BOT_TOKEN")
    chat_id = dotenv_get("TELEGRAM_CHAT_ID") or dotenv_get("TELEGRAM_HOME_CHANNEL")
    if not bot_token or not chat_id:
        print("⚠️ TELEGRAM_BOT_TOKEN или TELEGRAM_HOME_CHANNEL не найдены в .env", file=sys.stderr)
        return False
    try:
        import urllib.request
        payload = json.dumps({"chat_id": int(chat_id), "text": text[:4000]}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"⚠️ Ошибка отправки в Telegram: {e}", file=sys.stderr)
        return False

def interactive_mode():
    """TTY: сводка + интерактивный опрос."""
    status, tasks, habits, periodic = get_summary()
    print(f"\n{'='*60}")
    print("🌙 ВЕЧЕРНИЙ БРИФ")
    print(f"{'='*60}")
    print(f"\n📊 {status}")
    print(f"\n📋 Задачи на сегодня:\n{tasks}")
    print(f"\n🔁 Привычки:\n{habits}")
    if periodic and "Нет" not in periodic:
        print(f"\n🔄 Периодические напоминания:\n{periodic}")
    print(build_spheres_block())
    print(f"\n{'='*60}")
    print("📋 Отмечаем задачи (✅ / ❌ / оставь пустым = пропустить):")
    
    # Получаем ID pending-задач на сегодня
    result = subprocess.run(
        ["t", "list"], capture_output=True, text=True, timeout=15
    )
    for line in result.stdout.strip().split("\n"):
        # Парсим строку вида "  ⏳ 🔴 [ 2] Название"
        parts = line.strip().split()
        if len(parts) >= 3 and parts[0] in ("⏳", "✅", "❌"):
            # [2] → 2
            tid = parts[2].strip("[]")
            name = " ".join(parts[3:])
            if parts[0] == "⏳":
                ans = input(f"  [{tid}] {name} [✅/❌/⏳]: ").strip()
                if ans == "✅":
                    run_t("done", tid)
                    print(f"    → ✅ выполнено")
                elif ans == "❌":
                    run_t("cancel", tid)
                    print(f"    → ❌ отменено")
    
    print(f"\n{'='*60}")
    print("💭 ВОПРОСЫ РЕФЛЕКСИИ:")
    answers = {}
    qs = [
        "1. Что сегодня прошло ХОРОШО?",
        "2. Где облажался / можно лучше?",
        "3. Главный урок / инсайт дня:",
        "4. На что обратить внимание завтра?",
        "5. Deep Work (фокус-время):",
    ]
    for q in qs:
        a = input(f"\n{q}\n  > ").strip() or "_ _"
        answers[q] = a
    
    # Финальный дневник
    today = datetime.date.today().isoformat()
    status2, tasks2, habits2, periodic2 = get_summary()
    lines = [
        f"# 📖 Вечерний дневник — {today}",
        "",
        f"**{status2}**",
        "",
        "## 📋 Задачи",
        tasks2,
        "",
        "## 🔁 Привычки",
        habits2,
    ]
    if periodic2 and "Нет" not in periodic2:
        lines.append("")
        lines.append("## 🔄 Периодические напоминания")
        lines.append(periodic2)
    lines.append(build_spheres_block())
    lines.extend([
        "",
        "## 💭 Рефлексия",
    ])
    for q, a in answers.items():
        lines.append(f"\n**{q}**")
        lines.append(f"  {a}")
    lines.append(f"\n_Создано: {datetime.datetime.now().strftime('%H:%M МСК')}_")
    diary = "\n".join(lines)
    
    print(f"\n{'='*60}")
    print(diary)
    print(f"{'='*60}")
    
    fpath = DIARY_DIR / f"{today}.md"
    write_note(f"Дневник/{today}.md", diary)
    commit_all(f"diary {today}")
    print(f"\n💾 Сохранено: {fpath}")

    # Сохранить лог привычек
    try:
        result = subprocess.run(
            ["python3", str(Path.home() / ".hermes" / "skills" / "brief" / "log_habits.py")],
            capture_output=True, text=True, timeout=15
        )
        if result.stdout.strip():
            print(result.stdout.strip())
    except Exception as e:
        print(f"⚠️ Habit log error: {e}")

def cron_mode():
    """Cron/--send: сформировать бриф, отправить в Telegram, сохранить шаблон."""
    msg = build_brief_msg()

    fpath = save_diary_template()

    print(f"💾 Шаблон: {fpath}")
    print("📨 Отправка в Telegram...")
    ok = send_telegram(msg)
    if ok:
        print("✅ Отправлено")
    else:
        print("⚠️ Не удалось отправить")

def main():
    if "--send" in sys.argv:
        cron_mode()
    elif sys.stdin.isatty():
        interactive_mode()
    else:
        cron_mode()

if __name__ == "__main__":
    main()
