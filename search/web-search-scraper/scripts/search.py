# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx",
#   "trafilatura",
#   "python-dotenv",
# ]
# ///

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from urllib.parse import urlparse

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

try:
    import trafilatura
except ImportError:
    trafilatura = None  # type: ignore

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("search")

# ── config ──────────────────────────────────────────────────────────

XMLSTOCK_USER = os.getenv("XMLSTOCK_USER", "")
XMLSTOCK_KEY = os.getenv("XMLSTOCK_KEY", "")
XMLSTOCK_XML_URL = "https://xmlstock.com/yandex/xml/"
XMLSTOCK_TIMEOUT = int(os.getenv("XMLSTOCK_TIMEOUT", "8"))
LR_DEFAULT = int(os.getenv("YANDEX_LR", "213"))  # Москва
DOMAIN_DEFAULT = os.getenv("YANDEX_DOMAIN", "ru")

BLOCKED_DOMAINS: set[str] = {
    "youtube.com", "youtu.be", "rutube.ru", "vk.com", "t.me", "telegram.org",
    "facebook.com", "instagram.com", "twitter.com", "pikabu.ru", "dzen.ru",
    "wikipedia.org", "maps.yandex.ru", "2gis.ru", "yandex.ru",
    "gosuslugi.ru", "mos.ru",
    "olx.uz", "olx.kz", "olx.ru", "avito.ru", "avito.uz",
    "market.yandex.ru", "wb.ru", "wildberries.ru", "ozon.ru",
}

_STRIP_BLOCKS = re.compile(
    r"<(script|style|svg|noscript)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE
)

_NS = {"y": "http://yandex.com/xmlsearch/2.0"}

# ── data ────────────────────────────────────────────────────────────

@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str


@dataclass
class PageResult:
    url: str
    title: str
    snippet: str = ""
    content: str = ""


# ── search (XMLStock XML POST) ──────────────────────────────────────

def _xml_request(query: str, page: int, lr: int, domain: str, sortby: str | None) -> tuple[str, dict[str, str]]:
    """Сформировать POST-запрос к XMLStock XML API."""
    body_parts = [f"""<?xml version="1.0" encoding="UTF-8"?>
<request>
  <query>{query}</query>
  <maxpassages>3</maxpassages>
  <page>{page}</page>
  <groupings>
    <groupby attr="d" mode="deep" groups-on-page="30" docs-in-group="1" />
  </groupings>"""]

    if sortby:
        body_parts.append(f'  <sortby order="descending">{sortby}</sortby>')

    body_parts.append("</request>")
    body = "\n".join(body_parts)

    params = {"user": XMLSTOCK_USER, "key": XMLSTOCK_KEY, "lr": str(lr), "domain": domain}
    return body, params


def _is_blocked(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return any(b in host for b in BLOCKED_DOMAINS)


def _strip_text(text: str | None, maxlen: int = 300) -> str:
    if not text:
        return ""
    # Убираем <hlword>-разметку из пассажей
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()[:maxlen]


def _parse_xml_response(xml: str) -> list[SearchResult]:
    """Парсим XML-ответ, извлекаем url + title + passages."""
    results: list[SearchResult] = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return results

    response = root.find("y:response", _NS)
    if response is None:
        response = root.find("response")
    if response is None:
        return results

    for group in response.iter("group"):
        doc = group.find("doc")
        if doc is None:
            continue

        url_el = doc.find("url")
        if url_el is None or not url_el.text:
            continue
        url = url_el.text.strip()
        if _is_blocked(url):
            continue

        title_el = doc.find("title")
        title = _strip_text(title_el.text if title_el is not None else "", 120)

        # Собираем passages
        passages_el = doc.find("passages")
        snippet = ""
        if passages_el is not None:
            passages = [_strip_text(p.text, 300) for p in passages_el.findall("passage")]
            snippet = " | ".join(p for p in passages if p)

        results.append(SearchResult(url=url, title=title, snippet=snippet))

    return results


async def _fetch_xml_page(
    client: httpx.AsyncClient, query: str, page: int,
    lr: int = LR_DEFAULT, sortby: str | None = None,
    domain: str = DOMAIN_DEFAULT,
) -> list[SearchResult]:
    body, params = _xml_request(query, page, lr, domain, sortby)
    try:
        resp = await client.post(
            XMLSTOCK_XML_URL,
            params=params,
            content=body.encode("utf-8"),
            headers={"Content-Type": "application/xml"},
            timeout=XMLSTOCK_TIMEOUT,
        )
        resp.raise_for_status()
        results = _parse_xml_response(resp.text)
        log.info("XML page %d: %d results", page + 1, len(results))
        return results
    except asyncio.CancelledError:
        return []
    except Exception as e:
        log.warning("XML page %d failed: %s", page + 1, e)
        return []


async def search(
    query: str, pages: int = 2,
    lr: int = LR_DEFAULT, sortby: str | None = None,
    domain: str = DOMAIN_DEFAULT,
) -> list[SearchResult]:
    """Search via XMLStock XML — конкурентно, с ранним выходом."""
    if not XMLSTOCK_USER or not XMLSTOCK_KEY:
        log.error("XMLSTOCK_USER/KEY not set")
        return []

    seen: set[str] = set()
    all_results: list[SearchResult] = []
    min_results = 20  # с XML-endpoint 30 результатов на страницу

    async with httpx.AsyncClient(trust_env=False) as client:
        tasks = [
            asyncio.create_task(
                _fetch_xml_page(client, query, p, lr=lr, sortby=sortby, domain=domain)
            )
            for p in range(pages)
        ]

        for i, task in enumerate(tasks):
            try:
                page = await task
            except asyncio.CancelledError:
                break
            for r in page:
                if r.url not in seen:
                    seen.add(r.url)
                    all_results.append(r)

            if len(all_results) >= min_results:
                for j, remaining in enumerate(tasks):
                    if j != i and not remaining.done():
                        remaining.cancel()
                log.info("Enough results (%d), cancelled remaining", len(all_results))
                break

    log.info("Total unique results: %d", len(all_results))
    return all_results


# ── scrape ─────────────────────────────────────────────────────────

async def _scrape_one(
    url: str,
    client: httpx.AsyncClient,
    timeout: float,
) -> PageResult | None:
    try:
        resp = await client.get(url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 429, 503):
            html = await _curl_cffi_fetch(url, timeout)
            if not html:
                return None
        else:
            return None
    except Exception:
        html = await _curl_cffi_fetch(url, timeout)
        if not html:
            return None

    html = _STRIP_BLOCKS.sub("", html)

    if trafilatura is None:
        return None

    bare = trafilatura.bare_extraction(
        html,
        include_comments=False,
        include_tables=False,
        output_format="python",
        favor_recall=True,
    )
    if not bare or not bare.text:
        return None

    text_lower = bare.text.lower()
    if any(p in text_lower for p in ["captcha", "access denied", "just a moment",
                                      "пройдите проверку", "доступ запрещён"]):
        return None

    content = bare.text[:2000].strip()
    if len(content) < 50:
        return None

    title = (bare.title or content[:80].strip()).strip()
    return PageResult(url=url, title=title, content=content)


async def _curl_cffi_fetch(url: str, timeout: float) -> str | None:
    try:
        from curl_cffi import requests as curl_req  # type: ignore
    except ImportError:
        return None
    try:
        async with curl_req.AsyncSession() as session:
            r = await session.request("GET", url, timeout=timeout, impersonate="chrome131")
            return r.text if r.status_code == 200 else None
    except Exception:
        return None


async def scrape(results: list[SearchResult], timeout: float = 4.0) -> list[PageResult]:
    sem = asyncio.Semaphore(10)

    async def _worker(r: SearchResult) -> PageResult | None:
        async with sem:
            async with httpx.AsyncClient(trust_env=False) as c:
                page = await _scrape_one(r.url, c, timeout)
                if page:
                    page.snippet = r.snippet
                    return page
                return PageResult(url=r.url, title=r.title, snippet=r.snippet, content="")

    tasks = [_worker(r) for r in results]
    pages = await asyncio.gather(*tasks)
    return [p for p in pages if p is not None]


# ── main ────────────────────────────────────────────────────────────

async def web_search(
    query: str, pages: int = 1, timeout: float = 4.0,
    scrape_content: bool = True,
    lr: int = LR_DEFAULT, sortby: str | None = None,
    domain: str = DOMAIN_DEFAULT,
) -> list[PageResult]:
    results = await search(query, pages=pages, lr=lr, sortby=sortby, domain=domain)
    if not results:
        return []
    if not scrape_content:
        return [PageResult(url=r.url, title=r.title, snippet=r.snippet) for r in results]
    return await scrape(results, timeout=timeout)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Web search + scrape to markdown")
    parser.add_argument("--query", "-q", required=True)
    parser.add_argument("--pages", type=int, default=1,
                        help="Страниц (дефолт 1 = 20 результатов)")
    parser.add_argument("--timeout", type=float, default=4.0)
    parser.add_argument("--preview", action="store_true",
                        help="Только сниппеты (без скрапа)")
    parser.add_argument("--lr", type=int, default=LR_DEFAULT,
                        help=f"Регион (дефолт {LR_DEFAULT}=Москва)")
    parser.add_argument("--no-region", action="store_true",
                        help="Поиск без привязки к региону")
    parser.add_argument("--sortby", choices=["rlv", "tm"], default=None,
                        help="Сортировка: rlv, tm")
    parser.add_argument("--domain", choices=["ru", "uz", "kz", "by", "com"],
                        default=DOMAIN_DEFAULT,
                        help=f"Домен (дефолт {DOMAIN_DEFAULT})")
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO)

    results = asyncio.run(
        web_search(
            args.query, args.pages, args.timeout,
            scrape_content=not args.preview,
            lr=args.lr if not args.no_region else 0,
            sortby=args.sortby, domain=args.domain,
        )
    )
    data = [asdict(r) for r in results]
    print(json.dumps(data, ensure_ascii=False, indent=2))
    log.info("Found %d pages", len(data))


if __name__ == "__main__":
    main()
