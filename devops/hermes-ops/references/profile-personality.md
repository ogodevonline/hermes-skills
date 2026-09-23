# Profile Personality (SOUL.md)

Set up or update SOUL.md (persona/character) for a Hermes profile.

## Profiles

- **Default profile:** `~/.hermes/SOUL.md`
- **Named profile:** `~/.hermes/profiles/<name>/SOUL.md`

## Procedure

### 1. Check current state
```bash
# Default:
ls -la ~/.hermes/SOUL.md ~/.hermes/persona.md 2>/dev/null
hermes profile show default 2>&1 | grep -i soul

# Named:
ls -la ~/.hermes/profiles/<name>/SOUL.md ~/.hermes/profiles/<name>/persona.md 2>/dev/null
hermes profile show <name> 2>&1 | grep -i soul
```

### 2. Source data — persona.md (if exists)

If `persona.md` exists in the same directory, it's a ready-made persona
(from migration or legacy setup).

**Action:** simply copy:
```bash
# Default
cp ~/.hermes/persona.md ~/.hermes/SOUL.md

# Named
cp ~/.hermes/profiles/<name>/persona.md ~/.hermes/profiles/<name>/SOUL.md
```

**Do NOT write SOUL.md from scratch** if persona.md exists — it already
contains the configured persona with all instructions (coach mode, problem
protocol, memory/profile runtime markers, etc.).

### 3. If persona.md is absent — build SOUL.md from scratch

Ask the user:
- Language for the profile
- Style: business, friendly, formal, technical
- Special requirements (coach mode, protocols, output format)
- Use existing instructions from another profile as reference?

Write result to SOUL.md. Format: markdown with optional YAML header.

### 4. Clean up duplicates

After copying persona.md -> SOUL.md, delete persona.md:
```bash
# Default
rm ~/.hermes/persona.md

# Named
rm ~/.hermes/profiles/<name>/persona.md
```

### 5. Verify
```bash
hermes profile show <name> 2>&1 | grep -i soul
# Should show: SOUL.md: exists
```

## Important

- SOUL.md is loaded fresh every session — no restart needed.
- SOUL.md may have runtime markers like `[memory will be injected here at runtime]` — these work identically in SOUL.md and persona.md.
- On CLI-to-gateway or gateway-to-CLI transition, SOUL.md is re-read automatically.

## Pitfalls

- **Don't write SOUL.md from scratch if persona.md exists.** User already configured it. Copy, don't invent.
- **Don't delete persona.md before verifying.** Copy first, confirm `hermes profile show` sees SOUL.md, then delete.
- **Don't confuse default and named profile paths.** Default is `~/.hermes/SOUL.md`, NOT `~/.hermes/profiles/default/SOUL.md`.