"""Новости — HN, Tech, World, Russia, GitHub"""
import json
import subprocess
import re
import xml.etree.ElementTree as ET


def _run_command(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return "", str(e)


def summarize_text(text, max_len=120):
    """Обрезать до первого предложения или max_len символов"""
    if not text:
        return ""
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    for sep in ['. ', '! ', '? ', '\n']:
        idx = text.find(sep)
        if 0 < idx < max_len:
            return text[:idx + 1]
    return text[:max_len] + ("…" if len(text) > max_len else "")


def fetch_rss_items(url, max_items=5, timeout=15):
    """Fetch и парсинг RSS/Atom feed, вернуть список (title, link, summary)"""
    raw, _ = _run_command(f"curl -s --max-time {timeout} -A 'Mozilla/5.0 (compatible)' -L '{url}' 2>/dev/null", timeout=timeout+10)
    if not raw:
        return []
    items = []
    try:
        root = ET.fromstring(raw)
        entries = root.findall('.//item')
        atom_ns = 'http://www.w3.org/2005/Atom'
        if not entries:
            entries = root.findall(f'.//{{{atom_ns}}}entry')

        for e in entries[:max_items]:
            title_el = e.find('title')
            if title_el is None:
                title_el = e.find(f'{{{atom_ns}}}title')
            title = (title_el.text or '').strip() if title_el is not None else ''

            link = ''
            link_el = e.find('link')
            if link_el is not None:
                link = (link_el.text or link_el.get('href', '')).strip()
            else:
                link_el = e.find(f'{{{atom_ns}}}link')
                if link_el is not None:
                    link = (link_el.text or link_el.get('href', '')).strip()

            summary = ''
            for tag in ['description', f'{{{atom_ns}}}summary', 'summary',
                        f'{{{atom_ns}}}content', 'content']:
                desc_el = e.find(tag)
                if desc_el is not None and desc_el.text:
                    raw_summary = desc_el.text or ''
                    # Clean HTML tags, normalize spaces
                    summary = re.sub(r'<[^>]+>', ' ', raw_summary)
                    summary = re.sub(r'\s+', ' ', summary).strip()
                    # Cut at first sentence or max_len later
                    break

            if title:
                items.append((title[:80], link, summarize_text(summary)))
    except Exception:
        pass
    return items


def get_hn_news():
    """Hacker News топ-5 с кратким описанием"""
    hn_ids_str, _ = _run_command(
        "curl -s --max-time 10 'https://hacker-news.firebaseio.com/v0/topstories.json' 2>/dev/null | "
        "python3 -c \"import sys,json; ids=json.load(sys.stdin)[:7]; print(','.join(map(str,ids)))\"\""
    )
    if not hn_ids_str:
        return []

    items = []
    for story_id in hn_ids_str.split(',')[:7]:
        raw, _ = _run_command(
            f"curl -s --max-time 5 'https://hacker-news.firebaseio.com/v0/item/{story_id}.json' 2>/dev/null"
        )
        if raw and raw != 'null':
            try:
                d = json.loads(raw)
                title = d.get('title', '')
                sid = d.get('id', story_id)
                url = d.get('url', f'https://news.ycombinator.com/item?id={sid}')
                score = d.get('score', 0)
                comments = d.get('descendants', 0)
                text = d.get('text', '') or ''
                summary = re.sub(r'<[^>]+>', '', text).strip()
                summary = summarize_text(summary, 100)
                if title:
                    items.append({
                        'title': title, 'url': url,
                        'comments_url': f'https://news.ycombinator.com/item?id={sid}',
                        'score': score, 'comments': comments, 'summary': summary
                    })
            except:
                pass
    return items[:5]


def get_world_news():
    """Мировые новости — BBC / Al Jazeera / AP RSS"""
    sources = [
        ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("AP News", "https://rsshub.app/apnews/topics/ap-top-news"),
    ]
    for name, url in sources:
        items = fetch_rss_items(url, max_items=5)
        if items:
            return name, items
    return "World", []


def get_russia_news():
    """Новости России — Meduza / Lenta / Kommersant RSS"""
    sources = [
        ("Meduza", "https://meduza.io/rss/all"),
        ("Lenta", "https://lenta.ru/rss/news"),
        ("Коммерсант", "https://www.kommersant.ru/RSS/news.xml"),
    ]
    for name, url in sources:
        items = fetch_rss_items(url, max_items=5)
        if items:
            return name, items
    return "RU", []


def get_tech_news():
    """IT/Tech новости — TechCrunch / The Verge / Ars Technica"""
    sources = [
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ]
    for name, url in sources:
        items = fetch_rss_items(url, max_items=5)
        if items:
            return name, items
    return "Tech", []


def get_github_trending():
    """GitHub trending repos"""
    raw, _ = _run_command(
        "curl -s --max-time 10 "
        "'https://api.github.com/search/repositories?q=created:>2025-04-01&sort=stars&order=desc&per_page=5' "
        "2>/dev/null"
    )
    if not raw:
        return []
    try:
        data = json.loads(raw)
        items = []
        for r in data.get('items', [])[:5]:
            items.append({
                'name': r.get('full_name', '?'),
                'url': r.get('html_url', ''),
                'lang': r.get('language', ''),
                'desc': (r.get('description') or '')[:60],
                'stars': r.get('stargazers_count', 0),
            })
        return items
    except:
        return []


def render_news_block(section_emoji, section_name, source_name, items, with_summary=True):
    """Рендер блока новостей: заголовок + пронумерованные items с опциональным 1-line summary"""
    if not items:
        return f"{section_emoji} {section_name} — нет данных"

    lines = [f"{section_emoji} {section_name} _(источник: {source_name})_"]
    for i, (title, link, summary) in enumerate(items, 1):
        short = title[:70] + ("…" if len(title) > 70 else "")
        if link:
            line = f"  {i}. [{short}]({link})"
        else:
            line = f"  {i}. {short}"
        if with_summary and summary:
            line += f"\n      _{summary}_"
        lines.append(line)
    return "\n".join(lines)


def get_all_signals():
    """Собрать все новостные блоки"""
    sections = []

    # 1. IT / Hacker News
    hn = get_hn_news()
    if hn:
        lines = ["💻 IT / Hacker News:"]
        for i, item in enumerate(hn, 1):
            t = item['title'][:70] + ("…" if len(item['title']) > 70 else "")
            link = item['url']
            clink = item['comments_url']
            score = item['score']
            comments = item['comments']
            summary = item['summary']
            lines.append(f"  {i}. [{t}]({link}) · [💬{comments}]({clink}) ▲{score}")
            if summary:
                lines.append(f"      _{summary}_")
        sections.append("\n".join(lines))

    # 2. Tech news
    tech_src, tech_items = get_tech_news()
    sections.append(render_news_block("📱", "Технологии", tech_src, tech_items))

    # 3. World news
    world_src, world_items = get_world_news()
    sections.append(render_news_block("🌍", "Мир / Политика", world_src, world_items))

    # 4. Russia
    ru_src, ru_items = get_russia_news()
    sections.append(render_news_block("🇷🇺", "Россия", ru_src, ru_items))

    # 5. GitHub
    gh = get_github_trending()
    if gh:
        lines = ["🐙 GitHub Trending:"]
        for i, r in enumerate(gh, 1):
            lang = f" `{r['lang']}`" if r['lang'] else ""
            lines.append(f"  {i}. [{r['name']}]({r['url']}){lang} — {r['desc']} ⭐{r['stars']}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


if __name__ == "__main__":
    print(get_all_signals())