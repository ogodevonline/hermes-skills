# KiloCode Gateway Migration

## When to migrate

- DeepSeek API returns APITimeoutError (30-270s delays)
- Gateway hangs on retry loops, Telegram/Discord sessions freeze
- Subagents silently die because the parent DeepSeek call timed out

## Steps

```bash
# 1. Switch main model to KiloCode (use :discounted suffix for cheaper tier)
hermes config set model.default deepseek/deepseek-v4-flash        # regular price
hermes config set model.default deepseek/deepseek-v4-flash:discounted  # >40% off (prompts logged)
hermes config set model.provider kilocode
hermes config set model.base_url https://api.kilo.ai/api/gateway

# 2. (If not already set) Switch delegation too
hermes config set delegation.model deepseek/deepseek-v4-flash
hermes config set delegation.provider kilocode
hermes config set delegation.base_url https://api.kilo.ai/api/gateway
# delegation.api_key is ${KILOCODE_API_KEY} -- set in .env

# 3. Restart gateway
systemctl --user restart hermes-gateway

# 4. Verify
sleep 8 && systemctl --user status hermes-gateway | grep "Active"
```

## Effect

- KiloCode proxies deepseek models over their own infra
- Response time drops from 30-270s to ~1s
- No more timeout-related hangs on either gateway or subagents
- Use `deepseek/deepseek-v4-flash` (not `deepseek-chat`) -- different naming convention

## Diagnosis

```bash
# Check for timeouts in gateway
journalctl --user -u hermes-gateway --since "1 hour ago" | grep -i timeout

# Check current provider
python3 -c "import yaml; c=yaml.safe_load(open('/home/hermes/.hermes/config.yaml')); print(c['model'])"
```