#!/usr/bin/env python3
"""Diagnose a parser: fetch one search page, dump all items with prices.

When a user says "parser broken / хреново парсит", run this FIRST.
Isolates parser issues from config/filter issues (budget_max_sum, etc.).

Usage:
    python3 diagnose_parser.py <search_url> [--price-filter N]

Example:
    python3 diagnose_parser.py "https://www.olx.uz/nedvizhimost/doma/nukus/?page=1" --price-filter 300000000
"""

import argparse
import asyncio
import re
import sys

import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US,en;q=0.5",
}

CARD_SELECTOR = 'div[data-cy="l-card"]'
TITLE_SELECTOR = 'h4.css-hzlye5, h4[class*="hzlye5"]'
PRICE_SELECTOR = 'p.css-blr5zl, p[class*="blr5zl"]'


def normalize_price(text: str) -> int | None:
    """Parse '200 000 000 сумДоговорная' → 200000000."""
    if not text or not text.strip():
        return None
    text = text.strip()
    text = re.sub(r"(?i)\bсум\b|\bдоговорная\b|\bdogovornaya\b|\b$\b", "", text).strip()
    digits = re.sub(r"[^\d\s]", "", text).strip()
    if not digits:
        return None
    try:
        return int(digits.replace(" ", ""))
    except ValueError:
        return None


async def main():
    parser = argparse.ArgumentParser(description="Diagnose a classifieds parser")
    parser.add_argument("url", help="Search page URL (e.g. OLX page 1)")
    parser.add_argument("--price-filter", type=int, default=None,
                        help="Budget max (e.g. 300000000) — items above get ⚠️ marker")
    args = parser.parse_args()

    async with httpx.AsyncClient(
        headers=HEADERS, timeout=30, follow_redirects=True, verify=False
    ) as client:
        resp = await client.get(args.url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "lxml")
    cards = soup.select(CARD_SELECTOR)
    print(f"Найдено карточек: {len(cards)}")
    print()

    above = 0
    total = 0

    for i, card in enumerate(cards, 1):
        title_el = card.select_one(TITLE_SELECTOR)
        price_el = card.select_one(PRICE_SELECTOR)
        link_el = card.select_one("a[href]")

        title = title_el.get_text(strip=True) if title_el else "N/A"
        price_text = price_el.get_text(strip=True) if price_el else "N/A"
        href = link_el.get("href", "N/A") if link_el else "N/A"
        if href.startswith("/"):
            href = f"https://www.olx.uz{href}"

        price = normalize_price(price_text)

        marker = ""
        if price is not None:
            total += 1
            if args.price_filter and price > args.price_filter:
                marker = " ⚠️ ВЫШЕ ЛИМИТА!"
                above += 1
            elif price is not None and price > 0:
                pass  # normal

        ext_id = ""
        m = re.search(r"-ID([A-Za-z0-9]+)\.html", href)
        if m:
            ext_id = m.group(1)

        print(f"[{i:2d}] {title[:50]}")
        print(f"      Цена: {price_text:25s} → {price:>12,} сум{marker}")
        print(f"      ID: {ext_id}  |  {href[:80]}")
        print()

    print(f"Всего с ценой: {total}")
    if args.price_filter:
        print(f"Из них выше {args.price_filter:,}: {above}")
        if total > 0 and above == 0:
            print("→ Ни одно объявление не превышает лимит. Проблема не в фильтре.")
        elif above > 0:
            print(f"→ {above}/{total} объявлений отсекаются фильтром!")


if __name__ == "__main__":
    asyncio.run(main())