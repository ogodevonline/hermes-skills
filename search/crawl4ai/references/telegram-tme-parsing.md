# Telegram — парсинг публичных каналов через t.me/s/

## Принцип

Telegram предоставляет веб-версию каналов по адресу `https://t.me/s/<username>`.
Страница содержит все последние сообщения в виде HTML. Обычные HTTP запросы (httpx/requests)
проходят без блокировки (в отличие от Playwright/crawl4ai, который может блокироваться).

## Базовая реализация

```python
import httpx, re, asyncio, time
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

async def fetch(url, proxies=None):
    """GET with retry (3 attempts) on proxy/connection errors."""
    for i in range(1, 4):
        try:
            async with httpx.AsyncClient(
                headers=HEADERS, timeout=30, follow_redirects=True, verify=False
            ) as client:
                resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
        except (httpx.ProxyError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
            if i == 3:
                raise
            await asyncio.sleep(0.4 * i)
        except:
            raise
```

## Парсинг канала

```python
async def parse_channel(username: str) -> tuple[list[dict], dict | None]:
    """Parse t.me/s/<username> — returns (messages, channel_info)."""
    html = await fetch(f"https://t.me/s/{username}")
    soup = BeautifulSoup(html, "lxml")

    # --- Информация о канале ---
    info = None
    channel_info = soup.find("div", class_="tgme_channel_info")
    if channel_info:
        title = channel_info.find("div", class_="tgme_channel_info_header_title")
        desc = channel_info.find("div", class_="tgme_channel_info_description")
        info = {
            "title": title.get_text(strip=True) if title else "",
            "description": desc.get_text(strip=True) if desc else "",
        }

    # --- Сообщения ---
    messages = []
    for msg in soup.find_all("div", class_="tgme_widget_message"):
        post_id = msg.get("data-post")
        if not post_id:
            continue

        url = f"https://t.me/{post_id}"

        # Дата/время
        time_tag = msg.find("time")
        published = None
        if time_tag and time_tag.has_attr("datetime"):
            try:
                published = int(parse_date(time_tag["datetime"]).timestamp())
            except:
                pass

        # Просмотры
        views_span = msg.find("span", class_="tgme_widget_message_views")
        views = None
        if views_span:
            text = views_span.get_text(strip=True)
            if text:
                # "12.3K" → 12300
                views = parse_counter(text)

        # Текст сообщения
        text_el = msg.find("div", class_="tgme_widget_message_text")
        text = ""
        if text_el:
            for br in text_el.find_all("br"):
                br.replace_with("\n")
            text = text_el.get_text(separator="", strip=False)
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text)

        # Медиа
        media = []
        for pw in msg.find_all("a", class_="tgme_widget_message_photo_wrap"):
            style = pw.get("style", "")
            m = re.search(r"url\('(.*?)'\)", str(style))
            if m:
                media.append(m.group(1))

        # Ссылки на другие каналы в тексте
        related = []
        if text_el:
            for a in text_el.find_all("a", href=True):
                href = a["href"]
                if href.startswith("https://t.me/") and "+" not in href:
                    uname = href.replace("https://t.me/", "").split("/")[0]
                    if uname.lower() != username.lower():
                        related.append(uname)

        messages.append({
            "url": url,
            "text": text.strip(),
            "published_ts": published or int(time.time()),
            "views": views,
            "media": media or None,
            "related": related or None,
        })

    return messages, info
```

## Парсинг чисел (просмотры, подписчики)

```python
def parse_counter(text: str) -> int:
    """'12.3K' → 12300, '1.5M' → 1500000, '1234' → 1234"""
    text = text.strip().replace(" ", "")
    if not text:
        return 0
    multipliers = {"K": 1000, "M": 1000000, "B": 1000000000}
    suffix = text[-1].upper()
    if suffix in multipliers:
        return int(float(text[:-1]) * multipliers[suffix])
    return int(re.sub(r"\D", "", text) or 0)
```

## Проверенные каналы (Нукус, дома)

| Канал | Описание |
|-------|----------|
| @Nukus / @Nukus_Uj | «Нукус уй жай» — основной |
| @uy_satiladi | «УЙ ЖАЙ САТЫЛАДЫ НУКУС БАЗАР» |
| @uy_jay_nukus | «УЙ ЖАЙ Базары» |
| @Nokis_uy_jay | «Уй сатылады Жай сатылады Нукус» |
| @uyjaysatiladi007 | «Нукус уй жай сатылады 24/7» |
| @Bazar_nks | «Нукус Базар Уй жай» |
| @cheaphouses1 | Из Instagram |
| @SarvarService | Из Instagram |

## Ограничения

- `t.me/s/` показывает только последние ~20-50 сообщений (не всю историю)
- Медиа выдаётся в виде превью (ссылка на картинку), не исходник
- Если канал приватный — `t.me/s/` не работает
- Сообщения идут от новых к старым
- Чем больше каналов парсить за раз — тем дольше (каждый ~0.5-1 сек)
