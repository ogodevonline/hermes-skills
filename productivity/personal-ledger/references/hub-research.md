# Готовые решения учёта финансов — исследование 21.09.2026

## Вывод

Идея «учёт через чат вместо ZenMoney» не требует изобретения: в хабе Hermes (ClawHub) есть ~8 навыков личного учёта. Ни один не покрывает Russian-bank PDF выписки из коробки — но каркас (SQLite ledger + категории + бюджеты + NL-запросы) готов, адаптировать дешевле, чем писать.

## Кандидаты из индекса хаба (`~/.hermes/skills/.hub/index-cache/hermes-index.json`, trust_level community!)

| Identifier | Что | Вердикт |
|---|---|---|
| `financial-reconciler` | Privacy-first локальный SQLite: импорт CSV/OFX/QFX выписок, автокатегоризация, бюджеты, NL-запросы, отчёты. Зависимости pandas/ofxparse/tabulate | 🥇 кандидат. Минус: форматы — US-банки (Chase/BoA в onboarding-тексте), Сбер PDF нужен свой адаптер-конвертер |
| `spotsccc-finance` | Кошельки/категории/отчёты — но через CLI своего PostgreSQL-сервиса | ✖ лишняя инфраструктура |
| `beancount`, `beancount-skill` | Plain-text бухгалтерия + веб-отчёты Fava (графики!) | Мощно, графики из коробки; тяжёлый формат. Запасной путь |
| `openclaw-skill-personal-finance` | Парсинг CSV-экспортов + локальные правила категорий | Похож на Reconciler, мельче |
| `personal-finance-hardened`, `afrexai-personal-finance`, `smart ledger` (кит.) | Бюджеты/EMI/NL-бухгалтер JSON | Не срослось |

Ставка только после чтения кода всего навыка: `hermes skills inspect "<display-name>"` (identifier из индекса может не резолвиться — брать display name из подсказки «Did you mean»). Финансовые данные + community-код = обязательный аудит перед доверием.

## ZenMoney MCP (отвергнуто направлением пользователя)

6+ серверов на GitHub (ekho/sakost read-write, nnslvp read-only аналитика, roher/nonnname, krislintigo), токен zerro.app/token, api.zenmoney.ru/v8. Не нужны: проблема была в мёртвых автоимпортах Сбера + неудобном ручном вводе — чат-ввод решает и то, и другое без стороннего кода с токеном на весь кошелёк.

## Что строить сверху

1. `ledger.sqlite`: transactions (date/amount/category/payee/account, UNIQUE-хэш для дедупа при повторном импорте той же выписки), budgets, merchant_rules (самообучение категорий).
2. Парсер → см. sber-pdf-format.md (баги 1–3 починить, сверка с ИТОГО обязательна).
3. Gmail-cron: Сбер выписки на почту → распарсить → импортировать (gmail уже подключён через google-workspace, аккаунт svaaugust).
4. Графики matplotlib (venv ~/.hermes/venvs/ledger) → PNG в Telegram: круговая по месяцам, линия по дням, прогресс бюджетов; сводку — в вечерний бриф.
