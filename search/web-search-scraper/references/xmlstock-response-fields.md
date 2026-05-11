# XMLStock API Response Fields

XMLStock Yandex Live JSON API возвращает search-результаты с полями:

## Основные поля ответа

```
HTTP/1.1 200 OK
{
  "found": "13000000",
  "found-human": "нашлось 13000000 результатов",
  "date": "2026-05-10T15:28:11+03:00",
  "page": 0,
  "first": 1,
  "last": 10,
  "results": {
    "1": { ... item ... },
    "2": { ... item ... },
    ...
  },
  "query": "музеи москвы"
}
```

## Поля каждого результата (items)

| Поле | Тип | Описание |
|------|-----|----------|
| `url` | string | Полный URL страницы |
| `title` | string | Заголовок страницы (как в выдаче Яндекса) |
| `passage` | string | Сниппет/описание из выдачи Яндекса |
| `contenttype` | string | Тип контента: `organic` (обычный), `ads` (реклама) |
| `breadcrumbs` | string/null | Хлебные крошки (часто null) |
| `cachelink` | string | Ссылка на закешированную версию (yandexwebcache.net) |

## Ограничения

- API возвращает до 10 результатов на страницу
- `passage` — это не полный контент страницы, а выдержка Яндекса (1-2 предложения)
- Для полного контента нужен скрап страницы
- Время ответа: стабильно 5-7с (даже на простые запросы)
- Иногда отвечает 200 с пустым `results` если по запросу ничего нет

## Использование в web-search-scraper

`SearchResult` dataclass:
```python
@dataclass
class SearchResult:
    url: str        # из item["url"]
    title: str      # из item["title"]
    snippet: str    # из item["passage"]
```

`--preview` режим возвращает только эти поля, без скрапа.