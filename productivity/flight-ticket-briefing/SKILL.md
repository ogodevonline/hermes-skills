---
name: flight-ticket-briefing
description: Use when найти билет в почте и объяснить вылет пассажиру.
---

# Flight ticket briefing

Class: someone (Василий or a relative/близкий) flies; find the ticket, extract the facts, verify the schedule, answer "когда вылет / печатать ли / во сколько быть", and produce a ready-to-forward message + the ticket file.

## Procedure

1. **Find the ticket in mail** (skill `google-workspace`, account svaaugust):
   - Search `in:anywhere` from the start — agency/airline mail often sits in SPAM.
   - Query by passenger name (Latin + Cyrillic + nickname), by city/IATA (`Nukus OR Нукус OR NCU`) and by sender (`from:onetwotrip`, aviasales, airline).
   - Agency reminder mails ("ваш скорый перелёт") point to the order; then open the order mail itself.
2. **Download attachments** with `google-workspace/scripts/gmail_attachments.py` and read the PDFs via read_file. Primary source = airline's itinerary receipt (fare name, seat selection, baggage, PNR, ticket no.), not the agency HTML.
3. **Verify the schedule before giving times.** Ticket times are fixed at purchase; airlines move flights by season/weekday.
   - FlightAware page parsed via curl — see `references/schedule-verification.md`.
   - Compare same-weekday past flights with the ticket time; if they differ, also search mail for a schedule-change notice («изменение расписания», from airline/agency) and tell the user to confirm in airline «Управление бронированием» (surname + ticket no.).
   - A fresh agency/airline reminder mail sent 1–2 days before departure («ваша поездка послезавтра», time «по местному времени») is generated from the live booking — treat it as confirmation of the time; FlightAware history from a different weekday does not override it.
   - Do NOT tell the passenger "быть в аэропорту в X" until the time is verified — do this check BEFORE drafting the forwardable message, not after.
4. **Check-in / printing rules** — from the airline's official page, per departure airport (Pobeda: `references/pobeda-checkin.md`). Decide from fare: no seat selected → no online check-in → desk check-in, boarding pass printed at the desk, nothing to print at home.
5. **Arrival-at-airport time** = desk opening time per airline rules (not the agency's generic "за 3 часа на международные") minus ~30 min buffer for entrance screening.
6. **Deliver**: ready-to-forward message + `MEDIA:` ticket PDF. Writing to the passenger directly (Telegram/email) only after the user's OK on the text.

## Output rules (user preferences)

- **All times in the departure city's local time**, labelled («по нукусскому»). Arrival in arrival-city local time. Never lead with a MSK conversion — a parenthetical "= 07:45 МСК" gets read as the departure time. Mention MSK only if asked.
- Give the passenger a timeline: приехать → регистрация откр. → закр. → посадка закр. → вылет.
- "Печатать?" — yes/no first, separately for itinerary receipt vs boarding pass, then the source link.
- Forwardable message: short, emoji bullets, flight no., date, local times, documents, baggage limits, PNR — a plain block the user copies whole.
- Low-cost basic fares: always state the cabin-bag size limit and that checked baggage is not included.
