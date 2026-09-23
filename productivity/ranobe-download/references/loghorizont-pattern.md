# loghorizont.ru — паттерн скачивания (рабочий пример 07.2026)

Новелла: «Слава Королю!» (Hail the King / 国王万岁, Mad Blade During Troubled Times), 1320 глав, перевод завершён.

## URL-паттерн файлов

Страница новеллы: `https://loghorizont.ru/slava-korolyu-3/`
Файлы: `https://loghorizont.ru/ranobe/Slava-Korolyu-/Slava_Korolyu__{from}_{to}.{ext}`

- TXT (в .zip): `Slava_Korolyu__1_500.txt.zip`, `501_1000`, `1001_1310`
- EPUB (без zip): `Slava_Korolyu__1_500.epub`, `501_1000`, `1001_1310`
- DOCX: `Slava_Korolyu__1_500.docx` …
- FB2 (в .zip): `Slava_Korolyu__1_500.fb2.zip` …

Формат имени: `{BookName}__{from}_{to}.{ext}`, каталог: `ranobe/{BookName}-/` (с дефисом на конце).

## Скачивание

```bash
curl -sL -o "part.txt.zip" "https://loghorizont.ru/ranobe/Slava-Korolyu-/$i.txt.zip" -A "Mozilla/5.0" --max-time 120
```

## Сборка и чистка

```bash
unzip -o -q "Slava_Korolyu__$i.txt.zip" -d "part_$i"
cat part_1/*.txt part_2/*.txt part_3/*.txt > FULL.txt
grep -c "^Глава" FULL.txt   # 1320
```

### Python-чистка рекламных блоков между частями
```python
import re
junk_patterns = [
    r"Друзья, если Вам понравилась книга, и работа нашей команды по созданию электронной книги \r?\nПоддержите Нас символической оплатой, даже если это будет 0\.1\$ / 1RUB или кликните на рекламу на сайте\.\r?\nНам будет очень приятно осознавать, что проделанная работа принесла Вам пользу, и наша команда старались не зря\.\r?\nПоблагодарить авторов и команду\. \(ссылка на раздел поддержать проект https://loghorizont\.ru/podderzhat-proekt/\)\r?\n?",
]
for p in junk_patterns:
    text = re.sub(p, "\n", text)
# Заголовки частей
text = re.sub(r"Ранобэ: .*? \r?\nОписание:.*?\r?\nКол-во глав: \d+-\d+\r?\n\r?\n", "\n", text, flags=re.S)
# Нормализация
text = text.replace("\r\n", "\n").replace("\r", "\n")
text = re.sub(r"\n{3,}", "\n\n", text)
```

### Футеры в конце каждой главы (1300+ повторений)
```bash
sed -i '/Отблагодаритьте нашу команду: https:\/\/loghorizont.ru\/podderzhat-proekt\//d' CLEAN.txt
```

### Проверка после чистки
```bash
grep -c "Отблагодаритьте нашу команду" CLEAN.txt   # должно быть 0
grep -c "^Глава" CLEAN.txt                          # 1320
```

## Заметки

- Итог: 78 611 строк, ~18.8 МБ (UTF-8, кириллица = 2 байта/символ; 10.6М символов).
- Доставка: TXT и EPUB через Telegram Bot API sendDocument (см. навык telegram-file-delivery).
- Файлы сохранены в `~/downloads/slava-korolyu/` (FULL + CLEAN + 3×epub + 3×zip).
