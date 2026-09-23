# KiloCode Models (discovered 2026-05-27)

KiloCode gateway (`api.kilo.ai/api/gateway`) provides 345+ models through one API key (`${KILOCODE_API_KEY}`). Use as provider with base_url.

## Claude models available

| Model ID | Price in/out per 1M tokens | Use case |
|---|---|---|
| `anthropic/claude-sonnet-4.6` | $3 / $15 | Skill improvement, refactoring, analysis (smart tasks) |
| `stealth/claude-sonnet-4.6` | $2.40 / $12 | Same but cheaper (stealth provider) |
| `anthropic/claude-opus-4.7` | $5 / $25 | Max quality, architecture decisions |
| `anthropic/claude-sonnet-4.5` | $3 / $15 | Fallback if 4.6 is overloaded |
| `anthropic/claude-haiku-latest` | $1 / $5 | Fast/cheap claude, good for quick analysis |
| `~anthropic/claude-sonnet-latest` | $3 / $15 | Auto-latest sonnet |
| `~anthropic/claude-opus-latest` | $5 / $25 | Auto-latest opus |
| `anthropic/claude-opus-4.6` | $5 / $25 | Previous opus |
| `anthropic/claude-3.5-haiku` | $0.80 / $4 | Legacy haiku |

## Auto-models (router)

| Model ID | Routes to | Price |
|---|---|---|
| `kilo-auto/frontier` | Claude (best) | $5 / $25 |
| `kilo-auto/balanced` | Alibaba Qwen | $0.33 / $1.95 |
| `kilo-auto/free` | Rotating free models | $0 |

## Fast/cheap models (for worker, research)

| Model ID | Price | Notes |
|---|---|---|
| `deepseek/deepseek-v4-flash` | $0.13 / $0.27 | Current main model, 1M context |
| `deepseek/deepseek-v4-pro` | $1.61 / $3.22 | Better quality, same family |
| `google/gemini-3.1-flash-lite` | $0.25 / $1.50 | Cheaper alternative |
| `x-ai/grok-4.20` | $1.25 / $2.50 | Alternative fast model |

## Config example (for Kanban profile)

```yaml
model:
  default: anthropic/claude-sonnet-4.6  # or deepseek/deepseek-v4-flash
  provider: kilocode
  base_url: https://api.kilo.ai/api/gateway

delegation:
  model: deepseek/deepseek-v4-flash  # sub-agents use fast model
  provider: kilocode
  base_url: https://api.kilo.ai/api/gateway
  api_key: ${KILOCODE_API_KEY}
```