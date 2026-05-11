---
name: clean-disk
title: clean-disk
description: Очистка диска от мусора — кэши, логи, старые сессии, браузеры дубликаты
---

# Clean Disk

Очищает диск от мусора: кэши пакетных менеджеров, старые сессии Hermes, браузерные бинарники, системные логи.

## Запуск

### Базовый (без sudo) — через скрипт
```bash
bash ~/.hermes/skills/clean-disk/scripts/clean-disk.sh
```
Чистит: uv, npm, pip кэши, ~/.npm-local, сессии Hermes старше 7 дней, ms-playwright/camoufox/huggingface.

### Полный (с sudo)
```bash
sudo journalctl --vacuum-time=7d
sudo apt clean
```
Только если настроен sudo без пароля. Иначе руками.

## Cron

Два cron-задания (оба `no_agent=True`, т.е. скрипты выполняются напрямую, без LLM):

### 1. `clean-disk.sh` — фактическая чистка
- Расписание: воскресенье 22:00 МСК
- Скрипт лежит в `~/.hermes/skills/clean-disk/scripts/clean-disk.sh`
- Запускается через cron job (с LLM), не `no_agent`

### 2. `check-disk.sh` — проверка заполнения диска
- Расписание: воскресенье 19:00 МСК
- `no_agent=True` — скрипт сам решает, писать ли в stdout
- Если диск >75% — приходит уведомление в Telegram
- Если 60-75% — тихое предупреждение
- Если <60% — полная тишина (пустой stdout = без уведомления)

**Важно:** для `no_agent=True` скрипт ОБЯЗАН лежать внутри `~/.hermes/scripts/`. Путь задаётся относительно этой директории. Абсолютные пути не принимаются API cronjob. При добавлении/обновлении такого задания скопируй скрипт в `~/.hermes/scripts/` и укажи просто имя файла.

## Что чистит

| Что | Команда | Требует sudo |
|---|---|---|
| uv cache | `uv cache clean` | нет |
| npm cache | `npm cache clean --force` | нет |
| npm-local (_npx) | `rm -rf ~/.npm-local` | нет |
| pip cache | `rm -rf ~/.cache/pip` | нет |
| huggingface | `rm -rf ~/.cache/huggingface` | нет |
| ms-playwright | `rm -rf ~/.cache/ms-playwright` | нет |
| camoufox | `rm -rf ~/.cache/camoufox` | нет |
| Сессии Hermes >7d | по дате в имени файла | нет |
| journalctl >7d | `journalctl --vacuum-time=7d` | **да** |
| apt cache | `apt clean` | **да** |

## Когда запускать
- Раз в неделю (воскресенье) — базовый через cron
- Раз в месяц — полный (руками с sudo)

## Pitfalls
1. **no_agent cron jobs** — скрипт должен лежать в `~/.hermes/scripts/`, а не в `~/.hermes/skills/`. Для no_agent=True путь разрешается относительно `~/.hermes/scripts/`. Абсолютные пути не принимаются.
2. **Симлинки не использовать** — cron не будет ждать, пока ты создашь симлинк из scripts/ в skills/. Просто копируй скрипт.
3. **check-disk.sh** — должен быть в `~/.hermes/scripts/check-disk.sh`, не в `~/.hermes/skills/devops/clean-disk/scripts/check-disk.sh`

### Симлинки в `~/.hermes/scripts/` — не ок
Не создавай симлинк из `~/.hermes/scripts/` на скрипт из скилла. Cron job выполняется в контексте демона, и симлинк может сломаться при перезапуске или реорганизации. Вместо этого скопируй скрипт напрямую и обнови путь в cronjob.

### no_agent=True: скрипт должен быть в ~/.hermes/scripts/
При `script` параметре в cronjob, если `no_agent=True`, относительный путь разрешается относительно `~/.hermes/scripts/`. Абсолютные пути rejected. Перемести/скопируй скрипт туда, а не в `.skills/`.

### Пустой stdout = тишина
`check-disk.sh` использует пустой stdout как сигнал «всё ок, ничего не отправлять». Если скрипт ничего не вывел — уведомления не будет. Это штатное поведение для no_agent=False по умолчанию (если бы там был LLM-агент, пустой контекст тоже не вызвал бы сообщения).
