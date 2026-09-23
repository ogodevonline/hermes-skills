# Китайские/азиатские новеллы на английском — подбор по сложности

Проверено 08.2026. Для Василия: чтение на английском как прокачка языка. Сначала уровень-тест, потом подбор яруса.

## Источники-подборки
- **novelqi.com/guide/best-chinese-novels-for-beginners** — «10 Best Chinese Novels for Absolute Beginners» (главы, жанры, качество перевода)
- **lilnovel.com/post/top-10-must-read-chinese-web-novels-for-beginners** — ещё 10, с описаниями
- **novelupdatesforum.com/threads/easy-to-read-chinese-novels-or-manhua.25628** — советы читателей: slice of life проще; TJSS (автор) — простой вокабуляр; современный сеттинг легче xianxia; 1/2 Prince хвалят как лёгкую
- **novelupdates.com** — каталог/рейтинги (фильтр language: chinese)

## 🟢 Лёгкий язык (A2-B1) — старт
| Новелла | Жанр | Глав | Почему легко |
|---|---|---|---|
| The King's Avatar (全职高手) | Киберспорт, комедия | 1 728 | Современный мир, бытовая лексика, без культивационных терминов |
| Release That Witch (放开那个女巫) | Фэнтези, стройка | 1 498 | ГГ-инженер объясняет простыми словами, повторяющиеся конструкции |
| Bringing the Nation's Husband Home | Романтика, драма | ~700 | Современная бытовая жизнь, простые диалоги |
| Coiling Dragon (盘龙) | Xuanhuan | 806 | Западный сеттинг, короткие главы (~2000 слов), классика входа в жанр |

## 🟡 Средний язык (B1-B2)
| Новелла | Жанр | Глав | Комментарий |
|---|---|---|---|
| Tales of Demons and Gods (妖神记) | Xuanhuan | 500+ | Очень короткие главы (~1000 слов), термины повторяются — быстро запоминаются |
| A Will Eternal (一念永恒) | Xianxia, комедия | 1 315 | Юмор, проще остальных Er Gen |
| 1/2 Prince | VR-MMO, комедия | ~450 | На форумах советуют именно для начинающих |
| I Shall Seal the Heavens (我欲封天) | Xianxia | 1 614 | Лучшая в жанре, но много культивационных терминов |

## 🔴 Сложный язык (C1+) — отложить
- **Lord of the Mysteries** (诡秘之主) — викторианский английский + лавкрафтовские термины
- **Reverend Insanity** (蛊真人) — плотный, философский язык

## Где читать онлайн бесплатно
- **readnovelfull.com** — полные главы; URL-паттерн `https://readnovelfull.com/<novel>/chapter-N-<title>.html` (рабочий пример: the-kings-avatar/chapter-1-the-banished-battle-god.html)
- **novelfull.com**, **freewebnovel.com** — онлайн-читалки с полными главами
- **wuxiaworld.com** — оригинальные лицензионные переводы (часть глав платная/по подписке)
- **novelupdates.com** — каталог: где какая новелла переводится

## Скачать оффлайн (EPUB) — GitHub chazzam/wordpress-epub (проверено 08.2026)
Готовые EPUB английских переводов лежат в репо **github.com/chazzam/wordpress-epub**, прямой raw-URL:
```
curl -sL -o novel.epub "https://github.com/chazzam/wordpress-epub/raw/master/epubs/Tales-of-Demons-and-Gods.epub" -A "Mozilla/5.0" --max-time 120
```
- Имя файла = `epubs/<Novel-Name>.epub` (Tales-of-Demons-and-Gods.epub: 1.2 МБ, 253 главы, перевод wuxiaworld-качества).
- Другие названия — искать: `web-tools search "<name> EPUB github"` (репо chazzam/wordpress-epub) или `"<name> epub download english free"` (oceanofpdf.com — PDF/EPUB c1-490, armaell-library.net, mp4directs.com).
- **Проверка EPUB после скачивания:** `file x.epub` → `EPUB document` (не HTML); `unzip -o x.epub -d check && find check -name "*.xhtml" | wc -l` → число глав; глянуть 1-ю, среднюю и последнюю главы — чистый текст без рекламы/403-мусора; последняя глава часто ПУСТАЯ заглушка (`<section>` без текста) — это нормально.
- **Доставка:** sendDocument с MIME `application/epub+zip`, НЕ через MEDIA (навык telegram-file-delivery).

## Формат чтения для Василия (Android, НЕ iPhone)
- Читалка: **ReadEra** (бесплатно, без рекламы) или Moon+ Reader — тап по слову = мгновенный перевод (Google Translate / системный переводчик Android).
- ⚠️ Василий явно отказался выписывать незнакомые слова агенту («дорого по времени»). Формат чтения новелл — тап-перевод в читалке, НЕ интерактивный vocab-разбор как в уроках /english.
- Если он всё же кидает слова — объяснять по-английски + перевод (как в уроках), но не навязывать.

## Уровень чтения Василия (замер 08.2026)
- Реальный уровень чтения: **уверенный B1 → тянет к B2** (официальный A2 в конфиге занижен). Сюжет понял ~90%, самооценка 60-80% — скромная.
- Слабое место: **идиомы и менее частотная лексика** (conveying, tugged at her sleeve, took delight in his misfortune, ingrained, inferior, casually) — это слова B2.
- Вывод протокола: подбирать 🟡 (Tales of Demons and Gods — короткие главы ~1000 слов, старт) или 🟢 (The King's Avatar — современный язык), 🔴 отложить.

## Pitfalls
- Reddit часто отдаёт 403 на extract (и old.reddit .json тоже) — не упорствовать, обсуждения брать с novelupdatesforum.com.
- Объём: 1 000-5 000+ глав это норма для китайских новелл; главы короткие (1 500-2 500 слов); медленный старт — судить минимум после ~50 глав.
- Скачивание английских переводов ОТРАБОТАНО (08.2026): GitHub chazzam/wordpress-epub — готовые EPUB, парсинг по главам не нужен. Для русских переводов — по-прежнему loghorizont (навык ranobe-download).
