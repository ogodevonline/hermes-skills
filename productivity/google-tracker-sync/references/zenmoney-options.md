# Готовые интеграции ZenMoney (поиск 21.09.2026)

Контекст: у Василия привычка «Подбить расходы в ZenMoney 18:30»; сам ZenMoney «не работает» (не выяснено, что именно: автоимпорт банков ≠ API). Если задача — ручной ввод/аналитика через чат Hermes, это закрывается MCP или своей обёрткой над `api.zenmoney.ru/v8`.

## MCP-серверы (все берут ZENMONEY_TOKEN с zerro.app/token)

| Репозиторий | Направление | Особенности |
|---|---|---|
| `sakost/zenmoney-mcp` (crates.io) | read+write+bulk | sync→локальная БД; create/update/delete transaction; prepare_bulk/execute_bulk; поиск uncategorized |
| `ekho/zenmoney-mcp` / `a-tarasoff/zenmoney-mcp` | read+write | npx -y zenmoney-mcp; add_expense/income/transfer, suggest_category |
| `nnslvp/zenmoney-mcp` | read-only | SQLite-кэш `~/.cache/zenmoney-mcp`; аналитика: net worth, тренды, подписки, долги, аномалии |
| `nonnname/zenmoney-mcp` | read-only | кэш только в памяти (приватнее), write-tools за флагом |
| `krislintigo-zenmoney/mcp` | read+write | create_transaction, cursor-пагинация, cache 5min |

## Подключение к Hermes

Существующий паттерн — `mcp_servers:` в `~/.hermes/config.yaml` (пример codegraph там же). Минимально:

```yaml
mcp_servers:
  zenmoney:
    command: npx
    args: ["-y", "zenmoney-mcp"]
    env: { ZENMONEY_TOKEN: "..." }   # токен в .env, не в config (secrets policy)
```

Node v22 + npx 10.9.7 на сервере есть (`~/.hermes/node/bin`).

## Решение по безопасности (НЕ принято, для продолжения)

Сторонний код с токеном ко ВСЕМ финансам. Варианты, в порядке надёжности:
1. Свой навык-обёртка над `/v8/diff/` (read) + transaction API (write) — зависимостей ноль, аудит не нужен
2. MCP с preliminary source-read (sakost — rust/binary hardest to audit; nonnname/nnslvp read-only наименее рискованны)

## Что НЕ решает ни один вариант

Автоимпорт транзакций из банков — фича мобильного приложения/официальных интеграций ZenMoney; API/MCP это ручной ввод и чтение. Если «не работает» = импорт из банка, сначала чинить подписку/оффлайн-синк в приложении.
