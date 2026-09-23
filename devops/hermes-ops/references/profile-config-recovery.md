# Profile Config Recovery — rescue from duplicate YAML sections

## The problem

`patch` inserts a new matching section but does NOT delete the old one. YAML's merge semantics mean the **last definition wins** -- so if a profile has:

```yaml
delegation:
  model: deepseek/deepseek-v4-flash
  provider: kilocode
  ...                     # <- my new section (line 5-9)
agent:
  max_turns: 30
  ...
delegation:
  model: ''
  provider: ''            # <- original empty section (line 23-28)
  api_key: ''
```

YAML reads the second `delegation:` block and uses empty values. Hermes gets `api_key: ''` even though the first block has `${KILOCODE_API_KEY}`.

## Detection

```bash
grep -n "^delegation:" ~/.hermes/profiles/researcher/config.yaml
# 5:delegation:
# 23:delegation:   <- TWO occurrences = problem
```

## Fix strategy

1. **Identify the duplicate** -- which line numbers
2. **Complex patch** -- replace from the FIRST occurrence of the old section through the LAST occurrence, keeping only the merged version
3. **Verify** -- `python3 -c "import yaml; print(repr(yaml.safe_load(open('config.yaml')).get('delegation', {}).get('api_key')))"` returns `'${KILOCODE_API_KEY}'`, not `''`

## Real example from researcher profile rescue (27 May 2026)

Original config had: `model:` (DeepSeek API), then `delegation:` (empty), then `agent:`, `toolsets:`, then another empty `delegation:`.

Patch added a new `delegation:` block above `agent:` -- creating **three** delegation references. YAML read the last (empty) one.

Fix: single patch replacing from the first `delegation:` through the end of `toolsets:` with the merged version containing only one `delegation:` block.

## Prevention

- For profile config edits with multiple sections, prefer `write_file` with the complete content (read the file first, merge in code, write back)
- If using `patch`, always grep for duplicates after each operation
- Always run `yaml.safe_load()` and check `repr()` on critical values before declaring done