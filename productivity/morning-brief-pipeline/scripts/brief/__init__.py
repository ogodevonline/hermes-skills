# Morning Brief — главный модуль
# Собирает все блоки утреннего брифа

import os
import sys
import json
import requests
import re
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERMES_HOME = os.path.expanduser("~/.hermes")
MSK = timezone(timedelta(hours=3))

# Загрузить переменные окружения
ENV_FILE = Path(HERMES_HOME) / ".env"
TELEGRAM_BOT_TOKEN = None
TELEGRAM_CHAT_ID = None

if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                TELEGRAM_BOT_TOKEN = line.split("=", 1)[1].strip()
            elif line.startswith("TELEGRAM_ALLOWED_USERS="):
                TELEGRAM_CHAT_ID = line.split("=", 1)[1].strip()


def send_telegram_message(text: str) -> bool:
    """Отправить сообщение в Telegram с fallback на plain text"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram: нет токена или chat_id")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # Сначала пробуем с Markdown
    for parse_mode in ["Markdown", None]:
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": parse_mode
        }
        try:
            resp = requests.post(url, json=data, timeout=10)
            if resp.ok:
                mode = "Markdown" if parse_mode else "plain text"
                print(f"✅ Telegram: отправлено ({mode})")
                return True
            else:
                error = resp.text.lower()
                # Неудача — пробуем следующий вариант
                if parse_mode == "Markdown":
                    if "too long" in error or "can't parse" in error or "bad escape" in error or "invalid" in error:
                        print(f"⚠️ Markdown не сработал, пробуем plain text...")
                        continue
                print(f"❌ Telegram error: {resp.text}")
                return False
        except Exception as e:
            print(f"❌ Telegram exception: {e}")
            return False

    return False


def truncate_text(text: str, max_len: int = 3500) -> str:
    """Обрезать текст до max_len с маркером обрезки"""
    if len(text) <= max_len:
        return text
    return text[:max_len - 50] + "\n\n... (обрезано)"


def simplify_links(text: str) -> str:
    """Заменить ТОЛЬКО очень длинные URL (>100 символов) на домены.
    Короткие/средние ссылки (даже с query/fragment) оставляем как есть."""
    import re

    def replace_link(match):
        link_text = match.group(1)
        url = match.group(2)
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]

        # Сокращаем ТОЛЬКО если URL очень длинный (>100 символов)
        if len(url) > 100:
            return f"[{link_text}]({domain})"
        else:
            return f"[{link_text}]({url})"

    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, text)


def send_brief_chunks(chunks: list[str]) -> bool:
    """Отправить бриф по частям"""
    all_ok = True
    for i, chunk in enumerate(chunks, 1):
        print(f"📤 Отправка части {i}/{len(chunks)} ({len(chunk)} символов)...")
        ok = send_telegram_message(chunk)
        if not ok:
            all_ok = False
    return all_ok


sys.path.insert(0, f"{HERMES_HOME}/skills/productivity/google-workspace/scripts")

from .weather import get_weather
from .infra import get_infra_status
from .tasks import get_one_big_thing
from .gmail import get_gmail_inbox
from .calendar import get_calendar
from .habits import get_workspace_tasks, get_personal_and_habits, get_habits


def split_to_chunks(text: str, max_len: int) -> list[str]:
    """Разбить текст на чанки не больше max_len, сохраняя целостность строк"""
    if len(text) <= max_len:
        return [text]

    result = []
    lines = text.split('\n')
    current = ""

    for line in lines:
        # Если текущий чанк + новая строка переполняют — сбрасываем
        if len(current) + len(line) + 1 > max_len:
            if current:
                result.append(current)
            # Если одна строка сама по себе больше лимита — обрезаем
            if len(line) > max_len:
                line = line[:max_len - 50] + "\n... (обрезано)"
            current = line
        else:
            current = current + "\n" + line if current else line

    if current:
        result.append(current)

    return result


def format_brief_as_chunks(weather, infra, one_thing, inbox, calendar_str, workspace, personal_habits):
    """Форматировать бриф как список чанков (отдельные сообщения)"""
    now_msk = datetime.now(MSK)
    day_full = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    date_str = now_msk.strftime("%-d %B %Y")
    day_str = day_full[now_msk.weekday()]
    time_str = now_msk.strftime("%H:%M МСК")

    header = f"🌅 **Утренний бриф — {day_str}, {date_str}**\n\n━━━━━━━━━━━━━━━━━━━"

    chunks = [header]

    MAX_LEN = 2500  # Безопасный лимит для Telegram с Markdown

    # Блок 1: Статус системы + Погода (самые важные)
    chunk_system = f"⚡️ **Статус системы**\n{infra}\n\n🌦️ **Погода — Москва**\n{weather}\n\n🎯 **Главное на сегодня:** {one_thing}"
    chunks.extend(split_to_chunks(chunk_system, MAX_LEN))

    # Блок 2: Почта — заголовок уже есть в данных
    inbox_clean = simplify_links(inbox)
    if inbox_clean.strip():
        chunks.extend(split_to_chunks(inbox_clean, MAX_LEN))

    # Блок 3: Календарь — заголовок уже есть в данных
    cal_clean = simplify_links(calendar_str)
    if cal_clean.strip():
        chunks.extend(split_to_chunks(cal_clean, MAX_LEN))

    # Блок 4: Задачи + Личное + Привычки
    work_personal = f"{workspace}\n\n{personal_habits}"
    wp_clean = simplify_links(work_personal)
    if wp_clean.strip():
        chunks.extend(split_to_chunks(wp_clean, MAX_LEN))

    # Футер
    footer = f"\n_🕐 Сгенерировано: {time_str}_"
    chunks.append(footer)

    return chunks


def generate_brief():
    """Сгенерировать полный утренний бриф и отправить чанками"""
    # Погода
    weather = get_weather()

    # Инфраструктура
    infra = get_infra_status()

    # Задача дня
    one_thing = get_one_big_thing()

    # Почта
    inbox = get_gmail_inbox()

    # Календарь
    calendar_str = get_calendar()

    # Рабочие задачи
    workspace = get_workspace_tasks()

    # Личное и привычки
    personal_habits = get_personal_and_habits()

    # Форматировать как чанки
    chunks = format_brief_as_chunks(weather, infra, one_thing, inbox, calendar_str, workspace, personal_habits)

    # Собрать полный бриф для сохранения в файл
    full_brief = "\n\n".join(chunks)

    # Сохранить полную версию
    output_file = f"{HERMES_HOME}/cron/output/morning_brief.md"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(full_brief)

    print(f"✅ Полный бриф сохранён в: {output_file}")

    # Отправить в Telegram чанками
    send_brief_chunks(chunks)

    return full_brief


if __name__ == "__main__":
    print("🚀 Запуск утреннего брифа...")

    print("  🌦️ Погода...")
    weather = get_weather()

    print("  🖥️ Инфра...")
    infra = get_infra_status()

    print("  🎯 Главная задача...")
    one_thing = get_one_big_thing()

    print("  📧 Почта...")
    inbox = get_gmail_inbox()

    print("  📅 Календарь...")
    cal = get_calendar()

    print("  💻 Рабочие задачи...")
    workspace = get_workspace_tasks()

    print("  🏠 Личное и привычки...")
    personal_habits = get_personal_and_habits()

    full_brief = generate_brief()

    print("\n" + "=" * 50)
    print(full_brief)
    print("=" * 50)

    print(f"\n✅ Бриф сохранён в: {output_file}")
