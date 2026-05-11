# /// script
# requires-python = ">=3.11"
# dependencies = ["crawl4ai"]
# ///

"""
Crawl4AI — Deep site scraper with pagination + listing extraction.

Crawls a starting URL, extracts all content, then follows
"next page" links (up to --max-pages). Automatically extracts
structured listings {title, price, url} from classified sites.

Usage:
  uv run python crawl.py --url "https://www.olx.uz/doma/nukus/"
  uv run python crawl.py --url "https://..." --max-pages 5
  uv run python crawl.py --url "https://..." --output results.md
"""

import asyncio
import json
import re
import sys
from urllib.parse import urljoin, urlparse, parse_qs
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode


# Known classified URL patterns for listing extraction
LISTING_PATTERNS = [
    r"/d/obyavlenie/",   # OLX
    r"/obyavlenie/",     # OLX alt
    r"/announce/",       # OLX english
    r"/item/",           # Avito
    r"/a/",              # Kufar / others
    r"/product/",        # Common marketplaces
    r"/p/",              # Aliexpress-style
    r"/ad/",             # Generic
]


def find_listing_urls(links: dict | None) -> list[dict]:
    """Extract listing URLs from crawl4ai link data.

    Returns list of {href, text} for links matching known listing patterns.
    """
    if not links:
        return []

    listings = []
    seen = set()
    internal = links.get("internal", [])
    for link in internal:
        href = link.get("href", "")
        for pat in LISTING_PATTERNS:
            if pat in href and href not in seen:
                seen.add(href)
                listings.append({
                    "url": href,
                    "text": link.get("text", "").strip(),
                })
                break
    return listings


def parse_listing_prices(content: str, listings: list[dict]) -> list[dict]:
    """Match listing URLs with their titles and prices from markdown content.

    OLX format in markdown:
      #### [Title](url)
      price сум

    Returns enriched listings: {title, price, url}
    """
    # Extract all title+url pairs from markdown: #### [text](url)
    title_map = {}
    for m in re.finditer(r'#### \[([^\]]+)\]\(([^)]+)\)', content):
        title_map[m.group(2)] = m.group(1).strip()

    # Extract all prices: lines with "сум" containing digits
    price_lines = []
    for line in content.split("\n"):
        line = line.strip()
        if "сум" in line and re.search(r"\d", line):
            # Clean price: "1 500 000 000 сумДоговорная" -> "1 500 000 000 сум"
            price = re.sub(rf"(сум).*$", r"\1", line)
            price_lines.append(price)

    # Match listings with their prices by position
    result = []
    for listing in listings:
        url = listing["url"]
        title = title_map.get(url, listing["text"] or url.split("/")[-1])
        # Find closest price in content before/around this listing's position
        price = ""
        idx = content.find(url)
        if idx >= 0:
            # Look for nearest price after this listing in content
            after = content[idx:idx+500]
            pm = re.search(r"(\d[\d\s]*\d\s*(?:сум|USD|\$|₽))", after)
            if pm:
                price = pm.group(1).strip()

        result.append({
            "title": title,
            "price": price,
            "url": url,
        })

    return result


def find_pagination_links(url: str, links: dict | None, max_pages: int) -> list[str]:
    """Find pagination URLs from the crawled page links."""
    if not links:
        return []

    page_nums: set[int] = set()
    base = url.rstrip("/")

    parsed = urlparse(base)
    current_page = int(parse_qs(parsed.query).get("page", [1])[0])

    internal = links.get("internal", [])
    for link in internal:
        href = link.get("href", "")
        m = re.search(r"[?&]page=(\d+)", href)
        if not m:
            m = re.search(r"/page/(\d+)", href)
        if m:
            p = int(m.group(1))
            if p > current_page and p - current_page < max_pages * 3:
                page_nums.add(p)

    sorted_pages = sorted(page_nums)[: max_pages - 1]
    if not sorted_pages:
        return []

    results = []
    for p in sorted_pages:
        if "?" in base:
            new_url = re.sub(r"page=\d+", f"page={p}", base)
        else:
            sep = "&" if "?" in base else "?"
            new_url = f"{base}{sep}page={p}"
        results.append(new_url)

    return results


async def crawl_pages(
    start_url: str,
    max_pages: int = 3,
    page_timeout: int = 30000,
    max_chars: int = 30000,
    verbose: bool = True,
) -> dict:
    """Crawl a site with pagination support.

    Returns:
      dict with:
        - listings: [{title, price, url}] — all listings across pages
        - pages: [{url, title, content, length, page_number}]
        - total_pages, total_listings, total_chars
    """
    all_listings: list[dict] = []
    pages_data = []
    visited_urls = set()
    seen_listing_urls = set()

    config = CrawlerRunConfig(
        word_count_threshold=3,
        cache_mode=CacheMode.BYPASS,
        verbose=False,
        screenshot=False,
        pdf=False,
        page_timeout=page_timeout,
        wait_until="domcontentloaded",
        delay_before_return_html=0.1,
        magic=True,
        remove_consent_popups=True,
        exclude_social_media_links=True,
        exclude_external_links=True,
    )

    async with AsyncWebCrawler(verbose=verbose) as crawler:
        urls_to_crawl = [start_url]
        page_num = 0

        while urls_to_crawl and len(pages_data) < max_pages:
            url = urls_to_crawl.pop(0)
            normalized = url.rstrip("/")
            if normalized in visited_urls:
                continue
            visited_urls.add(normalized)
            page_num += 1

            if verbose:
                print(f"[page {page_num}] {url}")

            result = await crawler.arun(url=url, config=config)
            content = (result.markdown or "")[:max_chars]
            title = (
                result.metadata.get("title", "")
                if result.metadata else ""
            )

            pages_data.append({
                "url": url,
                "title": title,
                "content": content,
                "length": len(content),
                "page_number": page_num,
            })

            # Extract listings from this page
            listing_urls = find_listing_urls(result.links)
            page_listings = parse_listing_prices(content, listing_urls)
            for lst in page_listings:
                if lst["url"] not in seen_listing_urls:
                    seen_listing_urls.add(lst["url"])
                    all_listings.append(lst)

            # Find next page if needed
            if len(pages_data) < max_pages:
                next_urls = find_pagination_links(url, result.links, max_pages)
                for nu in next_urls:
                    if nu.rstrip("/") not in visited_urls:
                        urls_to_crawl.append(nu)

    return {
        "listings": all_listings,
        "total_listings": len(all_listings),
        "pages": pages_data,
        "total_pages": len(pages_data),
        "total_chars": sum(p["length"] for p in pages_data),
    }


def print_listings_table(listings: list[dict]):
    """Print a clean table of listings with clickable links."""
    print(f"\n{'='*70}")
    print(f"  Всего объявлений: {len(listings)}")
    print(f"{'='*70}")
    for i, lst in enumerate(listings, 1):
        price = lst["price"] if lst["price"] else "—"
        title = lst["title"][:60] if lst["title"] else "(без названия)"
        print(f"\n  {i}. {title}")
        print(f"     💰 {price}")
        print(f"     🔗 {lst['url']}")
    print(f"\n{'='*70}")
    print(f"  Всего: {len(listings)} объявлений")
    print(f"{'='*70}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Crawl a site with pagination support"
    )
    parser.add_argument("--url", required=True, help="Starting URL")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help="Max pages to crawl (default: 3)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30000,
        help="Page timeout in ms (default: 30000)",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=30000,
        help="Max chars per page (default: 30000)",
    )
    parser.add_argument(
        "--output",
        help="Save as markdown to file",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="No verbose output",
    )
    parser.add_argument(
        "--links-only",
        action="store_true",
        help="Only output listing titles + prices + URLs, no full content",
    )
    args = parser.parse_args()

    data = asyncio.run(
        crawl_pages(
            start_url=args.url,
            max_pages=args.max_pages,
            page_timeout=args.timeout,
            max_chars=args.max_chars,
            verbose=not args.quiet,
        )
    )

    if args.output:
        with open(args.output, "w") as f:
            for page in data["pages"]:
                f.write(f"# {page['title']}\n\n")
                f.write(f"URL: {page['url']}\n\n")
                f.write(page["content"])
                f.write("\n\n---\n\n")
        print(
            f"Saved {data['total_chars']} chars from "
            f"{data['total_pages']} pages to {args.output}"
        )

    elif args.links_only:
        print(json.dumps({
            "listings": data["listings"],
            "total_listings": data["total_listings"],
            "total_pages": data["total_pages"],
        }, ensure_ascii=False, indent=2))

    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()