---
name: news
category: productivity
description: Парсит Google News RSS и выводит топ-10 новостей за 24ч. Команда /news.
---

# News RSS

Парсит Google News RSS (русская версия), фильтрует за 24ч, выводит топ-10 новостей.

## Запуск

```bash
python3 ~/.hermes/skills/productivity/news-rss/scripts/news_rss.py
```

## Формат вывода

```
📰 Новости за 24ч:
1. Заголовок — Источник
2. Заголовок — Источник
...
```

## Требования

- `feedparser` (pip install feedparser)