---
title: OLX.uz Парсинг через trafilatura
---

# OLX.uz — парсинг через trafilatura + httpx + BeautifulSoup

## Структура

OLX.uz — SPA на React (версия `rweb`), с SSR. Страница списка и детальная страница
отдают HTML с данными. JSON-LD (Schema.org) присутствует только на **детальной**
странице как `@type: Product`. На странице списка JSON-LD ItemList **отсутствует**
(проверено май 2026) — только HTML карточки.

Playwright/crawl4ai **не работают** — CloudFront блокирует headless браузеры.
Используйте httpx или trafilatura.

## Приоритет инструментов

1. **trafilatura** (лучший для детальных страниц) — чистит HTML, возвращает
   структурированный текст всех параметров
2. **httpx + BS4** (для страниц списка) — парсинг HTML карточек
3. **web_extract** — если trafilatura недоступен

## URL для домов в Нукусе

```
https://www.olx.uz/nedvizhimost/doma/prodazha/nukus/?page=N
```

Без фильтра по цене — фильтр в query params ненадёжен. Фильтровать в коде.

## Парсинг страницы списка (HTML карточки)

```python
import httpx, re
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
soup = BeautifulSoup(resp.text, "lxml")

listings = []
for card in soup.select('div[data-cy="l-card"]'):
    title_el = card.select_one('h4.css-hzlye5, h4[class*="hzlye5"]')
    title = title_el.get_text(strip=True) if title_el else ""
    
    price_el = card.select_one('p.css-blr5zl, p[class*="blr5zl"]')
    price_text = price_el.get_text(strip=True) if price_el else ""
    price_text = re.sub(r'(сум)\\s*$', '', price_text).strip()
    
    link = card.select_one('a.css-1bbgabe, a[class*="1bbgabe"]')
    url = link.get('href', '') if link else ""
    if url and not url.startswith('http'):
        url = 'https://www.olx.uz' + url
    
    listings.append({
        "url": url,
        "title": title,
        "price_text": price_text,
        "external_id": re.search(r"-ID([A-Za-z0-9]+)\\.html", url).group(1) if re.search(r"-ID([A-Za-z0-9]+)\\.html", url) else "",
    })
```

## Парсинг детальной страницы (trafilatura — предпочтительно)

```python
import httpx, trafilatura, json, re

def parse_detail(url):
    r = httpx.get(url, headers=headers, timeout=20, follow_redirects=True, verify=False)
    if r.status_code != 200:
        return {}
    
    parsed = trafilatura.extract(r.text, output_format='json', with_metadata=True)
    if not parsed:
        return {}
    
    data = json.loads(parsed)
    text = data.get('text', '')
    
    params = {}
    for line in text.split('\n'):
        if ':' in line and line.index(':') < 40:
            k, v = line.split(':', 1)
            params[k.strip()] = v.strip()
    
    area_raw = params.get('Общая площадь', '0')
    am = re.search(r'([\d.]+)', area_raw)
    area_num = float(am.group(1)) if am else 0
    rooms = int(params.get('Количество комнат', 0))
    area_sqm = int(area_num * 100) if area_num < 50 and rooms >= 2 else int(area_num)
    
    return {
        'rooms': rooms,
        'area_sqm': area_sqm,
        'wall': params.get('Тип строения', ''),
        'gas': 'Газ' in text,
        'water': 'Вода' in text,
        'cond': params.get('Состояние дома', ''),
        'phone': extract_phone(data.get('raw_text', text)),
        'date': parse_date(text),
    }
```

## Телефон

OLX маскирует телефон в HTML (`+998****3335`), полный номер может быть в описании:
```python
def extract_phone(raw_text):
    cleaned = raw_text.replace(' ', '').replace('\n', '')
    m = re.search(r'998(\d{9})', cleaned)
    return '+998' + m.group(1) if m else None
```

## Дата публикации

Внутри текста как "Опубликовано 30 апреля 2026 г.":
```python
def parse_date(raw_text):
    dtm = re.search(r'Опубликовано\s*(.+)$', raw_text, re.MULTILINE)
    return dtm.group(1).strip() if dtm else ''
```

## Площадь: нормализация соток

OLX пишет "Общая площадь: 6 м²" но это сотки:
- Если `area_num < 50` и `rooms >= 2` → *100
- Пример: "6 м²" + 2 комнаты = 600 м²
- Пример: "165 м²" + 4 комнаты = 165 м² (не трогать)