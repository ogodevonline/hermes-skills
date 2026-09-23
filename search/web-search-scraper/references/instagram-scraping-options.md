# Instagram Scraping Options

Options for scraping Instagram posts, reels, and comments. Updated May 2026.

## Free (self-hosted)

### 1. Instaloader (Python) — recommended for small scale
- **Repo:** https://github.com/instaloader/instaloader
- **Works:** posts, reels, stories, highlights, comments
- **Auth required:** recommended (browser cookies, NOT login/password)
- **Limits:** ~200 requests per 30 min before ban. Getting stricter in 2025-2026.
- **Ban avoidance:** browser cookies (not login), 5-10s delays, proxy rotation, 1 run/day
- **Comments:** `Post.get_comments()` — iterates all comments
- **New posts:** `--fast-update` flag checks only new content
- **For Nukus houses:** sufficient for 5-10 accounts checked daily. VPN NOT needed from Uzbekistan.

### 2. instagram-media-scraper (Node.js)
- **Repo:** https://github.com/ahmedrangel/instagram-media-scraper
- **Works:** posts, reels — caption, likes, comment_count, video URL
- **Does NOT give:** comment text (only count)
- **Auth:** browser cookies + X-IG-App-ID from DevTools
- **Good as:** fallback if instaloader breaks. Less features.

### 3. Free web viewers (no API)
- **Imginn.com** — view/download public content via web
- **Dumpor.io** — stories, highlights, reels viewer
- Both are web scrapers themselves — unreliable for automation, but good for manual checks.

## Paid (reliable)

### 1. Apify — best value for money
- **Instagram Reel Scraper** — $2.30/1000 reels, gives caption + 10 latest comments
- **Instagram Comments Scraper (No Login)** — $0.001/comment (no cookie), $0.0002 (with cookie)
- **Instagram Post Scraper** — $1.00-$2.50/1000 posts
- **Free credit:** $5 on signup (~2000 reels free)
- **Scheduling:** built-in cron (hourly/daily)
- **No bans:** Apify handles anti-bot measures
- **Cost for monitoring 10 accounts daily:** ~$3-5/month

### 2. RapidAPI — various providers
- Multiple Instagram scraping APIs from different developers
- From $0.01/request
- Quality varies by provider

### 3. ScrapingBee, Scrapfly, Bright Data
- Enterprise-grade, expensive
- Good for large scale (100k+ requests/day)

## Recommendation for Nukus houses monitoring

| Scale | Approach | Cost |
|-------|----------|------|
| 5-10 accounts, 1x/day | Instaloader + browser cookies | Free |
| Same, if banned | Apify Instagram Reel Scraper | ~$3-5/month |
| Full automation + reliability | Apify from day 1 | ~$3-5/month |

**Uzbekistan note:** Instagram is NOT blocked in Uzbekistan (unlike Russia). No VPN needed.
**Russia note:** If server is in Russia, Instagram is blocked by Roskomnadzor — VPN required.