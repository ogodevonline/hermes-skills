"""Календарь — события на сегодня через google_api.py"""
import json
import os
import subprocess
from datetime import datetime, timezone, timedelta

HERMES_HOME = os.path.expanduser("~/.hermes")
GOOGLE_WORKSPACE_SCRIPTS = f"{HERMES_HOME}/skills/productivity/google-workspace/scripts"
GOOGLE_SITE_PACKAGES = "/home/hermes/.local/lib/python3.12/site-packages"
MSK = timezone(timedelta(hours=3))


def _run_command(cmd, timeout=30):
    try:
        # PYTHONPATH prepended to cmd for proper module resolution
        full_cmd = f'PYTHONPATH={GOOGLE_SITE_PACKAGES}:{GOOGLE_WORKSPACE_SCRIPTS} {cmd}'
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout, executable='/bin/bash')
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return "", str(e)


def get_calendar():
    """Получить события календаря на сегодня"""
    try:
        today = datetime.now(MSK).strftime("%Y-%m-%d")
        cmd = f'cd {GOOGLE_WORKSPACE_SCRIPTS} && PYTHONPATH={GOOGLE_SITE_PACKAGES}:. /usr/bin/python3 google_api.py --account svaaugust calendar list --start {today}T00:00:00Z --end {today}T23:59:59Z'
        result, err = _run_command(cmd)
        
        if not result or err:
            return "📅 Нет событий на сегодня"

        events = json.loads(result)
        if not events:
            return "📅 Нет событий на сегодня"

        lines = ["📅 Календарь:"]
        for e in events[:5]:
            # start может быть str или dict
            start_val = e.get('start')
            if isinstance(start_val, str):
                start_dt = start_val
            elif isinstance(start_val, dict):
                start_dt = start_val.get('dateTime', start_val.get('date', ''))
            else:
                start_dt = ''
            if 'T' in start_dt:
                try:
                    dt = datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
                    time_str = dt.astimezone(MSK).strftime('%H:%M')
                except:
                    time_str = start_dt[-8:-3]
            else:
                time_str = "весь день"
            summary = e.get('summary', 'Без названия')[:45]
            html_link = e.get('htmlLink', '')
            if html_link:
                lines.append(f"  • 🕐 {time_str} — [{summary}]({html_link})")
            else:
                lines.append(f"  • 🕐 {time_str} — {summary}")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Ошибка календаря: {str(e)[:80]}"


if __name__ == "__main__":
    print(get_calendar())