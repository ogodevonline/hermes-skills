---
name: aviasales-api
description: Поиск авиабилетов через бесплатный Aviasales Data API (Travelpayouts). Точные цены в RUB, прямые ссылки на покупку.
---

# Aviasales Data API

Бесплатный API для поиска цен на авиабилеты. Данные кэшированные (до 7 дней).

## Токен

Хранится в `$AVIA_API_TOKEN` (установлен в .env профиля).

## Основной эндпоинт

```
GET https://api.travelpayouts.com/aviasales/v3/prices_for_dates
  ?origin=MOW
  &destination=NCU
  &departure_at=2026-07-13
  &one_way=true
  &direct=true
  &currency=rub
  &token=$AVIA_API_TOKEN
```

**Параметры:**
- `origin` / `destination` — IATA коды городов
- `departure_at` — дата в формате YYYY-MM-DD
- `one_way` — true/false
- `direct` — true (только прямые) / false (все)
- `currency` — rub / usd / eur
- `limit` — макс результатов (до 1000)
- `sorting` — price / route

**Ответ:**
```json
{
  "success": true,
  "data": [{
    "flight_number": "9626",
    "airline": "HY",
    "price": 9886,
    "gate": "Uzbekistan airways",
    "transfers": 0,
    "duration": 210,
    "departure_at": "2026-07-13T09:30:00+03:00",
    "origin_airport": "VKO",
    "destination_airport": "NCU",
    "link": "/search/MOW1307NCU1?t=..."
  }],
  "currency": "rub"
}
```

## Календарь цен на месяц

```
GET https://api.travelpayouts.com/v2/prices/month-matrix
  ?origin=MOW&destination=NCU
  &month=2026-07-01
  &one_way=true&currency=rub&limit=31
  &token=$AVIA_API_TOKEN
```

Ответ — массив цен по дням с `depart_date`, `value`, `number_of_changes`, `gate`.

## Ссылка на покупку

Поле `link` из ответа — относительная. Полная ссылка:
```
https://www.aviasales.com/search/ + link
```

Или напрямую через Aviasales:
```
https://www.aviasales.ru/search/MOW{DD}{MM}NCU1
```
Где {DD}{MM} — дата: например 1307 = 13 июля.

## Ограничения

- Данные кэшируются до 7 дней — могут быть неактуальны
- Некоторые авиакомпании (Победа) могут отсутствовать в кэше на отдалённые даты
- Для точных цен на ближайшие даты лучше использовать `prices_for_dates`
- Для обзора месяца — `month-matrix`

## Альтернативы (если API не дал результатов)

1. **Яндекс.Расписания** — rasp.yandex.ru/plane/moscow--nukus — парсинг через web_extract
2. **Aviasales** — aviasales.ru/routes/mow/ncu — может быть JS, но web_extract иногда выдаёт текст
3. **UniTicket** — uniticket.ru/aviabilety/moscow/nukus/ — статичные страницы, хорошо парсятся
4. **flypobeda.ru** — официальный сайт Победы (JS-виджет)