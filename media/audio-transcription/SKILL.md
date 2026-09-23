---
name: audio-transcription
version: "1.0.0"
author: Hermes Agent
description: Транскрибация аудио/видео через Kilo (voxtral/gpt-audio).
platforms: [linux]
metadata:
  hermes:
    tags: [transcription, audio, kilocode, media]
    category: media
    related_skills: [video-translate, web-search-scraper]
---

# Audio Transcription Skill

Транскрибирует аудио и видео (голосовые, рилы, записи звонков, лекции) в текст через аудио-модели шлюза KiloCode — без локального Whisper и без отдельных API-ключей (используется ключ kilocode из config.yaml). Не занимается переводом — только verbatim-текст; перевод при необходимости делает сам агент поверх транскрипта.

## When to Use

- Пользователь прислал аудио/видео/голосовое и спрашивает «о чём там говорят», «переведи», «сделай транскрипт».
- Нужен текст из рила/сторис/лекции/звонка, файл уже скачан локально.

## Prerequisites

- `ffmpeg` в PATH (конвертация в wav 16k mono).
- `python3` + модуль `yaml` (есть в системном python3).
- Ключ Kilo в `~/.hermes/config.yaml` → `model.api_key` + `model.base_url` (уже настроено).
- Скрипт: `~/.hermes/scripts/transcribe_audio.py`.

## How to Run

```bash
python3 ~/.hermes/scripts/transcribe_audio.py <file> [--model MODEL] [--lang LANG] [--out out.txt]
```

Модели (проверены 2026-09):

- `mistralai/voxtral-small-24b-2507` — по умолчанию, чистая транскрибация.
- `openai/gpt-audio` — запасная, добавляет ремарки вроде «(crying)».

## Quick Reference

- `--lang ru` — подсказка языка (улучшает точность). Без него модель определяет сама.
- `--chunk-min 9` — длинные файлы режутся на куски ≤9 мин (~17MB wav), по умолчанию так и есть.
- `--out file.txt` — сохранить транскрипт в файл (иначе печатает в stdout).
- Если файл — видео (.mp4/.mov/.webm), ffmpeg сам вытащит дорожку; указывать путь как есть.

## Procedure

1. Если файл пришёл из Telegram/интернета и ещё не скачан — скачать (`terminal`, для соцсетей yt-dlp) в понятное место вроде `~/downloads/`.
2. Запустить `python3 ~/.hermes/scripts/transcribe_audio.py <путь>`.
3. Если язык известен заранее — добавить `--lang ru`/`--lang en`.
4. Дождаться вывода (на длинных файлах прогресс «chunk i/n» в stderr).
5. Ответить пользователю: краткий пересказ «о чём говорят» на русском (если просили пересказ) или приложить транскрипт файлом, если просили текст целиком.

## Pitfalls

- ⚠️ НЕ использовать `openai/gpt-audio-mini` — отказывается транскрибировать (отвечает как «терапевт»/отнекивается).
- ⚠️ НЕ слать mp3 напрямую — модели на шлюзе Kilo не слышат mp3-часть. Только wav 16k mono (скрипт делает сам).
- ⚠️ Voxtral игнорирует `audio_url` с data-URI — только OpenAI-формат `input_audio`.
- Локальный faster-whisper в ~/.hermes/venvs/whisper существует, но медленнее и хуже слышит речь поверх музыки — Kilo-модели точнее.
- Модель может добавить в скобках эмоции («(crying)») — при verbatim-задаче просили «только текст», но лёгкие ремарки допустимы, не считать ошибкой.
- На аудио с музыкой/шумом ВАЖНО НЕ обрезать «тихие» куски самому — модель слышит речь поверх музыки лучше VAD-фильтров.

## Verification

- Скрипт вернул exit 0 и непустой текст.
- Контрольная фраза из проверенного рила (@iamjaycarvalho, 2026-09): на входе должен получиться текст про «I keep trying, but I keep failing… Shut up! … Get your ass up and do it again». Если на этом файле пусто/мусор — что-то сломалось.
