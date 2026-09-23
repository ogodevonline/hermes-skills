#!/usr/bin/env python3
"""GitHub топ репозиториев за неделю через Search API."""
import json, urllib.request, os
from datetime import date, timedelta

def main():
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    url = f"https://api.github.com/search/repositories?q=created:>{week_ago}&sort=stars&order=desc&per_page=10"
    
    req = urllib.request.Request(url, headers={
        "User-Agent": "Hermes/1.0",
        "Accept": "application/vnd.github+json"
    })
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"❌ Ошибка GitHub API: {e}")
        return
    
    items = data.get('items', [])
    if not items:
        print("🔥 GitHub трендов за неделю нет")
        return
    
    print("🔥 **GitHub тренды за неделю:**")
    for i, repo in enumerate(items[:10], 1):
        name = repo['full_name']
        desc = (repo['description'] or '')[:80]
        stars = repo['stargazers_count']
        lang = repo.get('language') or ''
        lang_tag = f" [{lang}]" if lang else ""
        print(f"{i}. {name}{lang_tag} — {desc} ⭐{stars}")

if __name__ == '__main__':
    main()