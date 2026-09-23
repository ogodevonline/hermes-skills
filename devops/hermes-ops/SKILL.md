---
name: hermes-ops
title: Hermes VPS Administration
category: devops
description: >-
  VPS operations for a Hermes instance: LLM provider setup & switching,
  memory pressure diagnostics & cleanup, profile personality (SOUL.md)
  configuration. The umbrella covering all server-side Hermes administration.
triggers:
  - user asks to add/change/switch an LLM provider or API key
  - user reports API timeouts (DeepSeek 30-270s delays), slow responses, frozen sessions
  - free -h shows less than 300 MB available or swap over 80%
  - user says "Hermes is slow" or "gateway not responding" or reports bot silence
  - user asks to restart gateway (systemctl --user hermes-gateway)
  - user asks about SOUL.md / persona.md / personality setup for any profile
  - user wants to create or configure a named profile
  - cron jobs failing with 401 / Authentication Error
  - cron jobs failing with Request timed out / provider timeout / "Fallback chain was exhausted" (LLM jobs down, no_agent jobs fine)
  - user reports a cron job ran at the wrong time / should not have run now
  - VPS has been running for over 1 week without maintenance
  - user discovers orphan MCP / codegraph processes
  - user reports persistent typing indicator («бот печатает» в Telegram) — likely a stuck worker
  - any task involving ~/.hermes/config.yaml edits
  - user wants a simple static text reminder without LLM tokens (no_agent pattern)
  - cron job for no_agent won't deliver on `run` — only scheduled execution delivers
  - user says "обнови Hermes" / "пора обновить hermes" / "hermes update"
  - user asks about remote desktop / desktop connect / how to connect desktop to VPS / can I talk from my computer
  - cloudflared tunnel down / DNS timeout / tunnel URL changed / need to expose local port via cloudflare
  - user asks about external memory hub / agent memory layer / TencentDB Agent Memory / LLM-proxy integration («добавь X, чтобы ты лучше работал»)
---

# Hermes VPS Administration

A Hermes VPS typically runs a gateway (systemd user service), one or more
named profiles, MCP servers (codegraph), and optionally a dashboard. This
skill covers the three most common maintenance domains.

---

## 1. LLM Provider Setup

**Full detail:** `references/provider-setup.md`

Add or switch between LLM providers (KiloCode, DeepSeek, OpenRouter, etc.).

**Quick-start:**
```bash
# Add key
echo 'KILOCODE_API_KEY=*** >> ~/.hermes/.env

# Switch model (for default profile — named profiles use --profile <name>)
hermes config set model.provider kilocode
hermes config set model.default deepseek/deepseek-v4-flash:discounted
hermes config set model.base_url https://api.kilo.ai/api/gateway

# Restart gateway
systemctl --user restart hermes-gateway
```

**Named profile model change (THREE fields must match):**
```bash
# For a named profile, ALL THREE model fields must be updated separately:
hermes --profile <name> config set model.default "deepseek/deepseek-v4-flash:discounted"
hermes --profile <name> config set agent.model "deepseek/deepseek-v4-flash:discounted"
hermes --profile <name> config set delegation.model "deepseek/deepseek-v4-flash:discounted"
# ℹ️ KiloCode: model ID без префикса провайдера (не kilo/...) — provider уже в model.provider.
#    :discounted суффикс даёт >40% скидку. Без суффикса — полная цена.
```

**Key lessons:**
- Provider = `model.provider`, model name = `model.default` (different naming conventions per provider).
- Named profiles do **NOT** inherit `.env` from the root -- copy keys manually.
- Cron jobs snapshot their model at creation time; update stale jobs explicitly with `hermes cron update <id> --model ... --provider ...`.
- Kilo Gateway offers `:discounted` model endpoints (e.g., `deepseek/deepseek-v4-flash:discounted`) — >40% off on Flash. Query `GET https://api.kilo.ai/api/gateway/models` for full model catalog with pricing. ⚠️ Discounted endpoints log prompts/outputs — not for sensitive data.
- Never use `patch` on `config.yaml` for multi-section changes — it creates duplicate YAML sections AND the protected-file guard refuses it, triggering retry loops. **Always use `hermes config set`** for any config.yaml change. If you need to change multiple keys, do them one by one with `hermes config set`.

---

## 1b. External LLM-Proxy / Memory Hub Integration (e.g. TencentDB Agent Memory)

**Full detail:** `references/tencentdb-agent-memory.md`

Когда пользователь спрашивает «можно ли добавить X, чтобы ты работал лучше» (внешний memory hub, LLM-прокси):

1. **Ищи официальную секцию интеграции с Hermes** в документации проекта (у TencentDB Agent Memory она есть — «Using Proxy with Hermes» в INSTALL.md: `model.provider: custom` + `base_url http://<proxy>:8096/hermes/<spaceId>` + `extra_headers` с x-team-id/x-agent-id/x-task-id/x-conversation-id).
2. **Проверь ресурсы машины ДО обещаний:** `which docker`, `free -h`, `df -h /`, `nproc`. Docker-стеки требуют установленного Docker.
3. **Оцени ROI честно** — сравни с встроенными memory / skills / session_search / gitmark. Для single-user Hermes внешние memory-хабы дублируют ~80% функций; реальный аддон только для multi-agent над одним кодом/доками.
4. **Не обещай установку без проверки** — если Docker отсутствует, сначала скажи об этом и предложи вариант (установить Docker / не ставить).
5. **Если пользователь решил ставить — протокол полного развёртывания в `references/tencentdb-agent-memory.md`** (проверено Aug 2026): установка Docker + обёртка `sg docker -c` (sudo в фоновых процессах Hermes падает), .env с KiloCode upstream, создание Team/Agent/Task через API (⚠️ 403 «caller is not resource owner» — admin не может создать с чужим owner_user_id), E2E-проверка (`hermes -z` + чтение .jsonl записей), ограничение: **KiloCode не поддерживает /embeddings → векторный поиск выключен, только BM25**.

---

## 2. Memory Pressure & Cleanup

**Full detail:** `references/memory-pressure.md`

When the 2 GB VPS runs low on memory, the gateway and subagents slow or fail.

**Quick diagnostic:**
```bash
free -h
ps aux --sort=-%mem | head -20
ps aux | grep -E 'codegraph|hermes.*gateway' | grep -v grep
```

**Common memory hogs:**
| Source | Size | Risk |
|--------|------|------|
| Old codegraph orphans (not attached to gateway) | 18-80 MB RSS each | 1-2 safe, 4+ is leak |
| Stopped Hermes sessions (state `Tl`) | ~114 MB RSS each | 100% safe to kill |
| Dashboard process | ~50 MB RSS | Safe to kill if not in use |
| Gateway itself | ~135 MB after clean restart | DO NOT kill |

**Cleanup sequence (kill dashboard BEFORE restarting gateway):**
```bash
# 1. Kill dashboard (if running) -- it doesn't die with gateway
kill <dashboard_pid>

# 2. Stop gateway
systemctl --user stop hermes-gateway.service

# 3. Kill orphans (codegraph not attached to gateway, Tl-processes)
kill <orphan_pid1> <orphan_pid2>

# 4. Start gateway
systemctl --user start hermes-gateway.service

# 5. Verify
free -h
# Expected: ~800-900 MB used, >1 GB available
```

**Caution:** Processes in state `D` (uninterruptible sleep) can't be killed -- wait for I/O to complete. Swap doesn't clear magically; avoid `swapoff -a && swapon -a` on 2 GB RAM.

---

## 3. Profile Personality (SOUL.md)

**Full detail:** `references/profile-personality.md`

Set up or update SOUL.md (persona/character) for a Hermes profile.

**Paths:**
- **Default profile:** `~/.hermes/SOUL.md`
- **Named profile:** `~/.hermes/profiles/<name>/SOUL.md`

**Quick-start:**
```bash
# If persona.md already exists (legacy migration):
cp ~/.hermes/persona.md ~/.hermes/SOUL.md
rm ~/.hermes/persona.md

# Verify
hermes profile show default | grep -i soul
# -> SOUL.md: exists
```

**Key rules:**
- If `persona.md` exists in the same directory, copy it -- do NOT write SOUL.md from scratch.
- SOUL.md is reloaded fresh every session; no restart needed.
- Default profile's SOUL.md is at `~/.hermes/SOUL.md`, NOT `~/.hermes/profiles/default/SOUL.md`.

---

## Stale Process Gateway Restart Loop

When the gateway enters a restart loop — `hermes gateway status` shows `auto-restart (Result: exit-code)`, restart counter climbs (87+), and journalctl consistently says `❌ Gateway already running (PID X)`:

### Diagnosis

```bash
# 1. Check active status
systemctl --user status hermes-gateway | grep Active
# → "activating (auto-restart) (Result: exit-code)" + restart counter

# 2. Find the real problem in journal
journalctl --user -u hermes-gateway --no-pager -n 10 | grep "Gateway already running"
# → ❌ Gateway already running (PID 289259)

# 3. Check what that PID is
ps -p <PID> -o pid,state,cmd --no-headers
# → State "Tl" (stopped, traced) — stale process, probably from tmux/nohup
# → State "Ssl" (sleeping) — might be legitimate, check age

# 4. Check if `hermes` CLI itself works
hermes --version
# → If command not found / broken symlink → need to fix symlink first
ls -la /home/hermes/.local/bin/hermes
# → Check destination exists
```

### Fix

```bash
# 1. Kill the stale gateway process
kill -9 <STALE_PID>

# 2. Reset systemd restart counter (otherwise it keeps the "84 restarts" counter)
systemctl --user reset-failed hermes-gateway.service

# 3. Start fresh
systemctl --user start hermes-gateway

# 4. Verify
sleep 3 && systemctl --user status hermes-gateway | grep Active
# → "active (running)"
```

### Broken `hermes` symlink (after cleanup mistakes)

If `hermes --version` fails and `ls -la ~/.local/bin/hermes` shows a symlink pointing to a non-existent path (e.g., `.../venv/bin/hermes` but `venv/` was deleted):

```bash
# Find the surviving venv
ls -d ~/.hermes/hermes-agent/.venv/bin/hermes ~/.hermes/hermes-agent/venv/bin/hermes 2>/dev/null

# Update symlink to the surviving one
ln -sf /home/hermes/.hermes/hermes-agent/.venv/bin/hermes /home/hermes/.local/bin/hermes

# Verify
hermes --version
```

### Root causes

| Cause | How to detect | How to prevent |
|-------|--------------|---------------|
| Stale process from tmux/nohup `gateway run --replace` | `ps -p <PID> -o state` shows `Tl` | Use `systemctl --user` for all gateway management, never manual `gateway run` |
| Cleanup deleted `venv/` breaking symlink | `ls -la ~/.local/bin/hermes` → broken symlink | Never delete `~/.hermes/hermes-agent/venv/` or `.venv/` without checking the symlink first |
| Two gateways started from different terminals | `ps aux | grep "gateway run"` shows multiple PIDs | Only `systemctl --user start|stop|restart`, never manual `hermes gateway run` |

### Pitfalls

1. **`kill -9` безопасен для gateway** — systemd с `Restart=always` поднимет новый процесс. SIGKILL не повреждает данные (сессии в SQLite, конфиг в YAML).
2. **Не путай restart counter с проблемой.** Counter 85+ — следствие, а не причина. Настоящая причина: «Gateway already running (PID X)» из-за stale процесса.
3. **После `reset-failed` старый лог остаётся.** `journalctl --user -u hermes-gateway` покажет историю включая все 87 рестартов. Это нормально.
4. **Проверяй `hermes` CLI первым.** Если `hermes` не работает — gateway не поднимется, даже если убить stale PID. Сначала симлинка, потом gateway.

---

## Cross-Cutting: Gateway Restart

All three domains may require a gateway restart as the final step:
- Provider change -> restart
- Memory cleanup -> restart
- Profile changes -> restart NOT needed (SOUL.md is hot-loaded)

```bash
systemctl --user restart hermes-gateway
sleep 5 && systemctl --user status hermes-gateway | grep Active
```

After restart, always verify free memory and check that dashboard did NOT start again.

---

## 9. Gateway Frozen / Provider Unresponsive — Diagnostic Protocol

**Full detail:** `references/gateway-frozen-diagnosis.md`

When the gateway appears hung — bot doesn't respond in Telegram, typing indicator frozen, messages queue up without reply, or `hermes gateway restart` itself hangs.

### Quick diagnostic (3 commands)

```bash
# 1. Is gateway process alive?
ps aux | grep "gateway run" | grep -v grep
systemctl --user status hermes-gateway | grep Active

# 2. Are provider calls failing?
journalctl --user -u hermes-gateway --since "10 minutes ago" --no-pager | grep -E "ReadTimeout|API call failed|Stream drop|Stream exhausted" | tail -10

# 3. Is provider API itself responsive?
curl -s --max-time 15 -X POST https://api.kilo.ai/api/gateway/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer *** \
  -d '{"model":"test","messages":[{"role":"user","content":"hi"}],"stream":true}' 2>&1 | head -3
```

### Key diagnostic patterns

| Симптом | Что значит |
|---------|-----------|
| Gateway process alive, journalctl full of `ReadTimeout` | Provider API (KiloCode) зависает на стриминге — не gateway проблема |
| ReadTimeout + `http_status=200` + fast ttfb (<1s) + small bytes (~375) | Provider начал отвечать, но завис mid-stream. Vercel upstream timeout. |
| Gateway process alive, **no** ReadTimeout в логах | Gateway ждёт запрос — проблема на стороне клиента/сети |
| Gateway process dead/not running | Systemd убил, смотри `journalctl` на `OOM` или `signal` |
| `hermes gateway restart` или `systemctl --user restart` висит | Команда пытается graceful shutdown, который ждёт ответа от провайдера — и зависает |

### Emergency restart (when graceful restart hangs)

```bash
# 1. Find gateway PID
ps aux | grep "gateway run" | grep -v grep | awk '{print $2}'

# 2. Kill -9 bypasses graceful shutdown — systemd auto-restarts
kill -9 <pid>

# 3. Wait for systemd to pick it up
sleep 3 && systemctl --user is-active hermes-gateway
```

**Why this works:** `hermes gateway restart` and `systemctl --user restart` send SIGTERM (graceful). The gateway tries to drain active agents (180s timeout) and may try to finalize API calls — both can hang if the provider is unresponsive. `kill -9` (SIGKILL) bypasses all cleanup and systemd's `Restart=always` policy respawns the process immediately.

### After restart

Check that new ReadTimeout errors stopped appearing:
```bash
journalctl --user -u hermes-gateway --since "1 minute ago" --no-pager | grep -c "ReadTimeout"
# → 0 = clean restart
```

If ReadTimeout continues immediately — the provider is genuinely down, not a gateway state issue. Consider switching provider.

### Cross-reference

- Timeout tuning (HERMES_STREAM_READ_TIMEOUT, api_max_retries): `references/kilocode-timeout-tuning.md`
- Memory pressure causing gateway slowdowns: Section 2 above (Memory Pressure & Cleanup)
- Stuck Kanban workers (persistent typing indicator): Section 6 above

---

## 6. Disk Expansion after Provider Upgrade

When a VPS provider (VDSka, etc.) increases your disk quota, the block device grows but the **partition and filesystem stay at the old size**. You must expand them manually.

**Detection (always check before assuming the upgrade took effect):**
```bash
lsblk                              # actual block device size (new)
df -h /                            # partition/filesystem size (old/stuck)
# If lsblk shows e.g. 50G but df shows 20G → partition not expanded
```

**Prerequisites check:**
```bash
df -T /                            # confirm ext4 (supports online resize)
which growpart && which resize2fs  # confirm tools exist
sudo dumpe2fs -h /dev/sda2 | grep "Filesystem state"
# → must say "clean"
```

**Expansion (online, no downtime — ext4 supports live resize):**
```bash
sudo growpart /dev/sda 2           # expand partition to fill the disk
sudo resize2fs /dev/sda2           # expand filesystem into the new space
```

**Verify:**
```bash
df -h /                            # confirm new size
lsblk                              # partition now matches block device
```

**Pitfalls:**
1. **The user will be skeptical** — «уверен?» — always double-check FS type, tool availability, and partition layout BEFORE running the commands. Show the evidence.
2. **Partition number matters.** If the OS partition is `/dev/sda2`, pass `2` to growpart (`sudo growpart /dev/sda 2`). Never guess — check `lsblk` or `sudo fdisk -l`.
3. **Only ext4 supports online resize.** If the FS is xfs/btrfs/zfs, the procedure differs — confirm before executing.
4. **growpart vs parted resizepart.** `growpart` is the preferred tool on Ubuntu/Debian. If missing, install `cloud-guest-utils` or `cloud-utils`.
5. **Provider FAQ says «диск — только в большую сторону»** — you can't shrink, only grow. No rollback.

---

## 10. Hermes Update Protocol (Git Install)

When the user says "обнови Hermes" or "пора обновить hermes" — особенно с пометкой "аккуратно" или "be careful" — применяй этот протокол.

**Ключевой принцип:** сначала покажи changelog, потом спрашивай разрешения. Не запускай update молча.

### Шаг 1 — Проверить текущее состояние

```bash
cd ~/.hermes/hermes-agent

# Текущая версия
git describe --tags --always

# Быстрый взгляд на отставание + локальные правки в одном месте:
hermes --version
# → Hermes Agent vX.Y.Z · upstream <hash> · local <hash> (+N carried commits)
#   N>0 — есть незакоммиченные локальные правки; их надо засташить.

# Локальные изменения (⚠️ будут проблемы при pull)
git status --short

# Последние коммиты
git log --oneline -5
```

**⚠️ Покажи пользователю, какие файлы изменены локально.** Не просто «есть изменения» — выведи `git status --short` и, если пользователь спросит, покажи `git diff` по конкретным файлам. Три файла, которые чаще всего патчат: `gateway/run.py`, `hermes_cli/kanban_db.py`, `tools/terminal_tool.py`. Пользователь должен знать, что будет засташено.

### Шаг 2 — Fetch и оценка отставания

```bash
git fetch --tags origin

# Сколько коммитов позади
git rev-list --count HEAD..origin/main

# Последний тег в upstream
git tag --sort=-creatordate | head -5

# Последний тег на origin/main
git tag --merged origin/main --sort=-creatordate | head -3
```

### Шаг 3 — Показать changelog (группированный)

Не вываливай 1000 коммитов. Сгруппируй:

```bash
# feat — новое
git log --oneline HEAD..origin/main --no-merges --format="%s" | grep -iE "^feat|^add|^new" | head -15

# fix — важные исправления для твоей конфигурации
git log --oneline HEAD..origin/main --no-merges --format="- %s" | grep -iE "^\- (fix|change)" | grep -vE "test|docs|chore|nix|deps" | head -20

# breaking / deprecation / migration
git log --oneline HEAD..origin/main --no-merges --format="%s" | grep -iE "breaking|deprecat|migrat|config.*change" | head -10

# Специфические изменения для update-механизма
git log --oneline HEAD..origin/main --no-merges --format="- %s" | grep -iE "update" | head -10
```

### Шаг 4 — Принять решение

После показа changelog спроси пользователя: "Запускать обновление?" с опциями:
- «Да» → выполнить шаг 5
- «Покажи детальнее» → развернуть конкретную категорию
- «Нет, позже» → отложить

### Шаг 5 — Выполнить обновление

После подтверждения пользователя выполни последовательно:

```bash
# 1. Бэкап конфига с таймстемпом (чтобы не затереть предыдущий бэкап)
TS=$(date +%Y%m%d_%H%M%S)
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.backup-$TS
cp ~/.hermes/.env ~/.hermes/.env.backup-$TS
# Если .env не скопировался (overwritten timestamp-коллизия) — сделай отдельно
ls -la ~/.hermes/*.backup-*  # проверить оба файла

# 2. Stash локальных изменений (если есть)
cd ~/.hermes/hermes-agent
git stash push -m "local-changes-before-update-$(date +%Y%m%d)"  # stash все
# или конкретные: git stash push -m "..." <file1> <file2>

# 3. Pull (только fast-forward — безопасно)
git pull --ff-only origin main

# 4. Обновить зависимости
source venv/bin/activate
if grep -q "^uv " venv/pyvenv.cfg 2>/dev/null; then
    uv pip install -e .
else
    pip install -e .
fi

# 5. Миграция конфига
hermes config migrate

# 6. Очистка устаревших .env переменных
# После обновления могут появиться предупреждения о deprecated env vars:
#   ⚠ TERMINAL_CWD=/path found in .env — deprecated.
# Решение: перенести в config.yaml и удалить из .env:
grep -n 'TERMINAL_CWD' ~/.hermes/.env && sed -i '/TERMINAL_CWD/d' ~/.hermes/.env; hermes config set terminal.cwd /home/hermes/.hermes/hermes-agent

# 7. Проверить
hermes doctor
```

**Если git stash было:** после успешного обновления **НЕ применяй stash вслепую**. Сначала проверь, не вмерджили ли твой патч в апстрим:

```bash
# Ищешь функцию/строку из твоего патча в новом коде
grep -n "resolve_task_overrides" tools/terminal_tool.py   # пример из v0.20.6
# → если функция уже есть в upstream — патч не нужен, удаляй stash целиком:
git stash drop stash@{0}
```

Частный случай: `tools/terminal_tool.py` был пропатчен локально (добавлен `resolve_task_overrides`), но к v0.20.6 эта функция уже оказалась в апстриме — повторно применять патч не нужно. Если патч НЕ в апстриме — `git stash pop`, но могут быть конфликты с новым кодом. Безобидные правки (например, `.gitignore` с игнорами `.gitmark/`) можно вернуть точечно: `git checkout stash@{0} -- .gitignore`, затем `git stash drop`.

**Если возникли конфликты** — см. `references/post-update-conflict-resolution.md`. Ключевые правила:
- `git checkout --ours` = взять upstream (почти всегда правильно для core файлов)
- `git checkout --theirs` = взять локальный патч (если фичи нет в upstream)
- stash конфликты обычно требуют ручного merge обоих изменений

### Шаг 6 — Пост-апдейт: мониторинг и ожидаемые варнинги

После успешного обновления:

1. **Покажи пользователю сводку** — что обновили, с какой версии на какую, сколько коммитов, какие шаги прошли.

2. **`hermes doctor` — ожидаемые предупреждения (не паниковать):**
   - `Config version outdated (vN → vM)` — лечится `hermes config migrate`, который уже сделали в шаге 5
   - `⚠ Nous Portal auth (not logged in)` / `⚠ OpenAI Codex auth` — нормально, если не используешь эти провайдеры
   - `⚠ ripgrep (rg) not found` — опционально, не влияет на работу
   - `⚠ docker not found` — опционально
   - `⚠ Playwright Chromium not installed` — нормально, browser_* тулы не используются в Telegram
   - API connectivity checks могут таймаутить через 30с — не критично, это проверка 26 эндпоинтов параллельно
   - **На что обратить внимание:** `✗` или `error` по критическим компонентам (Python, venv, config, state.db)
   - `⚠ Installed gateway service definition is outdated` — после апдейта systemd-unit записан старой версией. Некритично: обновится сам при следующем `hermes gateway restart` (или сразу перезапусти — см. Шаг 7). Работающему gateway это не мешает.

3. **Предложи настроить еженедельную проверку** — если обновление давно не делали (1000+ коммитов), пользователю может захотеться не пропускать следующие. Используй готовый скрипт `hermes-update-check.sh`:

   **Что делает:** тихо выходит если всё актуально, присылает changelog если есть отставание. Не тратит токены — no_agent.

   **Установка:**
   ```
   cronjob action=create name="Hermes update check (weekly)" no_agent=true script=hermes-update-check.sh schedule="0 10 * * 1"
   ```

   **Проверка:** `cronjob action=run job_id=<id>` — скрипт выполнится, но no_agent не доставляет на `run`. Только по расписанию. Проверить статус: `cronjob action=list`.

   **Содержимое скрипта:** `~/.hermes/scripts/hermes-update-check.sh` — два fetch + git merge-base --is-ancestor + diff. Если нужно изменить порог (сейчас — любой отрыв), отредактируй скрипт.

### Шаг 6b — Большой апдейт: тулсеты переименованы (`messaging` → платформенные)

После крупного обновления (проверено v0.18.2 → v0.20.6) `hermes config migrate` выдаёт предупреждения:

```
⚠ platform 'cli' references unknown toolset 'messaging' — did you mean 'hermes-cli'?
⚠ platform 'telegram' references unknown toolset 'messaging' — did you mean 'hermes-telegram'?
```

Причина: тулсет `messaging` разбит на платформенные — `hermes-cli`, `hermes-telegram`, `hermes-discord`, `hermes-whatsapp` и т.д. (полный список — в `toolsets.py`, секция `TOOLSETS`). Старый конфиг ссылается на несуществующее имя, и `resolve_toolset()` молча отключает эти инструменты.

**Фикс — заменить `messaging` на правильный платформенный тулсет через `hermes config set`** (списки можно задавать как JSON-массив):

```bash
hermes config set platform_toolsets.cli '["browser","clarify","code_execution","cronjob","delegation","file","image_gen","memory","hermes-cli","session_search","skills","terminal","todo","tts","vision","web"]'
hermes config set platform_toolsets.telegram '["browser","clarify","code_execution","cronjob","delegation","file","image_gen","memory","hermes-telegram","session_search","skills","terminal","todo","tts","vision","web"]'
```

⚠️ `hermes config set platform_toolsets.*` печатает «not a recognized config key — saved anyway» — это **ложное предупреждение**: ключ валидный (его пишет setup-визард, `config.py` строка ~2095), значение сохраняется. Не паникуй, не ищи «правильный» ключ. Для тишины можно добавить `--force`.

**Проверка, что тулсеты разрешаются чисто:**

```bash
cd ~/.hermes/hermes-agent && python3 -c "
import sys; sys.path.insert(0, '.')
from hermes_cli.toolset_validation import validate_platform_toolsets
from hermes_cli.config import read_raw_config
import toolsets
raw = read_raw_config()
warns = validate_platform_toolsets(raw.get('platform_toolsets'), lambda n: n in toolsets.TOOLSETS)
print('WARNINGS:', warns if warns else 'none')
"
```

**Миграция конфига НЕ только добавляет опции — она может менять значения.** На v33→v39 (v0.20.6) миграция сама:
- Сбросила `personality` в `none` (был `kawaii`) — вернуть: `/personality kawaii`
- Подняла `delegation.max_iterations` 50 → 250
- Подняла `delegation.max_concurrent_children` 3 → 10

После миграции покажи пользователю эти изменения — это поведенческие изменения, а не косметика.

### Шаг 7 — Restart gateway (если нужно)

На VPS после обновления обязательно перезапусти gateway:
```bash
systemctl --user restart hermes-gateway
sleep 3 && systemctl --user status hermes-gateway | grep Active
```

Для CLI-сессии достаточно выйти и зайти заново — обновлённый код подхватится.

### Pitfalls

1. **Локальные изменения — главная причина проблем.** Три файла, которые чаще всего бывают изменены: `gateway/run.py`, `hermes_cli/kanban_db.py`, `tools/terminal_tool.py`. Перед pull всегда проверять `git status --short`.
2. **`hermes update` из CLI — рабочий вариант для git-установки, НО только на чистом дереве.** Проверено v0.18.2→v0.20.6 (11 102 коммита): `hermes update` сам делает pull, ставит зависимости, сидит .env для профилей, гоняет `config check` и перезапускает gateway. Локальные изменения он НЕ трогает/может конфликтовать — поэтому сначала `git stash` (шаг 2 выше), потом `hermes update`. Ручной `git pull` остаётся запасным вариантом (напр., при 429 rate limit).
3. **После обновления gateway нужно перезапустить** — `systemctl --user restart hermes-gateway` (на VPS) или перезапустить CLI.
4. **Dashboard может сброситься** — после обновления проверь `hermes dashboard --status` и перезапусти если нужно.
5. **Cron-задачи закрепляют модель при создании** — после обновления провайдера проверь `hermes cron list` на предмет устаревших моделей.
6. **Changelog в 1000+ коммитов — ок.** Покажи топ-10-15 по категориям, не все. Если пользователь хочет детальнее — развернёшь по запросу.

### GitHub rate limit 429 при update — retry с паузой

**Симптом:** `hermes update` (или `git fetch`) падает с:
```
✗ Failed to fetch updates from origin.
  error: RPC failed; HTTP 429 curl 22 The requested URL returned error: 429
```
Это **временный лимит GitHub** (частые запросы с одного IP), не проблема сети/конфига. Лечение:
1. Подождать 90 сек – 5 мин (не ретраить сразу — 429 держится).
2. Сначала отдельно `git fetch origin main` — проверить, что обновился FETCH_HEAD.
3. Потом снова `hermes update`.
429 слетает сам; ничего чинить не нужно.

### Approval block на `hermes update` — остановиться, не обходить

`hermes update` перезапускает gateway и убивает запущенные агенты, поэтому идёт через approval gate. Если пользователь **не ответил** на запрос подтверждения — система вернёт:
```
BLOCKED: Command timed out without user response. ... Do NOT retry this command,
do NOT rephrase it, and do NOT attempt the same outcome via a different command.
```
Правило: не ретраить, не перефразировать, **не обходить** (например, ручным `git pull` — это та же операция). Остановиться и отчитаться: fetch готов, полное обновление ждёт «добро» от пользователя.

---

## 8. Cron Job no_agent Pattern (Static Text Reminders)

When the user wants a simple fixed-text reminder without LLM tokens — e.g. «Неделя прошла. Может, пора что-то улучшить?» — use `no_agent=true` with a bash script.

### Creating a no_agent reminder

```bash
# 1. Create script
cat > ~/.hermes/scripts/<name>.sh << 'EOF'
#!/usr/bin/env bash
echo "Your reminder text here"
EOF
chmod +x ~/.hermes/scripts/<name>.sh

# 2. Create job with cronjob tool
# action=create, no_agent=true, script=<name>.sh, deliver=origin, schedule=...
```

### ⚠️ Critical: `cronjob action=run` does NOT deliver for no_agent

This is the #1 trap. When you call `cronjob(action='run', ...)` on a `no_agent=true` job:
- The script runs and exits with status `ok`
- **Nothing is delivered to the user** — no Telegram message, no output
- Only **scheduled execution** (the actual cron tick) triggers delivery

**How to test a no_agent job:**
- Don't rely on `run` — it won't show you the delivery
- Either wait for the scheduled time, or use `send_message` independently to verify the channel works
- Check `cronjob(action='list')` to see `last_status: ok` after a `run` — the script ran, but delivery was suppressed

### Deliver target: use `origin`

For Telegram-sourced cronjobs (created from a Telegram DM), set `deliver: origin` — not `telegram:chat_id`. Other working no_agent jobs (lunch-reminder, sync profile skills, gotham-nightly) all use `deliver: origin`.

`deliver: telegram` or `telegram:350262645` doesn't hurt for LLM-driven jobs, but for no_agent the `origin` value is what's proven to work.

### When to choose no_agent vs LLM-driven

| | no_agent | LLM-driven |
|---|---|---|
| **Use case** | Fixed text, zero reasoning | Dynamic content, conditional logic |
| **Tokens** | 0 | ~500-2000 per run |
| **Setup** | Script file + cronjob | Prompt only |
| **Testability** | `run` doesn't deliver — only schedule tests | `run` delivers normally |
| **Reliability** | Only stdout → message | LLM can hallucinate/stray from prompt |

**Default choice:** If the message text is static and doesn't need personalization, use no_agent. If it needs to reference current data (Kanban stats, unfinished tasks, time-sensitive context), use LLM-driven.

---

## 5. Cron Job Timing Debugging

When a user reports "this cron job ran at the wrong time" / "it shouldn't have run now" — the root cause is almost never a scheduler bug. It's a mismatch between perceived and actual schedule, or user seeing a delayed delivery.

### Diagnostic Protocol

**Step 1 — Check the schedule and last run:**
```bash
hermes cron list | grep -A 10 "<job-name-or-id>"
# Key fields: schedule, last_run_at, next_run_at, last_status
```

**Step 2 — Establish current time in user's timezone:**
```bash
TZ=Europe/Moscow date   # For Василий — always MSK (UTC+3)
```

**Step 3 — Cross-reference:**
- Does the user's «current time» match one of the schedule's time slots?
- Does `last_run_at` match that slot? (If yes, job ran correctly)
- Does the delivery error field show anything?

**Step 4 — Check scheduler logs for actual run time:**
```bash
grep "cron.scheduler\|job.*<id>" ~/.hermes/logs/agent.log | tail -20
```
Look for:
```
cron.scheduler: Running job '<name>' (ID: <id>)
```
This is the actual UTC run time. Convert to user's TZ and compare against the schedule.

**Step 5 — Check delivery in gateway log:**
```bash
grep "delivered to telegram\|delivery error\|Flushing.*batch" ~/.hermes/logs/gateway.log | grep "<date>" | tail -10
```

### Common Findings

| Symptom | Most likely cause |
|---------|------------------|
| User sees message NOW, logs say it ran hours ago | Delayed Telegram delivery (network issue / gateway restart) |
| `last_run_at` matches schedule, user says «ran at wrong time» | User confused about schedule — show them the cron expression |
| `last_run_at` matches schedule but timezone differs | Job was created with UTC assumption vs MSK reality |
| Message arrived but `last_run_at` is from earlier slot | User just opened Telegram after being offline — message was pending |
| Job ran 2+ times in one slot | Duplicate cron entries in `cronjobs.yml` — check for multiple identical lines |
| User wants `:00` AND `:30` slots on same job | **Can't do in one cron expression** — minute is a single field. Split into two jobs: one for `:00` hours, one for `:30` hours. |

### Pitfalls

1. **Agent.log runs on UTC** — `2026-05-30 03:00:54` UTC = `06:00:54` MSK. Always add +3 when reading scheduler timestamps.
2. **The cronjob list shows `last_run_at` WITH timezone offset** (e.g., `+03:00`), but agent.log is always UTC. Cross-referencing requires mental conversion.
3. **Gateway may not log the Telegram send at the exact scheduler delivery time** — the cron scheduler hands the message to the adapter synchronously. If gateway.log shows no Telegram flush around that time, the send still happened; `delivered to telegram:chat_id via live adapter` in agent.log is the authoritative record.
4. **Schedule strings with comma-separated hours** (e.g., `0 6,11,15,17 * * *`) mean MINUTES=0 at EACH of those hours — not a range. Verify against `next_run_at` to confirm parsing.

### Cron jobs failing with "Request timed out" / "provider timeout" (LLM jobs only)

**Signature:** ALL LLM-driven cron jobs fail with `RuntimeError: Request timed out.` /
`provider timeout. Fallback chain was exhausted or unavailable` (delivered as
"Cronjob Response: ... failed"), while `no_agent` script jobs (disk-check,
lunch-reminder, gotham-nightly) keep running `ok`. That asymmetry — LLM jobs
down, script jobs up — points at the provider timeout, NOT the scheduler.

**Diagnostic protocol:**

```bash
# 1. Which jobs failed? cronjob action=list → look at last_status + whether
#    the job is LLM-driven (has prompt, no script) vs no_agent (script set).
#    Old failures accumulate: morning-briefing, evening-reminder, study-reminder,
#    proxy reminders — all LLM-driven, all fail together.

# 2. Read the actual error from a failed run's output file:
ls -la ~/.hermes/cron/output/<job_id>/ | tail
#    Each run writes <timestamp>.md. FAILED files end with "## Error\n\nRuntimeError: Request timed out."

# 3. Confirm in logs — 3 retries × timeout, all same error:
grep -E "APITimeoutError|Request timed out" ~/.hermes/logs/errors.log | tail -20
#    → "API call failed after 3 retries. Request timed out. | provider=kilocode model=deepseek/deepseek-v4-flash:discounted"

# 4. Check the timeout config:
grep -A5 "^providers:" ~/.hermes/config.yaml
#    → providers.kilocode.request_timeout_seconds: 10  ← TOO LOW
```

**Root cause:** `providers.kilocode.request_timeout_seconds: 10` — the per-call
HTTP timeout for the KiloCode gateway. 10s is too tight for deepseek-v4-flash
during peak hours (cron slots: 07:00, 09:00, 12:00, 15:00, 21:00 MSK), so every
LLM cron run times out after 3 retries. Interactive chat often still works
because user-initiated requests hit off-peak or shorter prompts — the cron
failures are the canary.

**Fix (verified Aug 2026):**
```bash
hermes config set providers.kilocode.request_timeout_seconds 120
```

**Verify:** `cronjob action=run job_id=<id>` → `execution_success: true`,
`last_status: ok`, and the new output file contains `## Response` (no `## Error`).
No gateway restart needed — cron jobs read config fresh on each run.

**Pitfall:** the fix is `providers.kilocode.request_timeout_seconds` (provider
level) — see `references/kilocode-timeout-tuning.md` for the resolution chain
and the correction note (older text claimed the root-level key; that's wrong).

---

## 6. Stuck Kanban Workers (Typing Indicator Culprit)

When a user reports that the Telegram bot shows persistent typing indicator («печатает»), a **Kanban worker that completed its task but didn't exit** is the most likely cause.

**Diagnostic:**
```bash
# Find hanging workers — completed tasks with live processes
ps aux | grep 'hermes.*kanban task' | grep -v grep
```

**What to look for:**
- A process running `hermes ... -p worker ... chat -q work kanban task t_XXXXXXXX`
- Task shows `status: done` in `hermes kanban show t_XXXXXXXX` but the worker process is still alive
- Process may have been running for hours (check `ps -p <pid> -o etime`)

**Why it happens:**
The Kanban dispatcher spawns a worker subprocess. When the task completes (worker calls `kanban_complete`), the worker should exit. Rarely, the worker's agent loop finishes the task but the CLI process doesn't terminate — it stays in state `Ssl` indefinitely. Gateway sees an alive child and keeps the typing indicator alive.

**Fix:**
```bash
# Try SIGTERM first
kill <worker_pid>
sleep 1

# If still alive (most cases — stuck workers don't respond to TERM)
kill -9 <worker_pid>
```

After kill, verify:
```bash
ps -p <worker_pid> -o pid,state,cmd --no-headers || echo "✅ Worker killed"
```

The process may briefly show as zombie (`Zs`) — gateway collects it via wait() within seconds.

**Prevention:**
- Archive completed tasks periodically to clear workspaces and reduce dispatcher load
- Monitor for old worker processes during routine maintenance (weekly)

**Alternative cause — gateway cycling due to healthcheck cron job** (if no stuck workers found):

When the user reports «бот постоянно печатает» and no stuck Kanban workers exist, the gateway itself may be restarting every ~5 minutes.

**Diagnostic:**
```bash
journalctl --user -u hermes-gateway --since "2 hours ago" --no-pager | grep -E "shutting down|Started|Stopped|Failed|restart"
```

Look for: `SIGTERM` from systemd (`parent_name=systemd`) → clean exit → systemd restarts.

**Root cause:** A `no_agent` cron job (`gateway-healthcheck`, typically running `*/5 * * * *`) that runs a shell script checking the age of `gateway.log`. If the log hasn't been updated in N seconds (typically 120), the script decides the gateway is hung and runs `systemctl --user restart`. But the gateway doesn't write logs when idle — so this creates an infinite restart cycle.

**Fix:** Pause or remove the healthcheck cron job:
```bash
hermes cron pause 63ea7db24442   # typical ID of gateway-healthcheck
```

Or rewrite the script to use a real health endpoint instead of log file age.

## 7. Curator — Auto Skill Creation

The неcurator is an auxiliary-model background process that analyzes sessions and auto-creates skills. When the user says «не надо было сохранять», it's likely the curator.

### What it does

Periodically (default: every 7 days) the curator runs an LLM pass over recent sessions, looking for patterns it can consolidate into reusable skills. It can:
- Create new skills from session activity
- Consolidate overlapping skills
- Archive stale/unused skills
- Update memory with extracted facts

### The problem: unwanted skill creation

The curator analyses session content and decides what to save. If you did vault cleanup in a session, the curator might create an `obsidian-vault-maintenance` skill unprompted — even after you deleted it. It then recreates it on the next pass.

### Management

**Check status:**
```bash
hermes curator status
```

**Pause (reversible, survives gateway restart but NOT necessarily Hermes update):**
```bash
hermes curator pause
hermes curator resume   # to re-enable
```

**Disable in config (survives Hermes update — the right choice when user doesn't want it):**
```bash
hermes config set curator.enabled false
```

This writes to `~/.hermes/config.yaml` which is never overwritten by `hermes update`.

**Triggers to recognize:**
- If you see `💾 Self-improvement review: Skill '...' created. · Memory updated` in the conversation — that's the curator acting
- The user may not want this; offer to pause or disable it

### Pitfalls

1. **Curator is NOT a skill** — it's a built-in Hermes feature (auxiliary model), not a user-installed skill. You can't delete it via `skill_manage`.
2. **Pause vs disable** — `pause` is runtime-only, may reset on Hermes update. `hermes config set curator.enabled false` is permanent.
3. **Don't confuse with self-improver/skill-improver profiles** — those are Kanban profiles for manual invocation. The curator runs automatically in the background.
4. **Deleted skills come back if curator ran before deletion.** The curator tracks skills in an internal index (`~/.hermes/skills/.usage.json`). If the curator already indexed the skill, deleting the SKILL.md file doesn't remove the index entry — the curator may recreate it on its next LLM pass, even after `skill_manage(action='delete')`. To stop this: either `hermes config set curator.enabled false` (permanent) or `hermes curator pause` (until restart/update).

---

## 8. Profile Skill Duplication (Disk Waste)

**Full detail:** `references/profile-skill-duplication.md`

Each Hermes named profile maintains its own `skills/` directory with full dependency copies. The `search` skill (crawl4ai + web-search-scraper) is especially heavy — ~1.4 GB + ~826 MB per profile due to bundled Chromium/Playwright.

**Systematic check (all profiles in one go):**
```bash
for p in ~/.hermes/profiles/*/; do
  name=$(basename "$p")
  size=$(du -sh "$p/skills" 2>/dev/null | cut -f1)
  echo "$name: $size"
done
```

**Find any remaining heavy .venv across ALL profiles:**
```bash
find ~/.hermes/profiles -maxdepth 6 -name ".venv" -type d -exec du -sh {} \; 2>/dev/null | sort -rh
```

**Typical waste found (May 2026):**
| Profile | Search skill size | Notes |
|---------|-------------------|-------|
| coach | ~2.3 GB | Had full COPY with venv — fixed |
| researcher | ~741 MB | Legitimately uses crawling |
| main profile | ~745 MB | Legitimately uses crawling |

**Symlinks ARE supported** — most profiles already use them for selective skills. The issue is when a profile has a full **copy** of a heavy skill instead of a symlink.

**Check copy vs symlink for ALL profiles:**
```bash
for p in ~/.hermes/profiles/*/; do
  name=$(basename "$p")
  copies=""; links=""
  for item in "$p"skills/*; do
    [ -e "$item" ] || continue
    if [ -L "$item" ]; then links="$links $(basename "$item")"
    else copies="$copies $(basename "$item")"; fi
  done
  echo "$name: 🔗$links  📀$copies"
done
```

**Fix: replace copy with symlink to main profile:**
```bash
# 1. Remove the copy (CAUTION: rm -rf blocks on approval gate)
rm -rf ~/.hermes/profiles/<profile>/skills/<category>/<skill-name>

# 2. Create symlink to main profile's skill
ln -s ~/.hermes/skills/<category>/<skill-name> ~/.hermes/profiles/<profile>/skills/<category>/<skill-name>
```

**Which profiles already use symlinks (as of May 2026):**
| Profile | Symlinked skills |
|---------|-----------------|
| architect | architecture-diagram, writing-plans |
| coder | git-init-before-edits, requesting-code-review, subagent-driven-development, test-driven-development, writing-plans |
| debugger | git-init-before-edits, kanban-worker, requesting-code-review, systematic-debugging, writing-plans |
| explorer | crawl4ai, web-search-scraper |
| coach | growth-coach, kanban-orchestrator |
| researcher | crawl4ai, kanban-worker, web-search-scraper |
| + others | Selected skills per role |

**Cleanup notes:**
- Before cleaning, verify what the profile actually uses: check its SOUL.md and daily workflow.
- **⚠️ rm -rf triggers approval gate** — user must explicitly confirm destructive actions.
- **Recovery:** `cd <skill>/scripts && uv sync` rebuilds the venv if ever needed.

---

## 11. Remote Desktop Connection

Hermes Desktop (Electron app, `apps/desktop/`) может подключаться к gateway на VPS через WebSocket. Это даёт полноценный десктопный UI на ПК пользователя при том, что агент бегает на сервере.

### Архитектура

```
ПК пользователя (Windows/Mac)           VPS (Linux)
┌─────────────────────┐              ┌──────────────────────────┐
│ Hermes Desktop       │──wss://──→  │ Hermes Gateway           │
│ (Electron)           │             │ (dashboard: 9119)        │
│                      │             │    ↓                     │
│ локальный UI,        │             │ DeepSeek/KiloCode API    │
│ файлы, DevTools      │             │ Telegram Gateway         │
└─────────────────────┘             └──────────────────────────┘
```

### Как работает подключение

Desktop соединяется с gateway через **два канала**:
- **REST API** (HTTP/HTTPS) — управление, статус, аутентификация
- **WebSocket** (WS/WSS → `/api/ws` с токеном или OAuth ticket) — реальный диалог с агентом

Два режима аутентификации (определяются полем `auth_required` в `/api/status`):
| Режим | Как работает | Когда используется |
|-------|-------------|-------------------|
| `token` (default) | Статичный session token. REST: заголовок `X-Hermes-Session-Token`. WS: `?token=`. | Локальные установки, сам хост |
| `oauth` | HttpOnly session cookies. WS: одноразовый `?ticket=` с `/api/auth/ws-ticket`. | Nous Portal, публичные gateway |

### Что нужно настроить на VPS

**1. Запустить dashboard (HTTP-сервер gateway)**

```bash
# Без HTTPS — только для теста по IP в локальной сети
hermes dashboard --host 0.0.0.0 --insecure

# Через systemd (чтобы не умирал после выхода)
systemctl --user start hermes-gateway
# dashboard стартует автоматом вместе с gateway
```

⚠️ `--insecure` открывает API ключи в локальную сеть. Используй только если VPS и ПК в одной сети.

**2. Настроить reverse proxy с HTTPS (правильный способ)**

```nginx
# /etc/nginx/sites-available/hermes
server {
    listen 443 ssl;
    server_name hermes.твой-домен.ru;

    ssl_certificate /etc/letsencrypt/live/hermes.твой-домен.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hermes.твой-домен.ru/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:9119;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

Ключевое: `proxy_set_header Upgrade` и `Connection "upgrade"` — без них WebSocket не работает.

**3. Сгенерировать токен для Desktop**

Desktop использует dashboard session token. После запуска dashboard:
```bash
# Токен генерируется при первом запуске dashboard
# Он лежит в ~/.hermes/ (например, в dashboard token файле)
# Либо используется pairing-код:
hermes pairing list          # посмотреть активные коды
hermes pairing approve <code> # одобрить запрос с Desktop
```

### Как Desktop находит сервер

Connection config (`connection-config.cjs`) поддерживает **per-profile remote override**:

```json
{
  "profiles": {
    "default": {
      "mode": "remote",
      "url": "https://hermes.твой-домен.ru",
      "authMode": "token",
      "token": "..."
    }
  }
}
```

Без профильной конфигурации Desktop пытается:
1. Переменную окружения `HERMES_REMOTE_GATEWAY_URL`
2. Глобальную настройку в connection config
3. Запуск локального backend

### Когда это полезно

| Сценарий | Зачем |
|----------|-------|
| Агент на VPS, ты за ноутбуком | Весь контекст, память, скрипты на сервере. На компе — UI и файлы |
| Нужен браузер | Desktop может открывать локальный Chromium для `browser_*` тулов |
| Telegram глючит | Desktop как альтернативный интерфейс |
| Хочешь смотреть что агент делает в реальном времени | WebSocket стримит ответы как они приходят |

### Pitfalls

1. **Без HTTPS WebSocket не работает** в современных браузерах/Electron. `wss://` требует SSL-сертификата. Для теста по IP можно запустить с `--insecure` на VPS и подключаться по `http://IP:9119`, но токен идёт в открытую.
2. **Nginx proxy_read_timeout** — по умолчанию 60 секунд. Hermes диалоги могут быть долгими (агент думает, тулы выполняются). Ставь `proxy_read_timeout 86400` (24 часа), иначе nginx оборвёт соединение.
3. **Dashboard и gateway — один процесс.** `hermes dashboard` — это HTTP-прокси к тому же самому gateway. Не нужно запускать gateway отдельно. `hermes gateway run` уже включает HTTP API на порту 9119.
4. **Токен может протухнуть.** OAuth-режим требует перелогина раз в ~24ч. Token-режим статичен.
5. **Не путай с desktop-сборкой.** `hermes desktop` (собирает Electron) нужно запускать на ПК пользователя, не на VPS. На VPS достаточно `hermes dashboard` (или gateway, который уже включает dashboard).

## 12. Cloudflared Tunnel Management

**Full detail:** `references/cloudflared-tunnel.md`

Quick (account-less) Cloudflare tunnels for exposing local ports via HTTPS. Covers setup, monitoring for DNS timeout failures (~every 6h on some VPS providers), and URL extraction with `tee`.

---

## Pitfalls

1. **Patch on config.yaml creates duplicates AND hits protected-file guard.** The `patch` tool inserts a new section but doesn't remove the old one, AND `config.yaml` is registered as a protected system file — patch is flatly refused with a retryable error. If you retry with the same arguments, `tool_loop_guardrails` fires warnings. **Always use `hermes config set`** instead of any file-level tool (patch/terminal/write_file) for config.yaml changes. The CLI command is the only path that works without token-wasting retry loops.
2. **Named profiles don't inherit .env.** Every profile needs its own copy of `~/.hermes/.env`. Without it, cron jobs under that profile get 401 errors.
3. **Dashboard doesn't die with gateway.** It's a separate `hermes dashboard --host 0.0.0.0 --insecure` process. Kill it explicitly before restarting gateway, or it continues eating RAM.
4. **Cron jobs pin their model at creation.** Changing the default provider does NOT update existing cron jobs. Update them explicitly.
5. **codegraph orphans accumulate.** Each Hermes CLI session spawns its own codegraph MCP process. On normal exit the `finally` block cleans it up, but SIGKILL/crash leaves orphans. Clean periodically.
6. **Disk expansion not automatic.** When VDSka (or similar) increases disk, the block device grows but partition/FS don't. Always use `lsblk` vs `df -h` to verify before calling it done.
7. **Profile skill duplication wastes GBs.** Each Hermes profile duplicates `skills/search` (~2.3 GB for coach) due to bundled browser runtimes. Check `du -sh ~/.hermes/profiles/*/skills/*/` when disk is tight.
8. **`hermes update` (git pull) can overwrite local patches.** Before running `hermes update`, check for local modifications: `cd ~/.hermes/hermes-agent && git status --short`. If files like `gateway/run.py` or `kanban_db.py` are modified, `git pull` will either overwrite them or cause a merge conflict. Safer workflow: `cd ~/.hermes/hermes-agent && git stash` → `hermes update` → re-apply patches from stash. Always check `git diff HEAD` before updating.

9. **Code changes to `gateway/run.py` require a gateway restart to take effect.** The gateway runs as a persistent process — editing `~/.hermes/hermes-agent/gateway/run.py` only changes the file on disk. The running gateway still uses the old code in memory. After any manual patch: `systemctl --user restart hermes-gateway`. Without restart, the new logic (e.g., artifact fallback) doesn't execute; test tasks complete with no visible difference.
10. **Kanban artifact delivery requires BOTH the patch AND notify-subscribe.** The artifact fallback in `gateway/run.py` only fires for tasks with active `notify-subscribe`. If you create a test task without subscribing, the fallback won't trigger — even with the correct code. Always subscribe before testing. (See `references/kanban-artifact-fallback-patch.md`.)
11. **`hermes config migrate` — обязательный шаг после обновления, и он МОЖЕТ менять значения.** При крупном обновлении (v24→v29 и далее, проверено v33→v39) появляются новые опции конфига, которых нет в старой схеме. Без миграции `hermes doctor` покажет `Config version outdated`, а некоторые новые фичи могут не работать. ⚠️ Миграция добавляет недостающие опции **И** иногда переписывает существующие: на v0.20.6 она сбросила `personality` в `none` (был `kawaii`) и подняла `delegation.max_iterations` (50→250) и `delegation.max_concurrent_children` (3→10). После миграции сверь поведенческие настройки с пользователем и верни прежние значения, если они были осознанными.

12. **Stash конфликты после `git pull` — проверь upstream перед разрешением.** Когда после обновления `git stash pop` выдаёт merge conflict, **сначала проверь, не вмерджили ли твой патч в апстрим**:
    ```bash
    git log --oneline origin/main -- <файл> | head -10
    ```
    - Если есть коммит с той же функциональностью — **бери theirs** (upstream версия всегда качественнее)
    - Если нет — **бери ours** (локальный патч всё ещё нужен)
    - Если частично совпадает — разреши вручную, оставив лучшее из двух

    Конкретный пример из обновления v2026.6.5:
    - `tools/terminal_tool.py` (FileNotFoundError guard) — upstream commit `ad69d3edc` уже содержал `_safe_getcwd()`, лучше нашей версии → взяли theirs
    - `hermes_cli/kanban_db.py` (blocked event + cleanup subs on archive) — не было в upstream → взяли ours
    - `gateway/run.py` (kanban fallback + auto-subscribe) — upstream вынес watcher в `kanban_watchers.py` и сделал auto-subscribe на create по-своему → взяли theirs

    ⚠️ Никогда не принимай решение «на глаз» — всегда проверяй `git log` для каждого конфликтующего файла.
12. **PEP 668: `pip install -e .` упадёт в uv-венве.** Если venv создан через uv (проверить: `grep "^uv " venv/pyvenv.cfg`), то `pip install` вернёт `externally-managed-environment`. Используй `uv pip install -e .` внутри venv.

13. **`hermes kanban notify-subscribe` изменил синтаксис (v2026.6.5).** Раньше работали позиционные аргументы: `hermes kanban notify-subscribe T_ID telegram 350262645`. Теперь нужны флаги: `hermes kanban notify-subscribe T_ID --platform telegram --chat-id 350262645`. После обновления старые вызовы упадут с `error: the following arguments are required: --platform, --chat-id`. Исправь вызовы в памяти и навыках после апдейта.