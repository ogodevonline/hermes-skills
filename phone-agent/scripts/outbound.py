#!/usr/bin/env python3
"""Исходящий звонок: python outbound.py <номер> "<промпт для агента>"

Сервер (uvicorn phone_agent_server:app) должен быть запущен и доступен по PUBLIC_BASE_URL.
"""
import os
import sys
from urllib.parse import quote

from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    to = sys.argv[1]
    prompt = " ".join(sys.argv[2:])

    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = os.getenv("TWILIO_PHONE_NUMBER", "")
    base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    if not (sid and token and from_number and base):
        print("Ошибка: заполни TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
              "TWILIO_PHONE_NUMBER, PUBLIC_BASE_URL в .env")
        return 1

    client = Client(sid, token)
    webhook = f"{base}/voice?prompt={quote(prompt)}"
    call = client.calls.create(to=to, from_=from_number, url=webhook)
    print(f"Call SID: {call.sid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
