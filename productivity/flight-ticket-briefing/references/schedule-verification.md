# Verifying a flight's real schedule

## FlightAware (works with plain curl, no browser)

```bash
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130 Safari/537.36" \
  "https://www.flightaware.com/live/flight/PBD732" -o fa.html
```

Parse — write the script to a file and run it (inline `python3 -c` / heredocs can stall on approval prompts):

```python
import json, re
from datetime import datetime, timezone, timedelta
d = json.loads(re.search(r"trackpollBootstrap = (\{.*?\});</script>", open("fa.html").read(), re.S).group(1))
loc = timezone(timedelta(hours=5))  # departure city's UTC offset
for fl in d["flights"].values():
    for f in fl.get("activityLog", {}).get("flights", []):
        dep = f.get("gateDepartureTimes", {}).get("scheduled")
        print(f["origin"].get("iata"), f["destination"].get("iata"), f.get("flightStatus"),
              datetime.fromtimestamp(dep, loc).strftime("%a %d.%m %H:%M") if dep else "-")
```

- activityLog = recent past flights; print the weekday — schedules often differ by weekday, compare the SAME weekday as the ticket.
- One same-weekday past flight at another time is NOT proof of a schedule change (could be a one-off or a different rotation). Before alarming the user, check mail for the agency pre-departure reminder (OneTwoTrip «Полезная информация по вашему скорому перелёту», often in SPAM): it is generated from the live booking 1–2 days before departure, so if it was sent after the deviating flight and shows the ticket time, the time stands. Only a schedule-change mail or the airline's «Управление бронированием» overrides it.
- ICAO prefixes: Pobeda PBD, Aeroflot AFL, Uzbekistan Airways UZB, S7 SBI, Utair UTA.
- flightradar24 answers 403 to scrapers; flypobeda.ru per-route pages 404.

## UTC offsets (no DST)

- Uzbekistan (Nukus, Tashkent, Samarkand): UTC+5
- Moscow: UTC+3 → Nukus is 2 h ahead of Moscow
