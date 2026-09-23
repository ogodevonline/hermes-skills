---
name: hermes-book
category: productivity
description: Universal book context loader + updater. Работает с любыми книгами (fiction book.yaml / diary meta.yaml). Загружает сессии с tiered compression, обновляет summary/character_sheets/plot_threads.
---

# hermes-book — Universal Book Tool

Скрипт: `~/.hermes/scripts/hermes_book.py`

Универсальная замена `english_context.py` — работает с **любой книгой**, а не только в `Английский/`.

## Команды

### context — загрузить контекст с tiered compression
```bash
# Последние 10 сессий (по умолчанию)
hermes-book context /путь/к/книге

# С компрессией (если > 10К символов)
hermes-book context /путь/к/книге --compress

# N сессий + JSON
hermes-book context /путь/к/книге --count 15 --compress --json
```

### status — показать статус книги
```bash
hermes-book status /путь/к/книге
```

### update — обновить метаданные
```bash
hermes-book update /путь/к/книге summary --text "Новый сюжет..."
hermes-book update /путь/к/книге summary --file /tmp/summary.txt
hermes-book update /путь/к/книге chars --file /tmp/character_sheets.yaml
hermes-book update /путь/к/книге threads --file /tmp/plot_threads.yaml
```

## Поддержка типов книг

| Тип | Файл | Откуда берутся персонажи |
|-----|------|------------------------|
| `fiction` | `book.yaml` | `character_sheets` (keys) или `characters[].name` |
| `diary` | `meta.yaml` | Нет персонажей — другой формат |

## Tiered Compression

Флаг `--compress` включает трехуровневое сжатие, если общий размер > порога (10K по умолчанию):

| Слой | Сессии | Формат |
|------|--------|--------|
| **Consolidation** | Последние 2 | Полный текст |
| **Summarization** | 3-5 от конца | Ключевые события + клиффхэнгер |
| **Distillation** | 6+ от конца | Локация + откровения + клиффхэнгер |

Персонажи определяются **динамически** из `character_sheets` книги — не хардкодятся.