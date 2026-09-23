---
name: trends
category: productivity
description: Показывает топ-10 репозиториев GitHub за неделю. Команда /trends.
---

# GitHub Trends

Запрашивает GitHub Search API (created за неделю, сортировка по звёздам).

## Запуск

```bash
python3 ~/.hermes/skills/productivity/github-trends/scripts/github_trends.py
```

## Формат вывода

```
🔥 GitHub тренды за неделю:
1. owner/repo — описание ⭐N
2. owner/repo — описание ⭐N
...
```