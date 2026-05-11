# XMLStock XML POST API

## Endpoint

```
POST https://xmlstock.com/yandex/xml/
Params: user=<ID>&key=<KEY>&lr=<region>&domain=<zone>
Content-Type: application/xml
```

## Request body

```xml
<?xml version="1.0" encoding="UTF-8"?>
<request>
  <query>поисковый запрос</query>
  <maxpassages>3</maxpassages>
  <page>0</page>
  <sortby order="descending">rlv|tm</sortby>
  <groupings>
    <groupby attr="d" mode="deep" groups-on-page="30" docs-in-group="1" />
  </groupings>
</request>
```

## Параметры

| Параметр | Значение | Описание |
|----------|----------|----------|
| `groups-on-page` | 10-100 | Результатов на страницу. Для yandexlive/json — только 10. Для XML — до 100 |
| `maxpassages` | 1-5 | Пассажей в сниппете. 3 даёт хороший баланс |
| `attr="d"` | — | Группировка по доменам |
| `mode="deep"` | — | Глубокий режим (один домен — одна группа) |
| `sortby` | `rlv`/`tm` | По релевантности или времени |
| `page` | 0+ | Номер страницы (0-indexed) |
| `lr` | 213 (Москва) | ID региона. Список: https://yandex.cloud/ru/docs/search-api/reference/regions |
| `domain` | ru/uz/kz/by/com | Доменная зона Яндекса |

## Парсинг ответа

```python
import xml.etree.ElementTree as ET
_NS = {"y": "http://yandex.com/xmlsearch/2.0"}

root = ET.fromstring(xml_text)
response = root.find("y:response", _NS)

for group in response.iter("group"):
    doc = group.find("doc")
    url = doc.findtext("url")
    title = doc.findtext("title")     # может содержать <hlword>-теги
    passages = doc.find("passages")
    passage_texts = [p.text or "" for p in passages.findall("passage")]
    snippet = " | ".join(passage_texts)
```

## Поля ответа

| Поле | Описание |
|------|----------|
| `url` | Полный URL |
| `title` | Заголовок с `<hlword>` подсветкой |
| `domain` | Домен |
| `modtime` | Дата последнего изменения |
| `size` | Размер страницы |
| `mime-type` | Тип контента |
| `passages` | Сниппеты (до `maxpassages` шт.) |
| `extended-text` | Расширенный текст страницы (если есть) |

## Ограничения

- `yandexlive/json/` — только ТОП-10, не поддерживает `groupby`, `maxpassages`
- `yandex/xml/` — POST, XML-body, полный контроль, до 100 результатов
- XMLStock может отвечать 5-7 секунд — это внешний сервис, не ускорить
- `<hlword>` теги — убирать через `re.sub(r"<[^>]+>", "", text)` перед чтением