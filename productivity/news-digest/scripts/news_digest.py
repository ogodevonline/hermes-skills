#!/usr/bin/env python3
"""
News Digest — обеденный дайджест новостей из blogwatcher + GitHub Trending.
Собирает свежие статьи за 24ч, фильтрует по темам, переводит английские заголовки,
добавляет AI-суммаризацию, группирует по категориям и отправляет в Telegram.

API: KiloCode Gateway (kilo-auto/free)
"""

import os
import sys
import json
import re
import sqlite3
import requests
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ===== Конфигурация =====
HERMES_HOME = Path.home() / ".hermes"
TASKS_DIR = HERMES_HOME / "tasks"
ENV_FILE = HERMES_HOME / ".env"
DB_PATH = Path.home() / ".blogwatcher-cli" / "blogwatcher-cli.db"

MSK = timezone(timedelta(hours=3))

# KiloCode API
KILOCODE_BASE = "https://api.kilo.ai/api/gateway"
KILOCODE_MODEL = "kilo-auto/small"  # Дёшево, стабильно, для фоновых задач (перевод, суммаризация)
KILOCODE_FALLBACK = "inclusionai/ling-2.6-flash:free"  # Бесплатный fallback

# Токены Telegram (загружаются из .env)
TELEGRAM_BOT_TOKEN = None
TELEGRAM_CHAT_ID = None

# API ключ KiloCode
KILOCODE_API_KEY = None

# Загружаем .env
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            k = key.strip()
            v = value.strip()
            if k == "TELEGRAM_BOT_TOKEN":
                TELEGRAM_BOT_TOKEN = v
            elif k == "TELEGRAM_HOME_CHANNEL":
                TELEGRAM_CHAT_ID = v
            elif k == "TELEGRAM_ALLOWED_USERS":
                if not TELEGRAM_CHAT_ID:
                    TELEGRAM_CHAT_ID = v
            elif k == "KILOCODE_API_KEY":
                KILOCODE_API_KEY = v

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("❌ Ошибка: не заданы TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
    sys.exit(1)

if not KILOCODE_API_KEY:
    print("❌ Ошибка: не задан KILOCODE_API_KEY в .env")
    sys.exit(1)

# Категории и их иконки
CATEGORY_META = {
    "python_ai":  ("🐍", "Python & AI"),
    "security":   ("🔐", "Security"),
    "osint":      ("🕵️", "OSINT"),
    "policy":     ("🏛️", "Политика / Регуляции"),
    "russia":     ("🇷🇺", "Россия"),
    "tools":      ("🔧", "Инструменты / Релизы"),
    "general":    ("💡", "Разное"),
    "github":     ("🐙", "GitHub Trending"),
}

# Ключевые слова для фильтрации
KEYWORDS = [
    # Python / AI
    "python", "pypi", "django", "flask", "fastapi", "poetry",
    "ai", "ml", "llm", "gpt", "claude", "openai", "huggingface",
    "transformers", "pytorch", "tensorflow", "anthropic", "gemini",
    "copilot", "granite", "trainium",
    # Security / OSINT
    "security", "vulnerability", "cve", "exploit", "patch",
    "osint", "forensics", "reconnaissance", "investigation", "leak",
    "malware", "ransomware", "apt", "threat", "incident", "breach",
    "surveillance", "encryption", "privacy", "pentest", "stalkerware",
    "cyber", "hack", "0-day", "zeroday",
    # Policy / Russia / World
    "policy", "regulation", "law", "sanction", "export-control",
    "data-sovereignty", "cyber-law", "gdpr", "government",
    "russia", "ru", "moscow", "kremlin", "россия", "москва",
    "ukraine", "china", "us", "eu",
    # Tech / Open Source
    "release", "tool", "library", "framework", "update", "open-source",
    "best-practice", "tutorial", "guide", "how-to", "automation",
    "docker", "kubernetes", "ci-cd", "devops", "github", "gitlab",
]

# Blacklist — мусорные слова/домены, которые НЕ должны попадать в дайджест
BLACKLIST_WORDS = [
    "промокод", "скидка", "акция", "распродажа", "купон",
    "promo code", "coupon", "discount", "sale", "deal",
    "power bank", "повербанк", "зарядка", "powerbank",
    "корм для", "собака", "кошка", "зоотовары",
    "сигарета", "вейп", "электронная сигарета",
    "казино", "рулетка", "ставки на спорт",
    "кредит", "займ", "микрозайм", "дебетовая карта",
    "шампунь", "косметика", "парфюм",
    "доставка цветов", "букет",
    "матрас", "подушка ортопедическая",
    "товары для дома", "хозтовары",
    "автомобиль с пробегом", "автосалон",
    "ремонт квартир", "стройматериалы",
    "dog food", "cat food", "pet food",  # зоотовары на англ
]

BLACKLIST_DOMAINS = [
    "povaremok.ru", "loveplanet.ru", "zooprice.ru",
    "sbermegamarket.ru", "market.yandex.ru",
    "wildberries.ru", "ozon.ru",
]

# Русские названия месяцев
MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]
DAY_NAMES_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


# ===== KiloCode API =====

def kilo_chat(messages: list[dict], temperature: float = 0.1, max_tokens: int = 150, model: str | None = None) -> str | None:
    """Универсальный вызов KiloCode API со streaming (стабильнее для free моделей).
    Перебирает несколько free моделей для надёжности."""
    models_to_try = [
        model or KILOCODE_MODEL,
        KILOCODE_FALLBACK,
        "openrouter/free",
    ]

    for mdl in models_to_try:
        try:
            resp = requests.post(
                f"{KILOCODE_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {KILOCODE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": mdl,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                },
                timeout=25,
                stream=True,
            )
            if resp.status_code != 200:
                print(f"⚠️ KiloCode API error ({mdl}): {resp.status_code}")
                continue

            full = ""
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode(errors="replace")
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full += content
                    except json.JSONDecodeError:
                        pass

            if full:
                if mdl != models_to_try[0]:
                    print(f"   ✅ Использован fallback: {mdl}")
                return full.strip()
            else:
                print(f"⚠️ KiloCode пустой ответ ({mdl})")
                continue

        except Exception as e:
            print(f"⚠️ KiloCode API exception ({mdl}): {e}")
            continue

    return None


# ===== Перевод =====

def is_english(text: str) -> bool:
    """Проверить, что текст на английском (латиница преобладает над кириллицей)."""
    if not text:
        return False
    latin = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    cyril = sum(1 for c in text if 'а' <= c.lower() <= 'я')
    return latin > cyril and latin > 5


def translate_articles(articles: list[dict]) -> list[dict]:
    """
    Батчевый перевод английских заголовков через KiloCode.
    Отправляет все заголовки одним запросом — быстрее и дешевле.
    """
    to_translate = [a for a in articles if is_english(a["title"])]
    if not to_translate:
        return articles

    BATCH_SIZE = 10
    print(f"🌐 Перевод {len(to_translate)} заголовков (батчи по {BATCH_SIZE})...")

    for start in range(0, len(to_translate), BATCH_SIZE):
        batch = to_translate[start:start + BATCH_SIZE]
        titles = [a["title"] for a in batch]
        titles_json = json.dumps(titles, ensure_ascii=False)

        prompt = (
            f"Переведи следующие заголовки новостей с английского на русский язык. "
            f"Сохрани технические термины без перевода (например, Python, Django, CVE, API). "
            f"Верни ТОЛЬКО JSON-массив строк с переводами в том же порядке, без пояснений.\n\n"
            f"{titles_json}"
        )

        result = kilo_chat([
            {"role": "system", "content": "Ты переводчик технических новостей. Отвечай только JSON-массивом строк."},
            {"role": "user", "content": prompt},
        ], temperature=0.05, max_tokens=1000)

        if not result:
            print(f"⚠️ Батч {start//BATCH_SIZE + 1} не удался, пробуем по одному...")
            for a in batch:
                single_prompt = f"Переведи на русский: {a['title']}. Ответь только переводом."
                r = kilo_chat([
                    {"role": "system", "content": "Ты переводчик. Отвечай только переводом."},
                    {"role": "user", "content": single_prompt},
                ], temperature=0.05, max_tokens=200)
                if r and r != a["title"]:
                    a["title_original"] = a["title"]
                    a["title"] = r.strip().strip('"').strip("'")
                    print(f"  ✅ {a['title_original'][:40]}... → {a['title'][:40]}...")
                else:
                    print(f"  ⚠️ Не удалось перевести: {a['title'][:40]}...")
            continue

        # Парсим JSON ответ
        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                code_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', cleaned)
                if code_match:
                    cleaned = code_match.group(1).strip()
            json_match = re.search(r'\[.*\]', cleaned, re.DOTALL)
            if json_match:
                translations = json.loads(json_match.group(0))
            else:
                translations = json.loads(cleaned)

            if not isinstance(translations, list) or len(translations) != len(batch):
                print(f"⚠️ Неверный формат ответа батча {start//BATCH_SIZE + 1}: {len(translations) if isinstance(translations, list) else 'не массив'} переводов вместо {len(batch)}")
                continue

            for a, translated in zip(batch, translations):
                translated = translated.strip().strip('"').strip("'")
                if translated and translated != a["title"]:
                    a["title_original"] = a["title"]
                    a["title"] = translated
                    print(f"  ✅ {a['title_original'][:40]}... → {translated[:40]}...")
                else:
                    print(f"  ⚠️ Не удалось перевести: {a['title'][:40]}...")

        except (json.JSONDecodeError, Exception) as e:
            print(f"⚠️ Ошибка парсинга перевода батча {start//BATCH_SIZE + 1}: {e}")
            print(f"   Ответ: {result[:200]}")
            continue

    return articles


# ===== AI-суммаризация =====

def summarize_articles(articles: list[dict]) -> list[dict]:
    """
    Батчевая AI-суммаризация статей через KiloCode.
    Разбивает на подбатчи по 10 статей для надёжности.
    Добавляет поле summary (1-2 предложения на русском) к каждой статье.
    """
    if not articles:
        return articles

    BATCH_SIZE = 10
    done = 0

    for start in range(0, len(articles), BATCH_SIZE):
        batch = articles[start:start + BATCH_SIZE]
        print(f"📝 Суммаризация {len(batch)} статей (батч {start//BATCH_SIZE + 1})...")

        items = []
        for a in batch:
            source = a.get("source", "?")
            url_domain = get_source_url(a.get("url", ""))
            items.append({"title": a["title"], "source": source, "domain": url_domain})

        prompt = (
            "Для каждой новости напиши краткую аннотацию (2-3 предложения) на русском языке. "
            "Объясни практическую значимость новости. Упомяни: "
            "- чем это может быть важно для Python-разработчика, специалиста по безопасности или OSINT-аналитика "
            "- если речь о санкциях, ограничениях, блокировках или альтернативах для России — отметь это обязательно "
            "- какие новые возможности, угрозы или изменения это создаёт "
            "Верни ТОЛЬКО JSON-массив строк с аннотациями в том же порядке.\n\n"
            f"{json.dumps(items, ensure_ascii=False, indent=2)}"
        )

        result = kilo_chat([
            {"role": "system", "content": "Ты редактор технического дайджеста. Пиши краткие, информативные аннотации на русском. Отвечай только JSON-массивом."},
            {"role": "user", "content": prompt},
        ], temperature=0.2, max_tokens=2000)

        if not result:
            print("⚠️ Суммаризация батча не удалась")
            continue

        try:
            # Очищаем от markdown-кода
            cleaned = result.strip()
            if cleaned.startswith("```"):
                code_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', cleaned)
                if code_match:
                    cleaned = code_match.group(1).strip()
            json_match = re.search(r'\[.*\]', cleaned, re.DOTALL)
            if json_match:
                summaries = json.loads(json_match.group(0))
            else:
                summaries = json.loads(cleaned)

            if not isinstance(summaries, list):
                print(f"⚠️ Неверный формат суммаризации: не массив")
                continue

            for a, summary in zip(batch, summaries):
                summary = str(summary).strip().strip('"').strip("'")
                if summary and summary != "None":
                    a["summary"] = summary
                    done += 1
                    if done <= 5:  # Показываем первые 5 для лога
                        print(f"  📄 {a['title'][:40]}... → {summary[:60]}...")

        except (json.JSONDecodeError, Exception) as e:
            print(f"⚠️ Ошибка парсинга суммаризации: {e}")
            continue

    print(f"✅ Суммаризировано: {done}/{len(articles)} статей")
    return articles


# ===== Telegram =====

def html_escape(text: str) -> str:
    """Экранировать HTML-спецсимволы для Telegram HTML parse_mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_telegram(text: str) -> bool:
    """Отправить сообщение в Telegram (HTML parse_mode)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return True
        print(f"❌ Telegram error: {r.status_code} {r.text[:200]}")
        return False
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")
        return False


def send_telegram_chunks(chunks: list[str]) -> bool:
    """Отправить сообщение по частям (макс 4000 символов)."""
    all_ok = True
    for i, chunk in enumerate(chunks, 1):
        print(f"📤 Отправка части {i}/{len(chunks)} ({len(chunk)} символов)...")
        ok = send_telegram(chunk)
        if not ok:
            all_ok = False
    return all_ok


# ===== GitHub Trending =====

def get_github_trending(since: str = "daily") -> list[dict]:
    """GitHub trending repos за выбранный период (daily/weekly/monthly) через парсинг HTML + API."""
    # 1. Парсим github.com/trending для получения списка репозиториев
    raw, _ = _run_command(
        f"curl -s --max-time 15 "
        f"'https://github.com/trending?since={since}' "
        "2>/dev/null"
    )
    if not raw:
        return []

    # 2. Извлекаем имена репозиториев из HTML
    repo_pattern = re.compile(r'href="/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"')
    all_hrefs = repo_pattern.findall(raw)

    # Фильтруем: только owner/repo, не sponsors/trending/apps
    skip_prefixes = ("/sponsors/", "/trending/", "/apps/", "/settings/")
    repos = []
    seen = set()
    for href in all_hrefs:
        path = href.split('"')[1]  # "/owner/repo"
        if any(path.startswith(p) for p in skip_prefixes):
            continue
        if path in seen:
            continue
        seen.add(path)
        repos.append(path.strip("/"))

    # Берём первые 7 репо с периода — не все дойдут до API (могут быть ошибки)
    repos = repos[:7]

    # 3. Для каждого репозитория получаем детали через GitHub API
    items = []
    for repo_name in repos:
        raw_repo, _ = _run_command(
            f"curl -s --max-time 5 "
            f"'https://api.github.com/repos/{repo_name}' "
            "2>/dev/null"
        )
        if not raw_repo:
            continue
        try:
            r = json.loads(raw_repo)
            if "message" in r and r["message"] == "Not Found":
                continue
            items.append({
                "name": r.get("full_name", repo_name),
                "url": r.get("html_url", f"https://github.com/{repo_name}"),
                "lang": r.get("language") or "",
                "desc": (r.get("description") or ""),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "issues": r.get("open_issues_count", 0),
                "topics": r.get("topics", []),
                "created": r.get("created_at", ""),
                "updated": r.get("updated_at", ""),
            })
        except:
            continue

    return items


def get_github_trending_merged() -> list[dict]:
    """Собрать trending за daily + weekly + monthly, объединить, удалить дубликаты, отсортировать по звёздам."""
    print("🐙 GitHub Trending (daily + weekly + monthly)...")
    all_items = []

    for period in ["daily", "weekly", "monthly"]:
        print(f"   Период: {period}...")
        items = get_github_trending(since=period)
        print(f"      {len(items)} репозиториев")
        all_items.extend(items)

    # Убираем дубликаты по имени репозитория
    seen = set()
    unique = []
    for item in all_items:
        if item["name"] not in seen:
            seen.add(item["name"])
            unique.append(item)

    # Все уникальные, сортируем по звёздам
    unique.sort(key=lambda x: x.get("stars", 0), reverse=True)

    print(f"   ✅ Итого уникальных: {len(unique)}")
    return unique


def github_summarize(repos: list[dict]) -> list[dict]:
    """Сгенерировать расширенные AI-аннотации для GitHub репозиториев через KiloCode."""
    if not repos:
        return repos

    items = []
    for r in repos:
        items.append({
            "name": r["name"],
            "desc": r.get("desc", "")[:300],
            "lang": r.get("lang", ""),
            "stars": r["stars"],
            "forks": r.get("forks", 0),
            "topics": ", ".join(r.get("topics", [])[:5]),
        })

    print(f"🤖 GitHub AI-аннотации ({len(repos)} репозиториев)...")
    prompt = (
        "Для каждого GitHub репозитория ниже напиши краткую аннотацию (2-3 предложения) на русском языке, "
        "объясняющую: чем репозиторий полезен, для кого предназначен (разработчики, ML-инженеры, дизайнеры и т.д.), "
        "почему он набрал много звёзд и стоит внимания специалиста. "
        "Верни ТОЛЬКО JSON-массив строк с аннотациями в том же порядке, без пояснений.\n\n"
        f"{json.dumps(items, ensure_ascii=False, indent=2)}"
    )

    result = kilo_chat([
        {"role": "system", "content": "Ты технический редактор, анализирующий GitHub репозитории. Пиши информативные аннотации на русском. Отвечай только JSON-массивом."},
        {"role": "user", "content": prompt},
    ], temperature=0.2, max_tokens=2000)

    if not result:
        return repos

    try:
        # Очищаем от markdown-кода
        cleaned = result.strip()
        if cleaned.startswith("```"):
            code_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', cleaned)
            if code_match:
                cleaned = code_match.group(1).strip()
        json_match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if json_match:
            summaries = json.loads(json_match.group(0))
        else:
            summaries = json.loads(cleaned)

        if isinstance(summaries, list):
            for r, summary in zip(repos, summaries):
                summary = str(summary).strip().strip('"').strip("'")
                if summary and summary != "None":
                    r["gh_summary"] = summary
                    print(f"  📦 {r['name']} → {summary[:60]}...")
    except Exception as e:
        print(f"⚠️ Ошибка суммаризации GitHub: {e}")

    return repos


def _run_command(cmd: str, timeout: int = 15) -> tuple[str, str]:
    """Запустить shell-команду, вернуть (stdout, stderr)."""
    import subprocess
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return "", str(e)


def get_source_url(url: str) -> str:
    """Сократить URL до домена для отображения."""
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except:
        return url


# ===== Blogwatcher DB =====

def get_recent_articles(hours: int = 24, limit: int = 60) -> list[dict]:
    """Получить свежие статьи из blogwatcher DB за последние N часов."""
    if not DB_PATH.exists():
        print(f"❌ БД blogwatcher не найдена: {DB_PATH}")
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    cur.execute("""
        SELECT a.id, a.title, a.url, a.published_date, b.name as source, a.categories
        FROM articles a
        JOIN blogs b ON a.blog_id = b.id
        WHERE a.published_date > ?
        ORDER BY a.published_date DESC
        LIMIT ?
    """, (cutoff.isoformat(), limit))

    rows = cur.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def is_blacklisted(article: dict) -> bool:
    """Проверить, не является ли статья мусорной."""
    text = (article.get("title", "") + " " + article.get("url", "")).lower()
    url = article.get("url", "").lower()

    # Проверка по домену
    for domain in BLACKLIST_DOMAINS:
        if domain in url:
            return True

    # Проверка по ключевым словам
    for word in BLACKLIST_WORDS:
        if word in text:
            return True

    return False


def matches_keywords(article: dict) -> bool:
    """Проверить, содержит ли заголовок или URL ключевые слова (с учётом границ слов для коротких ключей)."""
    text = (article["title"] + " " + article.get("url", "")).lower()
    for kw in KEYWORDS:
        if kw.lower() in text:
            # Для коротких ключей (≤3 символов) проверяем по границам слов
            if len(kw) <= 3:
                if re.search(r'\b' + re.escape(kw.lower()) + r'\b', text):
                    return True
            else:
                return True
    return False


def categorize(article: dict) -> str:
    """Отнести статью к категории по ключевым словам (с учётом границ слов для коротких ключей)."""
    text = (article["title"] + " " + article.get("url", "")).lower()

    def has_kw_in_text(keywords: list[str]) -> bool:
        """Проверить наличие любого из ключевых слов в тексте с учётом границ для коротких."""
        for kw in keywords:
            kw_lower = kw.lower()
            if len(kw_lower) <= 3:
                if re.search(r'\b' + re.escape(kw_lower) + r'\b', text):
                    return True
            elif kw_lower in text:
                return True
        return False

    # OSINT — проверяем раньше security
    if has_kw_in_text(["osint", "forensics", "reconnaissance"]):
        return "osint"

    # Security
    if has_kw_in_text([
        "cve", "vulnerability", "exploit", "patch", "malware",
        "ransomware", "apt", "threat", "incident", "breach",
        "surveillance", "encryption", "privacy", "stalkerware",
        "0-day", "zeroday", "cyber", "hack", "pentest",
    ]):
        return "security"

    # Python
    if has_kw_in_text([
        "python", "pypi", "django", "flask", "fastapi", "poetry",
    ]):
        return "python_ai"

    # AI/ML
    if has_kw_in_text([
        "ai", "ml", "llm", "gpt", "claude", "openai", "huggingface",
        "transformers", "pytorch", "tensorflow", "anthropic", "gemini",
        "granite", "copilot", "trainium",
    ]):
        return "python_ai"

    # Policy
    if has_kw_in_text([
        "policy", "regulation", "law", "sanction", "gdpr",
        "cyber-law", "data-sovereignty", "export-control",
    ]):
        return "policy"

    # Russia / Ukraine / geopolitical
    if has_kw_in_text(["russia", "россия", "moscow", "москва", "kremlin", "ukraine"]):
        return "russia"

    # Tools / frameworks / releases
    if has_kw_in_text([
        "release", "tool", "library", "framework", "update",
        "monad", "mozilla", "prompt api", "cursor", "cookbook",
    ]):
        return "tools"

    return "general"


# ===== Форматирование =====

def format_date_ru(dt: datetime) -> str:
    """Форматировать дату по-русски: '28 апреля 2026'."""
    return f"{dt.day} {MONTHS_RU[dt.month]} {dt.year}"


def format_digest(groups: dict, max_per_group: int = 4) -> str:
    """Сформировать текст дайджеста в HTML для Telegram."""
    now_msk = datetime.now(MSK)

    lines = [
        f"📡 <b>Обеденный дайджест — {DAY_NAMES_RU[now_msk.weekday()]}, {format_date_ru(now_msk)}</b>",
        f"<i>{now_msk.strftime('%H:%M МСК')}</i>",
        "",
        "━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    # Сначала GitHub Trending (если есть) с расширенной информацией
    gh = groups.pop("github", None)
    if gh:
        lines.append("🐙 <b>GitHub Trending:</b>")
        for item in gh:
            lang = f" [{html_escape(item['lang'])}]" if item.get("lang") else ""
            forks_s = f" 🍴{item['forks']}" if item.get("forks") else ""
            issues_s = f" 🐛{item['issues']}" if item.get("issues") and item['issues'] < 999 else ""
            # Topics (первые 3)
            topics = item.get("topics", [])
            topics_s = f" 🏷️{', '.join(topics[:3])}" if topics else ""
            
            # Краткое описание (60 символов) — в строку с названием
            desc_short = ""
            if item.get("desc"):
                d = html_escape(item["desc"][:80])
                desc_short = f" — {d}"
            
            lines.append(f"  • <a href=\"{item['url']}\">{html_escape(item['name'])}</a>{lang} ⭐{item['stars']}{forks_s}{desc_short}{topics_s}")

            # AI-аннотация (если есть)
            if item.get("gh_summary"):
                summary_h = html_escape(item["gh_summary"])
                lines.append(f"    💡 {summary_h}")

            lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━")
        lines.append("")

    # Категории с сортировкой: security/osint/python_ai → policy/russia → tools/general
    priority = ["security", "osint", "python_ai", "policy", "russia", "tools", "general"]
    for cat in priority:
        articles = groups.get(cat, [])
        if not articles:
            continue
        icon, name = CATEGORY_META.get(cat, ("📰", cat))
        lines.append(f"{icon} <b>{html_escape(name)}:</b>")
        for art in articles[:max_per_group]:
            title = html_escape(art["title"])
            source = html_escape(art.get("source", "?"))
            url = art.get("url", "")

            # Строка с заголовком (ссылка)
            title_line = f"  • <a href=\"{url}\">{title}</a>"
            # Добавляем оригинал, если был переведён
            if "title_original" in art:
                orig = html_escape(art['title_original'][:50])
                if len(art['title_original']) > 50:
                    orig += "…"
                title_line += f" <i>(ориг: {orig})</i>"
            lines.append(title_line)
            # Источник
            lines.append(f"    <i>({source})</i>")
            # Summary (если есть)
            if "summary" in art:
                summary_h = html_escape(art['summary'])
                lines.append(f"    💬 {summary_h}")
        lines.append("")

    # Итог
    total = sum(len(v) for k, v in groups.items() if k != "github")
    lines.append(f"📊 Всего: {total} статей из {len(groups)} категорий")
    lines.append("🤖 Перевод и аннотации — KiloCode Free")

    return "\n".join(lines)


def split_chunks(text: str, max_len: int = 3600) -> list[str]:
    """Разбить на чанки по границам строк."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    lines = text.split("\n")
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line
    if current:
        chunks.append(current)
    return chunks


# ===== Main =====

def main():
    print(f"📡 News Digest — {datetime.now(MSK).strftime('%H:%M МСК')}")
    print("=" * 40)

    # 0. Сканируем blogwatcher перед сбором дайджеста
    print("🔄 Запуск blogwatcher-cli scan...")
    scan_out, scan_err = _run_command("blogwatcher-cli scan", timeout=120)
    if scan_err and "error" in scan_err.lower():
        print(f"⚠️ Ошибка сканирования blogwatcher: {scan_err[:200]}")
    else:
        new_count = 0
        for line in scan_out.split("\n"):
            if "new" in line.lower() and "article" in line.lower():
                import re as _re
                nums = _re.findall(r"\d+", line)
                if nums:
                    new_count = int(nums[-1])
                break
        if new_count:
            print(f"   ✅ Найдено новых статей: {new_count}")
        else:
            print(f"   ✅ Сканирование завершено")

    # 1. Получаем статьи из blogwatcher (максимум 30 — для производительности)
    print("📰 Загрузка статей из blogwatcher DB...")
    articles = get_recent_articles(hours=24, limit=30)
    print(f"   Найдено: {len(articles)} статей за 24ч")
    
    # Fallback: если за 24ч пусто — расширяем окно
    if not articles:
        print("   ⚠️ За 24ч ничего нет, пробуем 48ч...")
        articles = get_recent_articles(hours=48, limit=30)
        print(f"   Найдено: {len(articles)} статей за 48ч")
    if not articles:
        print("   ⚠️ И за 48ч пусто, пробуем 72ч...")
        articles = get_recent_articles(hours=72, limit=30)
        print(f"   Найдено: {len(articles)} статей за 72ч")

    # 1.5 Фильтруем мусор
    before = len(articles)
    articles = [a for a in articles if not is_blacklisted(a)]
    blacklisted = before - len(articles)
    if blacklisted:
        print(f"🗑️ Отсеяно мусора: {blacklisted}")

    # 2. Фильтруем по ключевым словам
    filtered = [a for a in articles if matches_keywords(a)]
    print(f"✅ После фильтрации: {len(filtered)} статей")

    # 3. Категоризируем (если есть статьи)
    groups = {}
    if filtered:
        for art in filtered:
            cat = categorize(art)
            groups.setdefault(cat, []).append(art)
        print(f"📊 Категории: {', '.join(f'{k}:{len(v)}' for k,v in groups.items())}")

        # 4. Переводим английские заголовки (батч)
        for cat in groups:
            groups[cat] = translate_articles(groups[cat])

        # 4.5 AI-суммаризация (батч, максимум 20 статей — по приоритетным категориям)
        # Сортируем категории по приоритету и берём первые 20 статей
        priority_order = ["security", "osint", "python_ai", "policy", "russia", "tools", "general"]
        sorted_articles = []
        for cat in priority_order:
            sorted_articles.extend(groups.get(cat, []))
        articles_to_summarize = sorted_articles[:20]
        
        if len(sorted_articles) > 20:
            print(f"📊 Сокращение суммаризации: {len(sorted_articles)} → 20 (по приоритету категорий)")
        
        summarized = summarize_articles(articles_to_summarize)
        print(f"✅ Суммаризировано статей: {len(summarized)}")
    else:
        print("ℹ️ Нет релевантных новостей из blogwatcher — проверяем GitHub Trending")

    # 5. Добавляем GitHub Trending с AI-аннотациями (daily + weekly + monthly)
    gh = get_github_trending_merged()
    if gh:
        # AI-аннотации для репозиториев
        gh = github_summarize(gh)
        groups["github"] = gh
        print(f"   {len(gh)} репозиториев")

    # 5.5 Если ничего нет — выходим
    if not groups:
        print("✅ Пропускаем — нет ни статей, ни GitHub Trending")
        return

    # 6. Форматируем дайджест
    print("📝 Форматирование...")
    digest_text = format_digest(groups)

    # 7. Разбиваем на чанки
    chunks = split_chunks(digest_text, max_len=3800)

    # 8. Отправляем
    print(f"📤 Отправка ({len(chunks)} чанков)...")
    success = send_telegram_chunks(chunks)

    if success:
        print("✅ Обеденный дайджест отправлен!")
    else:
        print("❌ Часть сообщений не отправлена")

    # Сохраняем лог
    output_dir = HERMES_HOME / "cron" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / f"news_digest_{datetime.now(MSK).strftime('%Y%m%d')}.md"
    with open(log_file, "w") as f:
        f.write(digest_text)
    print(f"💾 Лог сохранён: {log_file}")


if __name__ == "__main__":
    main()
