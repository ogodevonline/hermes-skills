# Instagram Parsing for Nukus Houses (July 2026)

## Goal
Parse Instagram accounts of Nukus realtors/agencies for house/apartment listings.

## Options

### 1. Instaloader (FREE, already installed v4.15.2)
- **Pro:** бесплатно, open-source, уже в requirements.txt
- **Con:** нужен IG sessionid (кука из браузера), может банить сессию
- **Что даёт:** посты (текст, фото, видео), комментарии, профили
- **Не даёт:** транскрибацию видео, OCR

### 2. HikerAPI ($0.0006/req, ~100 бесплатно)
- **Pro:** 99% success rate, 100+ endpoints, MCP server for AI agents
- **Con:** оплата USD (картой не из РФ)

### 3. RocketAPI (от €49/мес)
- **Pro:** 38 endpoints, Python SDK
- **Con:** USD, подписка

## Video Transcription

### Яндекс SpeechKit (RUB)
- Асинхронное: ~0.28 ₽/мин
- Минута Reels (~30-60 сек видео): ~0.14-0.28 ₽
- 1000 роликов: ~140-280 ₽
- Оплата рублями через Яндекс.Облако
- Python SDK: `pip install yandex-speechkit`

### Whisper (FREE, local CPU)
- tiny (~1 GB RAM, ~1x realtime) — влезает на VPS
- base (~1.5 GB RAM) — влезает
- small (~2.5 GB RAM) — на грани
- medium (~5 GB RAM) — не влезает (VPS 4.8 GB)

## Pipeline (planned)
```
instaloader → download Reels video
    ↓
ffmpeg → extract audio (opus → wav/mp3)
    ↓
Whisper OR Яндекс SpeechKit → transcription
    ↓
text + comments → insta_posts table in nukus.db
```
