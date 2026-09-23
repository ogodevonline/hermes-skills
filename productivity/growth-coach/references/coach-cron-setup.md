# Coach Cron Setup

## Cron job: Daily Coach Check
- job_id: `4f7eab9f12ef`
- Расписание: `0 18 * * *` (21:00 МСК)
- Профиль: `coach`
- Модель: `deepseek-chat` через провайдер `deepseek`
- Навыки: `growth-coach`
- Доставка: `telegram:350262645`

## Cron job: Weekly Coach Deep Dive
- job_id: `1382d6359344`
- Расписание: `30 5 * * 0` (08:30 МСК воскресенье)
- Профиль: `orchestrator`
- Модель: `deepseek/deepseek-v4-flash` через провайдер `kilocode`
- Навыки: `kanban-orchestrator`, `growth-coach`
- Доставка: `telegram:350262645`

## Настройка профиля coach
1. `mkdir -p ~/.hermes/profiles/coach/skills`
2. Править `config.yaml`: toolsets, модель, display.personality=coach
3. Написать `SOUL.md`
4. Симлинки навыков: `ln -sf ~/.hermes/skills/productivity/growth-coach ~/.hermes/profiles/coach/skills/growth-coach`
5. Скопировать .env: `cp ~/.hermes/.env ~/.hermes/profiles/coach/.env`
6. Проверка: `hermes -p coach chat -q "Тест"`

## Диагностика
| Проблема | Решение |
|----------|---------|
| `Error: Unknown skill(s): growth-coach` | Symlink skills: `ln -sf ...` |
| `HTTP 401: Authentication Fails` | .env не скопирован в профиль coach |
| Пустой вывод/log | Проверить ~/.hermes/profiles/coach/logs/agent.log (пусто = не стартовал) |
| Старая модель | Проверить `cronjob list` — model-override может быть устаревшим |
