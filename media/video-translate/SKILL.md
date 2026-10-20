---
name: video-translate
description: Transcribe and translate social media videos (IG/TikTok/YT); long YouTube videos via auto-subs.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [video, transcription, translation, whisper, instagram, tiktok, youtube]
    category: media
    related_skills: [english]
---

# Video Translate Skill

Скачивает короткое видео из соцсетей (Instagram Reels, TikTok, YouTube Shorts), распознаёт речь локально через faster-whisper и переводит на язык пользователя (обычно русский). Только короткие клипы; длинные видео (лекции/подкасты/разборы) — пайплайн через авто-субтитры yt-dlp, см. раздел ниже.

## When to Use

- Пользователь прислал ссылку на reel/short/видео и просит «переведи», «что там говорят», «перевод напиши».
- Нужен текст речи из видео без облачных STT-ключей и без денег.
- Проверить, есть ли у видео субтитры, прежде чем что-то распознавать.

## Prerequisites

- `yt-dlp` — `uv tool install yt-dlp` (бинарь в `~/.local/bin/yt-dlp`).
- `ffmpeg` — системный (обычно `/usr/bin/ffmpeg`).
- `faster-whisper` — **НЕ ставить в venv Hermes**. Отдельный venv:
  `uv venv /tmp/whisper_venv && uv pip install --python /tmp/whisper_venv/bin/python faster-whisper`
- Модели whisper (tiny/base/small) кешируются в `~/.cache/huggingface/hub/models--Systran--faster-whisper-*` — после первой загрузки распознавание почти бесплатное.

## How to Run

См. Procedure. Скрипт транскрипции: `scripts/transcribe_audio.py` — запускать через `/tmp/whisper_venv/bin/python`.

## Quick Reference

```bash
uv tool install yt-dlp   # один раз
cd /tmp && mkdir -p reel_dl && cd reel_dl
~/.local/bin/yt-dlp --no-playlist --no-warnings -o "reel.%(ext)s" "URL"   # скачать (merge в reel.mp4)
~/.local/bin/yt-dlp --no-warnings --list-subs "URL"                        # ДЁШЕВО: субтитры ДО транскрипции
ffmpeg -y -v error -i reel.mp4 -vn -ac 1 -ar 16000 audio.wav              # звук 16kHz mono
/tmp/whisper_venv/bin/python <skill_dir>/scripts/transcribe_audio.py audio.wav base
```

## Procedure

1. **Сначала дешёвый путь (пользователь явно просил: «дорого, проще запрос»).** Если у поста есть текст (описание/подпись) — отдай его. Для Instagram подпись достаётся без видео: `yt-dlp --skip-download --write-info-json -o "post_%(id)s" "URL"`, затем читай `description` из `post_<id>.info.json`. Проверь субтитры: `yt-dlp --no-warnings --list-subs "URL"`. Если субтитры есть — скачай их (`--write-subs --sub-langs all`, или `--write-auto-subs` для авто) и НЕ запускать транскрипцию.
2. Скачай видео. Публичные IG-рилсы качаются без логина и cookies. Перед скачиванием определи тип поста: если yt-dlp пишет `No video formats found` для каждого элемента — это фото или карусель без видео, транскрипция бессмысленна (см. Pitfalls).
3. Извлеки аудио в wav 16kHz mono (`-vn -ac 1 -ar 16000`).
4. Транскрибируй: язык авто (`language=None`) — скрипт печатает определённый язык и вероятность.
5. Переведи сам (ты — LLM), ответь на языке пользователя. Для коротких клипов давай оригинал + перевод, иронию/сарказм передавай смыслом, не дословно.

## Длинные YouTube-видео (лекции/подкасты/разборы): субтитры, не транскрипция

Полнометражные видео (10 мин – 2+ ч) НЕ транскрибировать через whisper/Kilo — у YouTube почти всегда есть авто-субтитры: бесплатно, быстро, точнее распознавания. Пайплайн (проверен 2026-09 на 34-мин видео):

```bash
# 1. Проверить наличие субтитров (вывод = список языков)
~/.local/bin/yt-dlp --skip-download --list-subs "URL"

# 2. Скачать авто-субтитры БЕЗ видео (в /tmp)
~/.local/bin/yt-dlp --skip-download --write-auto-subs --sub-langs "en" --sub-format vtt -o "video_%(id)s" "URL"

# 3. Метаданные для ответа: название, канал, длительность, просмотры, дата
~/.local/bin/yt-dlp --skip-download --print "%(title)s | %(channel)s | %(duration_string)s | %(view_count)s views | %(upload_date)s" "URL"

# 4. Очистить VTT → plain text (убрать header, таймкоды, <теги>)
python3 -c "
import re
content = open('video_XXX.en.vtt', encoding='utf-8').read()
lines = [re.sub(r'<[^>]+>', '', l.strip()) for l in content.split('\n')
         if l.strip() and not l.startswith('WEBVTT') and not l.startswith('Kind:')
         and not re.match(r'^\d{2}:\d{2}', l) and '-->' not in l and not l.startswith('NOTE')]
open('transcript.txt', 'w', encoding='utf-8').write(' '.join(l for l in lines if l))
"
```

⚠️ **read_file обрезает длинный однострочный текст** — если транскрипт записан одной строкой, read_file показывает только начало. Перед чтением разбей на строки ~3500 символов, потом читай с `offset`/`limit`:

```bash
python3 -c "
text = open('transcript.txt', encoding='utf-8').read()
lines, cur = [], ''
for w in text.split():
    cur = w if not cur else cur + ' ' + w
    if len(cur) > 3500:
        lines.append(cur); cur = ''
if cur: lines.append(cur)
open('transcript_lines.txt', 'w', encoding='utf-8').write('\n'.join(lines))
"
```

- Авто-субтитры = автоперевод речи: допустимы повторы слов («word word word») и опечатки — смысл читается, это нормально.
- Разбор видео для пользователя: сначала метаданные + полный транскрипт, потом структурированный пересказ тезисов с привязкой к его задаче/проектам (не generic-пересказ).

### Сохранение выводов разбора (vault + money)

Когда пользователь просит «сохрани идеи/выводы из видео» — сохраняй СРАЗУ в два места, не жди напоминания:

1. **Vault-заметка** — `~/hermes-vault/Projects/Planning/YYYY-MM-DD/<slug>.md`. Frontmatter по навыку vault-frontmatter (node_type=plan для Planning/, status=draft, created/updated). Если пользователь ценит точные формулировки автора — включай дословные цитаты, а не пересказ.
2. **Money-снапшот** (если контент — бизнес-идеи/выводы/стратегия): `~/.smtm/sessions/<slug>/<YYYYMMDD-HHMMSS>-<title>.md` по формату money-save: frontmatter slug/timestamp ISO с таймзоной/title ≤24 симв./source_skill/status/next_skill; секции Business state / Confirmed conclusions (помечать (new)/(reaffirmed)) / Ruled out / Open hypotheses / Next move / Notes. Подхватится через /money-restore в любой будущей сессии. Slug бери по смыслу (напр. agent-internet), а не по имени проекта, если выводы касаются нескольких проектов.

Урок (05.09.2026, разбор «Cloudflare will make 1000+ AI millionaires»): пользователь поправил «в money навыке вроде тоже нужно сохранять» — vault-заметки для бизнес-идей НЕДОСТАТОЧНО, нужен и .smtm-снапшот. Оба файла писать сразу, не дожидаясь второй просьбы.

### Цитаты и выдача транскрипта

- Полный транскрипт чужого видео пользователю НЕ выписывать: это воспроизведение охраняемого контента. Отдавать структурированный пересказ своими словами + таймкоды ключевых мест.
- Точные формулировки — только короткие фразы (несколько слов, 1–2 предложения) в кавычках с атрибуцией. Извлекать программно из очищенного транскрипта (python find по lowercase-фразе), а не переписывать по памяти. Длинные блоки-окна (±600–700 символов) не выводить.
- Если пользователь просит «выпиши весь текст» — отказать вежливо, предложить конспект или ссылку на первоисточник (видео/субтитры на его машине), без вставки текста в чат.

## Pitfalls

- У IG-рилсов субтитров обычно НЕТ (`<id> has no subtitles`) — не трать время, сразу к аудио.
- Instagram-пост с несколькими слайдами (карусель) yt-dlp трактует как плейлист, и `--no-playlist` его не отменяет: обрабатываются все элементы. Для фото-карусели `No video formats found` и нет картинок для скачивания (даже `--write-all-thumbnails` ничего не дал). Из такого поста yt-dlp вытаскивает только подпись и метаданные (`info.json`). Текст слайдов можно получить только от пользователя (скриншоты) или из открытой в браузере сессии; не повторяй попытки скачивания карусели тем же способом.
- Ошибка `No CSRF token set by Instagram API` — предупреждение, а не провал: метаданные при этом приходят.
- Первый запуск модели = скачивание ~145 МБ (base). Проверь кеш `~/.cache/huggingface` — если модель уже там, транскрипция дешёвая. Не предлагай платные облачные STT (Groq/OpenAI), если локальная модель кеширована: пользователь считает это дорого и бесится.
- `faster-whisper` не установлен в venv Hermes и в `~/.venv` — не пытайся импортировать оттуда, ставь в отдельный venv через uv (это секунды).
- **Кэш /tmp/reel_dl — ловушка.** Если там лежит reel.mp4 от ПРОШЛОГО рилса, yt-dlp скажет «has already been downloaded» и возьмёт СТАРЫЙ ролик. Перед скачиванием нового ВСЕГДА: `rm -f reel.mp4 reel.*.mp4 audio.wav transcript.txt` + флаг `--force-overwrites`. Сверяй длительность нового файла с ожидаемой (новый рилс ≠ старый по размеру/секундам).
- Правильный флаг авто-субтитров — `--write-auto-subs` (дефис). `--write-auto_subs` даёт `no such option`.
- Если `--sub-langs en` даёт 429, а видео имеет ru-субтитры, скачай тот язык, который есть в `--list-subs`: `--sub-langs "ru"`. Языки брать из списка, а не угадывать.
- Субтитры YouTube могут вернуть `HTTP Error 429: Too Many Requests` при серии запросов. Добавь `--sleep-subtitles 5` (пауза между запросами) и не повторяй залпом. Каждый повтор с 429 продлевает блокировку, поэтому: один запрос, при 429 — стоп и ответ пользователю с вариантами (открыть субтитры в плеере, прислать текст, попробовать позже). Не запускать повторы в фоне и не ставить `sleep` на 15 минут: пользователь хочет быструю проверку, а не отложенный запрос, который он потом ждёт.
- Ссылки `youtube.com/shorts/ID?is=...` — перед запросом канонизировать в `https://www.youtube.com/shorts/ID` (лишние query-параметры не нужны для yt-dlp).
- Для Shorts без авто-субтитров yt-dlp не вернёт текст вообще; тогда честный ответ — «субтитров нет», а не догадка по названию ролика.
- Предупреждение `No supported JavaScript runtime` (нет deno) не блокирует субтитры, но может скрыть часть форматов видео; для субтитров его игнорировать.
- `web_extract` для YouTube-ссылок часто не работает (нет extract-бэкенда). Для YouTube сразу идти через yt-dlp (раздел выше), не через web_extract.
- **IG фото-карусели (`/p/ID`, «No video formats found» ×N)**: yt-dlp/gallery-dl/embed без логина картинки НЕ отдают (gallery-dl → 302 на login + 429). Рабочий путь без логина: headless Chromium (`~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome --headless=new --no-sandbox --remote-debugging-port=9222 --user-data-dir=<scratch>` через terminal background=true) → browser_exec: new_tab(URL), закрыть модалку, кликать `button[aria-label="Далее"]`, собирать `article img` с naturalWidth≥1000 → скачать urllib с Referer instagram → vision_analyze каждого слайда. Подпись поста берётся из `yt-dlp --write-info-json` (description). Не перебирать прокси-сервисы (kkinstagram/ddinstagram и т.п.) — мертвы или проксируют логин-стену.
- Приватные/возрастные рилсы могут требовать логин — прямо скажи об этом вместо танцев с cookies.
- Авто-субтитры искажают термины (ASR путает слова: «йод» → «юда», «галогены» → «Голгена», «тироксин» → «тереопероксидаза»). Не отождествляй препарат, вещество или имя по одному слову: сверяй с контекстом и с первоисточником, а если сомневаешься — прямо скажи, что название неразборчиво, и попроси пользователя назвать его или прислать скриншот.
- `search_files` по транскрипту, записанному одной строкой, возвращает всю строку целиком. Поиск ключевых слов делай только после разбиения на строки (шаг из раздела про read_file).

## Видео о здоровье, лекарствах, добавках

- Не выписывать из видео препараты, дозировки, схемы приёма и «рецепты» как инструкцию. Пересказать тезисы автора, пометить, что это его утверждения.
- Каждое медицинское утверждение отметить как непроверенное и сверить по первоисточникам (NIH ODS, StatPearls, вкладыш препарата), прежде чем это считать фактом.
- Если пользователь спрашивает «как принимать» или «что за препарат» — сначала назвать препарат из первоисточника, который пользователь укажет или который виден в кадре/тексте; не выдумывать название по смыслу. Ответ: что это, для чего, почему не принимать по видео, что делать при симптомах.
- Сначала отвечать на заданный вопрос в одной-двух фразах, потом оговорки. Пользователь раздражается, когда ответ тонет в дисклеймерах.
- Масштаб: 58-секундный рилс ≈ видео 10 МБ, аудиодорожка 0.5 МБ, wav 1.8 МБ — всё быстро, транскрипция на CPU — секунды.

## Verification

- Транскрипция печатает `lang=en prob=0.99` — проверь, что язык определился верно (у рилса, где говорят не по-английски, `language=None` вернёт правильный код).
- Сегменты с таймкодами; текст покрывает всю длительность видео (сверь с `ffprobe`).
- Перевод: если это сатира/ирония (например, монолог «I'm a human, and...»), переводи смыслом, а не подстрочно.
