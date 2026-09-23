# Электронные библиотеки — справочник (проверено 08.2026)

## Флибуста (русские книги, fb2/epub)

- OPDS поиск книг: `https://flibusta.is/opds/search?searchType=books&searchTerm=<query>` (URL-encoded, `+` вместо пробелов)
  - ⚠️ Без `searchType=books` OPDS возвращает только ссылки-заглушки «Поиск авторов/Поиск книг» — пусто.
- Поиск авторов: `searchType=authors` → `<entry><id>tag:author:<id>` → книги автора: `https://flibusta.is/opds/author/<id>/alphabet` (страница с прямыми ссылками на файлы).
- Прямые файлы: `https://flibusta.is/b/<book_id>/fb2` | `/epub` | `/mobi` | `/txt` | `/html`.
- **fb2 отдаётся как zip-архив** (`Zip archive data`) → `unzip -o -q file.fb2 -d dir` → внутри `.fb2` (XML). Проверять `file`.
- Парсинг: `python3` + regex `<book-title>`, `<author>`, `<annotation>` (внутри fb2 — аннотация прямо в файле).
- Зеркала (08.2026): `flibusta.is` ✅ 200, `flibusta.site` ✅ 200; `flibusta.net/lib/online` ❌ 000.

Пример: The Indigo Girl → «Девушка индиго» → `/b/732916/fb2` → zip → `Boyd_Devushka-indigo.*.fb2`.

## Libgen.li (английские + русские)

- Поиск: `https://libgen.li/index.php?req=<query>` — HTML-таблица. Строки содержат `edition.php?id=<id>` и `md5`-хэши.
- Скачивание по md5 (ключ одноразовый):
  1. `curl "https://libgen.li/ads.php?md5=<MD5>"` → grep `get\.php\?md5=[a-f0-9]{32}&key=[A-Z0-9]+`
  2. `curl -sL "https://libgen.li/<полный get.php...>" -H "Referer: https://libgen.li/" -o out.epub`
- **`503 Service Temporarily Unavailable`** от get.php → ключ протух/сервер перегружен: заново запросить ads.php (новый key), пауза 10–15с, до 3 попыток.
- Всегда проверять `file` после скачивания: HTML = 503/challenge, а не файл.
- **IPFS-шлюзы из edition.php** (`cloudflare-ipfs.com`, `gateway.ipfs.io`, `gateway.pinata.cloud`) в этом окружении недоступны (DNS 000 / HTTP 403) — не тратить время, сразу get.php.
- Зеркала: `libgen.li` ✅; `libgen.is/rs/st/gs` ❌ 000; `libgen.lc` ❌ «domain may be for sale».
- JSON API `/json.php` требует request keys — не использовать, идти через HTML.

## Anna's Archive

- `annas-archive.li` / `.rs` — fingerprint JS challenge для curl (редирект с `tr_uuid`, FingerprintJS). Браузер тоже застревает на challenge (страница только ToS/Privacy). Fallback, не основной путь.
- `en.annas-archive.gl/md5/<md5>` — используется как зеркало ссылок libgen, тоже под challenge.

## archive.org (общественное достояние)

- `https://archive.org/details/<slug>` → кнопка Download (epub/pdf/djvu). Для книг до ~1928.
- Пример: Lady Hancock (1900, M. E. Springer) — `archive.org/details/ladyhancockasto00cogoog`.

## Сайты с прямыми файлами (русские)

- `topliba.com/books/<id>` → прямая ссылка `/files/<file_id>/fb2` (работает, проверено 08.2026).
- `fb2.top/<slug>` — онлайн-чтение + жанры книги («Эротическая литература», «Любительский перевод») — удобно для проверки, что книга подходит по запросу.
- `librusec.site`, `litmir.club`, `rulit.me` — запасные.

## Доставка в Telegram

- fb2: `sendDocument`, MIME `application/x-fictionbook+xml` (curl `-F document=@file -F filename=...`).
- EPUB: `sendDocument`, MIME `application/epub+zip`.
- НЕ через MEDIA (MEDIA — только изображения/аудио/видео). Подробности: `telegram-file-delivery`.

## Русские переводы западных книг — стратегия

- Свежие книги (2023–2025) на русском почти всегда отсутствуют (Флибуста/Libgen пусто) — проверить 2–3 источника и прекратить.
- Честно сказать пользователю + предложить аналог: переведённая серия того же автора, та же эпоха/жанр.
- Пример: The Gilded Heiress (Joanna Shupe, 2025) → рус. аналог «Охота на наследницу» (Джоанна Шуп, серия «Мятежницы Пятой авеню», эротический роман, Позолоченный век/Нью-Йорк) — fb2 на topliba.com.
- Пользовательский контекст: книги ищутся для чтения на телефоне (ReadEra/Moon+), русские версии приоритетны, английские — по запросу «тоже скинь».

## Жанровая карта: «spicy historical про бизнес/самодостаточную женщину» (на русском)

Запрос (08.2026, для девушки): весёлый/откровенный исторический роман, много секса и «извращений», самодостаточная женщина, бизнес/успех, старые времена.

| Автор | Книга на русском | Где брать | Что внутри |
|-------|------------------|-----------|------------|
| Джоанна Шуп | «Охота на наследницу» (серия «Мятежницы Пятой авеню») | topliba `/books/1017722` → `/files/649165/fb2` | Gilded Age, Нью-Йорк, наследница + повеса, эротика. Остальные книги Шуп на русском НЕ переведены |
| Лиза Клейпас | «Дьявол весной» | topliba `/books/703514` → `/files/117988/zip` (внутри fb2); fb2.top 537953 | Викторианская Англия, героиня-изобретательница (настольная игра = свой бизнес), весёлый, spicy |
| Тесса Дэр | «Хотите быть герцогиней?» | Флибуста `/b/577850/epub` | Викторианская Англия, героиня-портниха со своим ателье, очень весёлый, spicy |

Приёмы поиска: русское название часто НЕ совпадает с английским (The Duchess Deal = «Хотите быть герцогиней?», Devil in Spring = «Дьявол весной», The Heiress Hunt = «Охота на наследницу») — искать по обоим; жанры fb2.top («Эротическая литература», «Любительский перевод») — маркер spicy / фанатский перевод; yandex-запрос `<автор> <название> скачать fb2`.
