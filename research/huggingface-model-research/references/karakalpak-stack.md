# Каракалпакский (kaa): готовый открытый стек

Собрано 02.10.2026 через HF API + живая проверка. Язык: kaa, ~900 тыс. носителей,
Каракалпакстан (Узбекистан), латиница с диакритикой (`á ǵ ı ń ó ú`), близок к казахскому.

## ASR (аудио → текст)
**atikuwu/whisper-medium-karakalpak** — лучший по факту (не по обещаниям).
- whisper-medium (764M), Apache-2.0; обучен 6 эпох на Karakalpak Speech Corpus
- **~8 часов обучения на NVIDIA RTX 5060 Ti 16GB** (школьная лаборатория, Нукус)
- WER test **9.59%** (медиана 3.85%), val 8.37%, CER 4.03%
- Сравнение из карточки: mms-1b-all `kaa` 50.39% · Quyashbek/whisper-medium 65.29% ·
  wav2vec2-xls-r-300m 88.00% · whisper-medium zero-shot 91.27% · whisper-large-v3 zero-shot 97.75%
- Живая проверка 02.10.2026 через Space `atikuwu/whisper-karakalpak-asr`:
  2 примера из test → micro-WER **4.76%** (3/63 слова); транскрипт читаемый,
  ошибки типа `Ministr` → `Ministrler`. Дальше — ZeroGPU quota exceeded (анонимно).
- Демо: https://huggingface.co/spaces/atikuwu/whisper-karakalpak-asr

## Датасет
**atikuwu/karakalpak-speech-corpus** (KSC), CC-BY-4.0
- 106.92 ч, 21 702 записи, 200+ дикторов, OGG 16 kHz mono; сплиты 19 554 / 1 074 / 1 074
  (train/val/test), стратификация по дикторам
- есть `raw_text` с ненормализованным исходником — удобно для честного WER

## Перевод / MT (kaa ↔ ru/uz/en)
- **tahrirchi/dilmash** — NLLB-200-distilled-600M (600M!), дообучен на 100 000 пар
  на каждую пару; датасет `tahrirchi/dilmash`. Варианты: dilmash-raw, dilmash-til.
- **google/madlad400-3b-mt** — тег `kaa` в карточке, есть GGUF q2k/q3k/q4k → CPU-инференс.
- Google Translate каракалпакский НЕ поддерживает (подтверждено в статье WMT24/OLDI).
- FLORES+ devtest для kaa: 1012 предложений (OLDI shared task).

## TTS (ответ голосом)
**Quyashbek/karakalpak-omnivoice** — k2-fsa/OmniVoice (backbone Qwen3-0.6B), ~6 ч речи,
5 000 шагов, **обучение ~51 мин**, есть клонирование голоса.

## OCR
- `davron112/kaa-karakalpak-ocr` — Tesseract traineddata, латиница
- `kaa-ml/tesseract-kaa-cyrl` — кириллица

## Текстовые корпуса / маленькие LLM
- `bekan/karakalpak_corpus_v2_m` — моно-корпус (1M+ предложений, JSONL, MIT)
- `bekan/english_karakalpak_parallel_corpus_v5…v10` — параллельные корпуса
- `kdrnyzv890/qwen2.5-3b-karakalpak-base` — LoRA CPT (r16, 150 МБ текста, ~0.3 эпохи),
  обучение остановлено автором из-за отсутствия бюджета; SFT-фазы нет («Bawir AI»)
- `Musadanebaev/karakalpak-qwen2.5-7b-instruct` — карточка пустая, проверять перед ссылкой

## Авторы (полезно для дообучения под свои данные)
- Atabek Kadirbergenov — школа им. аль-Хорезми, Нукус: корпус KSC + whisper-medium-kaa,
  Telegram @atik_uwu, GitHub AtabekKadirbergenov
- Quyashbek Allanazarov — New Uzbekistan University / Xalq Banki AI Lab: whisper-*/wav2vec2/TTS
- tahrirchi (Узбекистан) — MT dilmash + параллельные корпуса

## Ограничение среды
На сервере Hermes GPU нет (nvidia-smi отсутствует), RAM 4 ГБ, свободно ~15 ГБ диска:
локальный инференс whisper-medium нецелесообразен. Рабочие варианты — аренда GPU по часам
(RunPod 4090 от $0.34/ч), HF с токеном или отдельный VPS с GPU.

## Пайплайн «цифровой администратор»
Whisper-medium-kaa (слух) → dilmash или MADLAD-400 (перевод kaa↔ru) → дешёвая LLM на
русском (логика) → karakalpak-omnivoice (ответ голосом). Всё открытое, стоимость = только
инференс.
