# Token & Cost Tracking

Hermes stores per-session token usage and estimated cost in `state.db` (table `sessions`). This is useful for monitoring spending, debugging pricing discrepancies, and understanding which models/profiles consume the most.

## Data Location

```
~/.hermes/state.db  →  table: sessions
```

Key columns:
- `model` — model ID string (e.g. `deepseek/deepseek-v4-flash`)
- `input_tokens` — non-cached input tokens (prompt total minus cache)
- `output_tokens` — completion tokens
- `cache_read_tokens` — tokens served from prompt cache
- `cache_write_tokens` — tokens written to cache
- `reasoning_tokens` — reasoning/thinking tokens (if supported)
- `api_call_count` — number of API calls in the session
- `estimated_cost_usd` — cost calculated from provider's published pricing
- `actual_cost_usd` — actual billed cost (often NULL; provider-dependent)
- `cost_status` — `estimated`, `unknown`, or `actual`
- `started_at` — Unix timestamp (float with microseconds)

## Useful Queries

### Today's usage by model

```sql
SELECT model,
       SUM(input_tokens) as input,
       SUM(output_tokens) as output,
       SUM(cache_read_tokens) as cache_read,
       SUM(COALESCE(api_call_count, 0)) as api_calls,
       COALESCE(SUM(estimated_cost_usd), 0) as cost,
       COUNT(*) as sessions
FROM sessions
WHERE date(CAST(started_at AS INTEGER), 'unixepoch') = date('now')
GROUP BY model
ORDER BY cost DESC;
```

Note: `started_at` is a float, so cast to INTEGER before passing to `unixepoch`.

### Last N sessions

```sql
SELECT id, model, started_at,
       datetime(CAST(started_at AS INTEGER), 'unixepoch') as dt,
       input_tokens, output_tokens, cache_read_tokens,
       estimated_cost_usd, api_call_count
FROM sessions
ORDER BY started_at DESC
LIMIT 10;
```

### Cost by day (last 30 days)

```sql
SELECT date(CAST(started_at AS INTEGER), 'unixepoch') as day,
       SUM(input_tokens) as input,
       SUM(output_tokens) as output,
       SUM(cache_read_tokens) as cache_read,
       COALESCE(SUM(estimated_cost_usd), 0) as cost,
       COUNT(*) as sessions
FROM sessions
WHERE started_at > strftime('%s', 'now') - 30 * 86400
GROUP BY day
ORDER BY day;
```

## Pricing Data Source

Hermes estimates cost via `agent/usage_pricing.py`:

1. Resolves billing route from model name + provider
2. For custom providers with a `base_url` (like Kilo Code), fetches pricing from `GET {base_url}/models`
3. Falls back to built-in lookup tables for known providers (OpenAI, Anthropic, DeepSeek, OpenRouter)
4. Calculates: `tokens × cost_per_million / 1,000,000`

**Pricing discrepancies** between `estimated_cost_usd` and actual billing are common when:
- The provider applies gateway surcharges (Kilo Code, OpenRouter markup)
- Cache write pricing is missing from the API response
- The provider's `/models` endpoint returns different prices than the user's billing tier

## Slash Command

The TUI/gateway provides `/usage` which shows the current session's token breakdown:
- Input / Output / Cache read / Cache write / Reasoning tokens
- API call count
- Context utilisation percentage

This reads from the active agent's `session_*_tokens` attributes (populated per API call).
