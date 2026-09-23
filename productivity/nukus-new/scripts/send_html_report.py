#!/usr/bin/env python3
"""Send nukus_report.html to Telegram as a document via python-telegram-bot.
MEDIA: doesn't support .html — this is the working workaround."""
import asyncio, os
from telegram import Bot

token = None
with open(os.path.expanduser("~/.hermes/.env")) as f:
    for line in f:
        s = line.strip()
        if s.startswith("TELEGRAM_BOT_TOKEN=") and not s.startswith("#"):
            token = s.split("=", 1)[1].strip()
            break
if not token:
    print("ERROR: token not found")
    exit(1)

chat_id = "350262645"
path = "/home/hermes/.hermes/cache/documents/nukus_report.html"

async def main():
    b = Bot(token=token)
    with open(path, "rb") as f:
        msg = await b.send_document(chat_id=chat_id, document=f, filename="nukus_report.html")
    print(f"OK msg_id={msg.message_id}")

asyncio.run(main())
