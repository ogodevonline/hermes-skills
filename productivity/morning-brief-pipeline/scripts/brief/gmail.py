"""Gmail — почта через google_api.py"""
import json
import os
import subprocess

HERMES_HOME = os.path.expanduser("~/.hermes")
GOOGLE_WORKSPACE_SCRIPTS = f"{HERMES_HOME}/skills/productivity/google-workspace/scripts"
# Добавляем пути для google-api-python-client
GOOGLE_SITE_PACKAGES = "/home/hermes/.local/lib/python3.12/site-packages"


def _run_command(cmd, timeout=30):
    try:
        # Используем shell=True, cmd уже содержит cd && ...
        full_cmd = f'PYTHONPATH={GOOGLE_SITE_PACKAGES}:{GOOGLE_WORKSPACE_SCRIPTS} {cmd}'
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout, executable='/bin/bash')
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return "", str(e)


def get_gmail_inbox():
    """Получить непрочитанные письма"""
    try:
        # Вызов через system python с правильным PYTHONPATH
        cmd = f'cd {GOOGLE_WORKSPACE_SCRIPTS} && PYTHONPATH={GOOGLE_SITE_PACKAGES}:. /usr/bin/python3 google_api.py --account svaaugust gmail search "is:unread" --max 7'
        result, err = _run_command(cmd)
        
        if not result or err:
            return f"📭 Нет непрочитанных писем"

        emails = json.loads(result)
        if not emails:
            return "📭 Нет непрочитанных писем"

        lines = [f"📧 Почта — {len(emails)} непрочитанных:"]
        for e in emails[:7]:
            subject = (e.get('subject') or 'Без темы')[:50]
            sender = (e.get('from') or '?').split('<')[0].strip()[:25]
            msg_id = e.get('id', '')
            # Прямая ссылка на конкретное письмо (открывает его в просмотре)
            url = f"https://mail.google.com/mail/u/0/?view=pt&message_id={msg_id}" if msg_id else ""
            if url:
                lines.append(f"  • {sender} — [{subject}]({url})")
            else:
                lines.append(f"  • {sender} — {subject}")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Ошибка почты: {str(e)[:80]}"


if __name__ == "__main__":
    print(get_gmail_inbox())