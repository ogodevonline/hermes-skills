# check-disk.sh — мониторинг заполнения диска

## Назначение
Скрипт для cron-задания `disk-check-reminder` (no_agent=True). Проверяет заполнение корневого раздела и выдаёт уведомление только если диск забит >75%.

## Где лежит
- Оригинал: `~/.hermes/skills/clean-disk/scripts/check-disk.sh`
- Копия для cron: `~/.hermes/scripts/check-disk.sh` (скопировать при настройке)

## Логика
| Заполнение | Вывод | Уведомление |
|-----------|-------|------------|
| >75% | `⚡ Диск забит на X% (свободно Y)` | ✅ приходит в Telegram |
| 60–75% | `💿 Диск на X% — пока норм (свободно Y)` | ✅ приходит в Telegram |
| <60% | (пусто) | ❌ тишина |

## Cron-конфигурация (no_agent=True)
```json
{
  "script": "check-disk.sh",
  "no_agent": true,
  "schedule": "0 19 * * 0",
  "deliver": "origin"
}
```

## Восстановление после сбоя
Если cron job упал с `Script not found`:
1. Проверить, что скрипт есть в `~/.hermes/scripts/check-disk.sh`
2. Если нет — скопировать из `~/.hermes/skills/clean-disk/scripts/check-disk.sh`
3. Убедиться, что `chmod +x`
4. Обновить путь в cronjob: `cronjob action=update job_id=... script=check-disk.sh`