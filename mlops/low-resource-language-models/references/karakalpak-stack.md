# Каракалпакский стек моделей — инвентарь

Проверено 02.10.2026 через HF API + живой прогон. Каракалпакский (Qaraqalpaqsha, ISO 639-3 `kaa`) — тюркский, кыпчакская группа, ~900 тыс. носителей, Каракалпакстан (Узбекистан). Письменность: латиница (основная, реформы 1995/2009/2016) и кириллица.

## ASR — аудио → текст

| Модель | Параметры | WER | Заметки |
|---|---|---|---|
| **atikuwu/whisper-medium-karakalpak** | 764M | **9.59%** test / 8.37% val, медиана 3.85%, CER 4.03% | SOTA. Apache-2.0. Обучен на KSC 107 ч, 6 эпох, ~8 ч на RTX 5060 Ti 16GB |
| facebook/mms-1b-all (`kaa` adapter) | 965M | 50.39% | кириллица → транслит перед скором |
| Quyashbek/whisper-medium-karakalpak | 764M | 65.29% | обучающие данные не раскрыты |
| Quyashbek/wav2vec2-xls-r-300m-karakalpak | 315M | 88.00% (своя карточка заявляет 21.21% на своём held-out) | разброс из-за разных тестов |
| openai/whisper-medium, zero-shot | 764M | 91.27% | автоопределение уходит в казахский |
| openai/whisper-large-v3, zero-shot | 1543M | 97.75% | каракалпакского в Whisper нет |

Все внешние системы в таблице atikuwu прогнаны на публичном test-сплите KSC (1074 уттер, 5.2 ч), одинаковой нормализацией, greedy, bootstrap 95% CI.
Демо: `https://huggingface.co/spaces/atikuwu/whisper-karakalpak-asr` (Gradio, api_name `transcribe`).

**Живой прогон 02.10.2026** (скрипт `scripts/verify_asr_space_wer.py`, test-сплит KSC): уттер 0 — WER 6.7% (30 слов, 2 ошибки), уттер 1 — WER 3.0% (33 слова, 1 ошибка), micro 4.76% на 63 словах. Текст читаемый; типовые ошибки — падежные окончания и лексика (`ministr` → `ministrler`, `potencialǵa` → `potencialına`). После 2 анонимных прогонов Space отдал `ZeroGPU quota exceeded`.

## Корпуса речи

- **atikuwu/karakalpak-speech-corpus (KSC)** — 106.92 ч, 21 702 записи, 200+ дикторов, CC-BY-4.0, Apache Parquet со встроенным аудио, сплиты стратифицированы по дикторам: train 96.3 ч / val 5.3 ч / test 5.3 ч. Поля: `id`, `audio`, `text`, `raw_text`. Собирался краудсорсинг-ботом командой школы им. аль-Хорезми (Нукус) на школьной RTX 5060 Ti 16GB.
- `kaa-ml/karakalpak-audio-dataset` — MIT, 1K-10K, но **gated** (нужна авторизация).
- Публикации: zenodo.org/records/19079670, cyberleninka (KSC paper), Mendeley data 2th8jvft8f.

## MT — перевод

- **tahrirchi/dilmash** — NLLB-200-distilled-600M, дообучен на kaa↔ru / kaa↔uz / kaa↔en, по 100 000 пар на пару. Варианты: `dilmash`, `dilmash-raw`, `dilmash-til` (лучший — til, +2.71 BLEU на en-kaa). Корпус: `tahrirchi/dilmash`.
- **google/madlad400-3b-mt** — тег `kaa` в карточке, есть GGUF-кванты (`model-q4k.gguf`) → работает на CPU без GPU.
- Google Translate каракалпакский **не поддерживает** (подтверждено в статье OLDI/WMT24). NLLB-200 без дообучения даёт что-то только если подсунуть каракалпакский как узбекский.
- Проприетарный сервис: `from-to.uz`.
- Конвертеры кириллица/старая латиница → текущая латиница: `github.com/tahrirchi/kaa-scripts`.

## TTS — синтез речи

- **Quyashbek/karakalpak-omnivoice** — на базе k2-fsa/OmniVoice (Qwen3-0.6B), ~6 ч каракалпакской речи, 5000 шагов, **обучение 51 минута**, поддерживает клонирование голоса.

## OCR — документы

- `davron112/kaa-karakalpak-ocr` — Tesseract `kaa.traineddata`, латиница.
- `kaa-ml/tesseract-kaa-cyrl` — Tesseract, кириллица.

## Текстовые корпуса и LLM

- `bekan/karakalpak_corpus_v2_m` — моно-корпус 1M-10M предложений, JSONL, MIT.
- `bekan/english_karakalpak_parallel_corpus_v5…v10` — параллельные en-kaa корпуса.
- `jafarisbarov/KarakalpakMMLU` — gated.
- `kdrnyzv890/qwen2.5-3b-karakalpak-base` — LoRA (r=16, alpha=32) поверх Qwen2.5-3B, continued pretraining на ~150 МБ текста, ~0.3 эпохи, **только text completion, не instruct**. Автор просит GPU-кредиты на продолжение.
- `Musadanebaev/karakalpak-qwen2.5-7b-instruct`, `kdrnyzv890/gsm8k-karakalpak-latn` — карточки почти пустые, качество не подтверждено.

## Стоимость

- Факт из карточки: whisper-medium на 107 ч = **8 часов на RTX 5060 Ti 16GB**. Аренда 4090: RunPod $0.34/ч (Community) / $0.74 (Secure) → прогон **$3-6**. Kaggle T4×2 16 ГБ, ~30 ч/нед — бесплатно.
- Инференс держать локально на слабом сервере нельзя: Whisper-medium это ~1.5 ГБ fp16 + torch; для VPS с 4 ГБ RAM не вариант — аренда GPU на часы либо HF с токеном.

## Кто делает

- **Atabek Kadirbergenov** — автор KSC и whisper-medium-karakalpak. Школа им. аль-Хорезми, Нукус. Telegram `@atik_uwu`, github.com/AtabekKadirbergenov. Прямой контакт по дообучению под свой домен.
- **tahrirchi** — узбекская команда, MT и лингвистические данные для тюркских языков.
- **Quyashbek Allanazarov** — ASR/TTS-модели, New Uzbekistan University + Xalq Banki AI Lab.

## Первоисточники

- arxiv.org/abs/2409.04269 — Open Language Data Initiative: MT for Karakalpak (FLORES+ devtest, 300k пар, сравнение dilmash / NLLB / Claude 3.5 / Google Translate)
- huggingface.co/datasets/atikuwu/karakalpak-speech-corpus — карточка KSC
- huggingface.co/atikuwu/whisper-medium-karakalpak — карточка модели с таблицей сравнения
