#!/usr/bin/env python3
"""Парсит Google News RSS и выводит топ-10 новостей за 24ч."""
import feedparser, re
from datetime import datetime, timezone, timedelta

RSS_URL = "https://news.google.com/rss?hl=ru-RU&gl=RU&ceid=RU:ru"

def clean_title(title):
    """Убирает суффикс ' - Источник' из заголовка Google News."""
    # Ищем последнее ' — ' или ' - '
    return re.sub(r'\s[—\-]\s[^—\-]+$', '', title).strip()

def main():
    feed = feedparser.parse(RSS_URL)
    if feed.bozo and not feed.entries:
        print("❌ Ошибка загрузки RSS")
        return

    # Фильтр за 24ч
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    news = []
    for entry in feed.entries:
        pub = entry.get('published_parsed')
        if pub:
            pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
            if pub_dt < cutoff:
                continue
        source = ''
        if hasattr(entry, 'source') and entry.source and hasattr(entry.source, 'title'):
            source = entry.source.title
        title = clean_title(entry.get('title', ''))
        if title:
            news.append((title, source))

    if not news:
        print("📰 Новостей за 24ч нет")
        return

    # Топ-10
    top = news[:10]
    print("📰 **Новости за 24ч:**")
    for i, (title, source) in enumerate(top, 1):
        src = f" — {source}" if source else ""
        print(f"{i}. {title}{src}")

if __name__ == '__main__':
    main()