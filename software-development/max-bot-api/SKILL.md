---
name: max-bot-api
category: software-development
description: Use when интеграция с MAX (max.ru) Bot API.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [max, max.ru, bot-api, geo-block, proxies]
    related_skills: [proxy-service, hermes-ops]
---

# MAX (max.ru) Bot API — интеграция

## When to Use — когда загружать

- «Сделай бота для MAX», «пересылай сообщения MAX ↔ Telegram», «запросы к max.ru не идут»
- Нужно понять, почему MAX недоступен с сервера и нужен ли прокси

## Гео: MAX режет зарубежные IP

VK/MAX закрывает доступ с иностранных адресов — и это **не 403 и не капча, а глухой сетевой блок**: TCP-соединение на :443 просто не устанавливается (таймаут).

Проверка с сервера, где будет работать бот (обязательно с контрольными сайтами в том же прогоне, иначе не отличить блок от своего сетевого сбоя):

```bash
timeout 8 bash -c '</dev/tcp/max.ru/443' && echo OPEN || echo BLOCKED
for u in https://max.ru/ https://platform-api2.max.ru/ https://yandex.ru/ https://api.telegram.org/; do
  printf "%-32s " "$u"
  curl -s -o /dev/null -w "http=%{http_code} t=%{time_total}s\n" --max-time 12 "$u"
done
```

Живые yandex.ru/api.telegram.org при таймауте на max.ru = нужен RU-exit IP. После покупки прокси (см. навык `proxy-service`) проверка такая:

```bash
curl -x http://LOGIN:PASS@HOST:PORT -s --max-time 15 "http://ip-api.com/json/?fields=country,isp,as"
curl -x http://LOGIN:PASS@HOST:PORT -s -o /dev/null -w "%{http_code}\n" --max-time 20 https://platform-api2.max.ru/me
```

Ожидаемый ответ на `/me` без токена — **401**: значит доступ есть и дело в токене, а не в сети. Таймаут — прокси не годится.

В коде прокси ставится только на вызовы MAX; Telegram (api.telegram.org) ходит напрямую с любого IP.

## База API и авторизация

- База — `https://platform-api2.max.ru` (миграция с `https://platform-api.max.ru`); примеры из старых статей содержат прежний адрес.
- Токен — в заголовке `Authorization: <token>` **без префикса Bearer**: с `Bearer` приходит 401 «No access token».
- Официальные SDK — TypeScript и Go; для Python есть сторонняя `maxapi`.

## Приём сообщений: webhook или polling

- **Webhook:** `POST /subscriptions`, только HTTPS на 443, самоподписанный сертификат не подходит. Бот **автоматически отписывается после 8 часов без успешного ответа** endpoint — молчащий бэкенд сам себя выключает.
- **Polling:** `GET /updates` — для ботов без публичного HTTPS. Входящий апдейт: `update_type: message_created`, адресат — `recipient.chat_id` (в личке `user_id`).
- Диагностика ответов: 401 — токен или способ его передачи; 404 — не тот chat/user id.

## Грабли

- **«Сайт не открывается — наверное ссылка мёртвая».** Для max.ru первый вопрос — не URL, а откуда запрос: с зарубежного IP не откроется ни сайт, ни API.
- **Датацентр-прокси подходит не всегда.** Для Bot API достаточно RU-exit, но если параллельно нужен скрапинг WB/Ozon/Avito — там блэклисты ASN хостеров (см. `proxy-service`), а это уже ISP/мобильные.
- **Не переноси шаблоны из Telegram-примеров:** `Authorization` без `Bearer` и авто-отписка через 8 часов — специфика MAX.
