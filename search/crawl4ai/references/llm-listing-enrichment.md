# LLM Batch Enrichment for Listings

## Pattern: multi-text batch processing through LLM

Instead of calling LLM once per listing (slow & expensive), collect all raw texts from a source, send them in ONE batch request, then filter/process results.

## When to use

- **Telegram channels**: 5-50 posts per channel, most are spam or off-topic
- **OLX/classifieds**: when detailed description parsing is needed beyond JSON-LD
- **Any bulk text**: user-generated content where you need structured extraction + relevance check

## Workflow

```
Raw texts → Quick price filter (regex) → LLM batch → Filter is_house=True → DB upsert
```

### 1. Quick pre-filter (before LLM, saves money)

```python
_MIN_PRICE = 150_000_000  # 150 млн
_MAX_PRICE = 300_000_000  # 300 млн

def quick_price(text: str) -> int | None:
    text_lower = text.lower()
    m = re.search(r"(\d+[\d\s]*)\s*мл(?:н|рд)\b", text_lower)
    if m:
        value = int(re.sub(r"\s+", "", m.group(1)))
        return value * (1_000_000_000 if "млрд" in m.group(0) else 1_000_000)
    m = re.search(r"(\d[\d\s]{3,})\s*сум", text)
    if m:
        return int(re.sub(r"\s+", "", m.group(1)))
    return None

# Only send to LLM if price is in range
if price is not None and (price < _MIN_PRICE or price > _MAX_PRICE):
    skip  # Don't waste LLM calls on out-of-range
```

### 2. Batch LLM call

```python
def parse_listings(texts: list[str]) -> list[dict]:
    """Parse N texts in ONE LLM call."""
    numbered = "\n\n---\n\n".join(
        f"=== ОБЪЯВЛЕНИЕ {i+1} ===\n{t[:2000]}"
        for i, t in enumerate(texts)
    )

    payload = {
        "model": "deepseek/deepseek-v4-flash",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Распарси {len(texts)} объявлений.\n\n{numbered}"},
        ],
        "temperature": 0.05,  # Low temp for consistent extraction
        "max_tokens": 2000,
    }

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    resp = httpx.post(API_URL, json=payload, headers=headers, timeout=45)
    content = resp.json()["choices"][0]["message"]["content"]

    # Extract JSON array (handle markdown-wrapped)
    json_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, re.DOTALL)
    results = json.loads(json_match.group(1)) if json_match else json.loads(content)

    # Pad to match input length
    while len(results) < len(texts):
        results.append({"is_house": None})
    return results[:len(texts)]
```

### 3. System prompt

```python
SYSTEM_PROMPT = """Ты — парсер объявлений о продаже домов в Нукусе (Узбекистан).
Анализируй КАЖДОЕ объявление и извлекай структурированные данные.

Языки: русский, узбекский, каракалпакский.
Слова: "уй"=дом, "жай"=земля/участок, "сатылады"=продаётся,
"хана"=комната, "соток"=сотка (100м²), "млн"=миллион, "сум"=сум.

Верни ТОЛЬКО JSON-массив, никакого другого текста.
Формат ответа — массив объектов, по одному на каждое объявление:
[
  {
    "is_house": true/false,  // false если реклама, машина, не дом/земля
    "price_sum": число или null,
    "rooms": число или null,
    "area_sqm": число или null,
    "area_sotok": число или null,
    "district": "район или null",
    "floor": "этаж или null",
    "wall_material": "кирпич/пеноблок/саман/... или null",
    "gas": true/false/null,
    "water": true/false/null,
    "phone": "телефон или null",
    "is_apartment": true/false
  }
]"""
```

### 4. Fallback (rule-based, no LLM)

When API is unavailable or returns bad response:

```python
# Keywords for house detection
house_kw = ["уй", "жай", "дом", "сатыл", "соток", "фундамент", "этаж", "комнат"]
spam_kw = ["машина", "nexia", "камера", "реклам", "100k.uz", "автомобиль"]

has_house = sum(1 for kw in house_kw if kw in text_lower) >= 2
has_spam = sum(1 for kw in spam_kw if kw in text_lower) >= 1
is_house = has_house and not has_spam
```

## API configuration

Using kilocode gateway (OpenAI-compatible):

```
API_URL = "https://api.kilo.ai/api/gateway/chat/completions"
MODEL  = "deepseek/deepseek-v4-flash"
API_KEY = os.environ["KILOCODE_API_KEY"]  # from .env file
```

## Performance

| Batch size | Time per batch | Cost | Notes |
|-----------|---------------|------|-------|
| 5 texts | ~8-15 sec | low | Fastest option |
| 10-20 texts | ~15-45 sec | low | Sweet spot |
| 50+ texts | ~60+ sec | medium | May hit token limits |

## Known pitfalls

- **API timeout**: if batch is too large (>50 texts), increase timeout to 120s
- **Output truncation**: LLM may cut off JSON array if too many texts. Keep batches ≤ 30
- **Malformed JSON**: LLM sometimes wraps JSON in markdown ```json ... ```. Always extract via regex
- **Missing results**: LLM may return fewer results than inputs. Pad with `{"is_house": null}`
- **False positives**: Spam like "машина" with "комнат" → LLM usually catches it. Fallback regex may miss edge cases
- **False negatives**: "Куплю дом" (buying) vs "Продам дом" (selling) — LLM marks buying as is_house=false
