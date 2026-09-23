# Aviasales Data API (Travelpayouts)

Free API for exact flight prices. No approval needed — just register at travelpayouts.com and get a token.

## Token

Stored in `~/.hermes/.env` as `AVIA_API_TOKEN`.

## Endpoint

```
GET https://api.travelpayouts.com/aviasales/v3/prices_for_dates
```

### Parameters

| Param | Type | Example | Description |
|-------|------|---------|-------------|
| `origin` | IATA | `MOW` | Departure city code |
| `destination` | IATA | `NCU` | Arrival city code |
| `departure_at` | date | `2026-07-13` | Departure date |
| `one_way` | bool | `true` | One-way search |
| `direct` | bool | `true` | Direct flights only |
| `currency` | string | `rub` | Currency |
| `token` | string | `***` | API token (from env) |
| `sorting` | string | `price` | Sort by price / route |

### Example request

```bash
curl -s "https://api.travelpayouts.com/aviasales/v3/prices_for_dates?\
origin=MOW&destination=NCU&\
departure_at=2026-07-13&\
one_way=true&direct=true&\
currency=rub&\
token=$AVIA_API_TOKEN"
```

### Response shape

```json
{
  "success": true,
  "currency": "rub",
  "data": [
    {
      "airline": "HY",
      "flight_number": "9626",
      "origin_airport": "VKO",
      "destination_airport": "NCU",
      "departure_at": "2026-07-13T09:30:00+03:00",
      "price": 9886,
      "transfers": 0,
      "duration": 210,
      "gate": "Uzbekistan airways",
      "link": "/search/MOW1307NCU1?..."
    }
  ]
}
```

### Purchase link

The `link` field is relative — prepend `https://www.aviasales.com` to get the full purchase URL:
```
https://www.aviasales.com/search/MOW1307NCU1?...
```

### Data freshness

Cached data (up to 7 days old). For real-time prices, use the Search API (requires approval). Data API is sufficient for price checking and comparison.

### Other useful endpoints

- **Month calendar:** `GET /v2/prices/month-matrix?origin=MOW&destination=NCU&month=2026-07-01&one_way=true&currency=rub&token=...`
- **Cheapest tickets:** `GET /v1/prices/cheap?origin=MOW&destination=NCU&currency=rub&token=...`

### Rate limits

See [Travelpayouts rate limits](https://support.travelpayouts.com/hc/en-us/articles/4402565416594). Conservative estimate: reasonable use for ad-hoc queries is fine.

## When to use

- Validating researcher output that returned vague price ranges
- Getting exact prices + purchase links for specific dates
- Supplementing web_search results with API-precise data
- Building comparison tables across dates

## Dedicated skill

A full skill exists at `search/aviasales-api` with complete endpoint docs, parameters, and fallbacks. Load it via:
```bash
hermes kanban create ... --skill aviasales-api
```

The skill is pre-loaded in the researcher profile's .env (`$AVIA_API_TOKEN`). For orchestrator: use this reference for quick lookup; the full skill has deeper detail including month-matrix, grouped_prices, and alternative sources (Yandex, UniTicket).

## When NOT to use

- For routes that don't exist in Aviasales data (obscure airlines, private jets)
- When you need real-time prices (use the Search API or airline website)