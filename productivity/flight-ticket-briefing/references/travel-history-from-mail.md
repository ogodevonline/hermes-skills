# Reconstructing someone's border crossings from mail (days abroad / ВНЖ)

Use when asked «сколько ей ещё можно отсутствовать», «даты выездов за год» (ВНЖ notification needs all exits), «когда она прилетала».

## Rule to compute against
- 115-ФЗ ст. 9 п. 1 пп. 11: ВНЖ is annulled if the holder was outside RF **more than six months summed within a calendar year** (Jan 1 – Dec 31). Exceptions: emergency treatment, own grave illness, death of a close relative abroad, business necessity — only with documents.
- The law says «шесть месяцев», not a day count: give a range (≈181–184 days) and a safe margin, say the exact conversion is not confirmed.
- Also note pp. 15: no annual residence notification for any 2 consecutive calendar years → annulment.

## Procedure
1. Gmail (svaaugust), `in:anywhere`, by passenger Latin name from tickets: Лима = `SHARIPOVA KHURLIMAN` (also try Cyrillic + nickname). Then by sender: `from:pobeda OR from:kupibilet OR from:aviasales OR from:uzairways OR from:aeroflot OR from:clickavia OR from:onetwotrip` with `after:` = start of previous year (the entry before Jan 1 matters).
2. Extract each leg: route, local date/time. Fast sources: kupibilet bodies embed schema.org `FlightReservation` JSON (`underName`, airports, `departureTime`); aviasales «Ваш билет готов» lists passenger + route; Pobeda «изменение времени» notices state flight no., date and route.
3. A «возврат» mail does NOT mean the flight was cancelled — compare refunded amount with order price (a 2 000 ₽ refund on a 9 500 ₽ order = only the paid seat). Confirm the flight happened via later signals: check-in-open mail, user forwarding the ticket on the eve.
4. Build the timeline: last entry before Jan 1 → each exit/entry in the year → planned exit. Days abroad = sum of (entry − exit). Remaining = limit − used − planned future absence.
5. State the gap explicitly: tickets bought outside this mailbox (by her, by family, ground crossings) are invisible — ask for passport stamps or permission to search chats before calling the number final.
6. Reading the user's Telegram chats needs his explicit OK for that search; if the approval prompt times out, stop and ask — do not retry another way.
