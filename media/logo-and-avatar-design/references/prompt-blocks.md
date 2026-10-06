# Блоки промптов для логотипа/аватарки

Промпт собирается из блоков: **объект (знак)** → `LAYOUT` → `PALETTE` → `WORDS`. Язык промпта —
английский; русский текст только в кавычках.

## LAYOUT

Аватарка (квадрат):

```
Square 1:1 app avatar. The mark is centred horizontally in the upper part and occupies
about 45 percent of the square; immediately beneath it the wordmark in bold geometric
sans-serif; together they fill most of the frame with tight balanced spacing, no wide
empty margins, nothing else in the image.
```

Горизонтальный лок-ап (сайт, шапка, презентация):

```
Horizontal logo lockup: the mark on the left, the wordmark on the right in a single line,
centred lockup, generous breathing room around it.
```

Плитка-иконка:

```
A rounded-square app tile filling the frame; a minimal white mark in the upper part and the
wordmark beneath it.
```

## PALETTE

```
PROD: full-bleed deep indigo background, the mark in pure white with a single cyan accent,
the wordmark in pure white.

DEMO: full-bleed near-black graphite background, the mark in amber-orange with a single
light accent, the wordmark in pure white, and directly under the wordmark a small rounded
amber-orange pill containing the single word DEMO in dark capitals.
```

Светлые версии — та же раскладка, фон `clean white background`, знак индиго, вордмарк
`dark navy`.

## WORDS

```
The wordmark is spelled EXACTLY <Name> - capital L, capital P, one word, no spaces. Crisp
professional typography, correct letterforms. Flat vector, clean edges, high contrast,
no watermark, no signature, no mockup, no photorealism.
```

Для латиницы и кириллицы перечислять словами, какие буквы заглавные. Строку не опускать:
без неё модели переставляют и теряют буквы.

## Запреты (в конце промпта)

```
no photorealism, no mockup, no watermark, no signature, no 3D, no glow, no gradients
```

## Проверенные знаки

Календарь с галочкой, звонок ресепшена, отрывной талон, песочные часы, пузырь с галочкой, пин
с календарём, монограмма из инициалов, выдвинутый сектор времени, закладка, стрелка в
негативном пространстве, кнопка-закрепка. Список — чтобы не повторять один и тот же знак в
новой партии.

## Арт-директор

Когда свои промпты дают клише — отдать бриф сильной текстовой модели: назначение, где живёт
лого, что уже забраковано, примеры уровня вкуса (Linear, Duolingo, Cal.com, Figma). Требовать
строго JSON:

```json
{"concepts":[{"id":"k1","name":"...","idea":"одно предложение","why":"почему работает
  иконкой","palette":["#hex"],"demo_variant":"чем отличается демо",
  "image_prompt":"60-90 слов английского промпта"}]}
```

Затем сгенерить все `image_prompt` одним батчем и отдать пользователю с названиями концептов.
