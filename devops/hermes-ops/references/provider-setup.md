# Provider Setup

Add, switch, and test LLM providers in Hermes.

## Environment Variables

| Provider | Env var | Model |
|----------|---------|-------|
| KiloCode | `KILOCODE_API_KEY` | `deepseek/deepseek-v4-pro`, `deepseek/deepseek-v4-flash`, `qwen/qwen3.7-max` |
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-chat` (V3), `deepseek-reasoner` (R1) |
| OpenRouter | `OPENROUTER_API_KEY` | `anthropic/claude-sonnet-4`, `openai/gpt-4o`, etc. |

Full list: https://hermes-agent.nousresearch.com/docs/integrations/providers

## Adding a Provider

```bash
# 1. Add API key
echo 'DEEPSEEK_API_KEY=sk-your-key-here' >> ~/.hermes/.env

# 2. Switch model
hermes config set model.default deepseek-chat
hermes config set model.provider deepseek
hermes config set model.base_url https://api.deepseek.com

# 3. Verify
hermes chat -q "OK" -m deepseek-chat --provider deepseek
```

For named profiles, add `-p <profile>` to config set commands.

## Switching Providers

```bash
# Interactive (recommended)
hermes model

# Direct
hermes config set model.provider kilocode
hermes config set model.base_url https://api.kilo.ai/api/gateway
```

### Gateway Restart is Mandatory

`model.default` + `model.provider` is a **shared** setting for CLI and gateway.
After switching:

```bash
systemctl --user restart hermes-gateway
sleep 5 && systemctl --user status hermes-gateway | grep Active
```

Without restart, gateway continues using the old provider.

## KiloCode Naming

Use `deepseek/deepseek-v4-flash`, NOT `deepseek-chat`.
Format: `deepseek/deepseek-v4-flash`, `deepseek/deepseek-v4-pro`, `qwen/qwen3.7-max`.

### Discounted Endpoints (`:discounted` suffix)

Kilo Gateway offers discounted model endpoints via the `:discounted` suffix.
These route through cheaper provider tiers — prompts may be logged/used for
training by the upstream provider.

| Model ID | Discount | Prompt/1M | Completion/1M |
|----------|----------|-----------|---------------|
| `deepseek/deepseek-v4-flash:discounted` | >40% off | $0.14 | $0.28 |
| `deepseek/deepseek-v4-pro:discounted` | >80% off | $0.435 | $0.87 |

Switch to discounted:

```bash
hermes config set model.default deepseek/deepseek-v4-flash:discounted
```

**⚠️ Warning:** discounted endpoints log prompts/outputs — do not use for
sensitive data. The description says: *"your prompts and completions may be
retained and used to train or improve the provider's services."*

### Querying Kilo Gateway API

To check available models, pricing, and features without signing up:

```bash
curl -s "https://api.kilo.ai/api/gateway/models" | python3 -c "
import json,sys
data=json.load(sys.stdin)['data']
for m in data:
    mid=m['id']
    if 'deepseek' in mid.lower() and 'discounted' in mid.lower():
        p=m['pricing']
        print(f'{mid}  prompt=\${p[\"prompt\"]}/tok  comp=\${p[\"completion\"]}/tok')
"
```

Use this to discover new discounted models or verify pricing before switching.

## Per-Job Cron Model Override

Cron jobs snapshot their model at creation. After a provider change, update stale jobs:

```bash
hermes cron update <job_id> --model deepseek-chat --provider deepseek
hermes cron list | grep <job_id>
# model: deepseek-chat, provider: deepseek
```

## Key Check

```bash
grep "DEEPSEEK_API_KEY" ~/.hermes/.env
hermes chat -q "Hi" -m deepseek-chat --provider deepseek 2>&1 | grep "401\|Error\|OK"
```

## KiloCode Gateway Migration

See `references/kilocode-gateway-migration.md` — step-by-step migration from DeepSeek to KiloCode when DeepSeek times out.

## Profile Config Recovery

See `references/profile-config-recovery.md` — how to fix duplicate YAML sections caused by `patch` on profile configs.

## Pitfalls

- **DeepSeek API intermittently times out (30-270s).** Switch to KiloCode (`deepseek/deepseek-v4-flash`) which responds in ~1s via the same DeepSeek models.
- **KiloCode naming:** use `deepseek/deepseek-v4-flash`, NOT `deepseek-chat`.
- **DeepSeek keys start with `sk-`.** Keys from other providers won't work.
- **Do NOT patch `config.yaml` directly.** Use `hermes config set` (or read-merge-write with `write_file`). Patch creates duplicate YAML sections; the last one wins (silently empty).
- **Named profiles don't inherit `.env`.** Always copy: `cp ~/.hermes/.env ~/.hermes/profiles/<name>/.env`.
- **Always check all sections for duplicates after patching a profile config.** Run `grep -n "^section:" config.yaml` and `python3 -c "import yaml; print(repr(yaml.safe_load(open('config.yaml')).get('key')))"`.
- **`hermes profile create --clone` can hang for 60+ seconds.** Workaround: create the profile dir manually and copy config.yaml.
- **`.env` keys are not visible via `read_file`.** Use `grep` in terminal.
- **Verify every profile config change.** YAML validation + field-level repr check + duplicate check.