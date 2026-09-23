# Adding Telegram Slash Commands to Hermes Agent

## TL;DR — quick_commands (для skill-задач, без кода)

Самый простой способ добавить слэш-команду `/evening` (запуск навыка) — **не требует правки кода**:

```bash
hermes config set quick_commands.evening.type alias
hermes config set quick_commands.evening.target evening-diary-brief
```

```yaml
# config.yaml — результат
quick_commands:
  morning:
    type: alias
    target: morning-ritual
  evening:
    type: alias
    target: evening-diary-brief
```

**Как работает:** `/evening` → gateway загружает навык `evening-diary-brief` в сессию → инструкции навыка выполняются.

**Этот способ подходит для:** запуска навыков (вечерний дневник, утренний ритуал, английский урок).
**НЕ подходит для:** команд с кастомной логикой, аргументами, подкомандами.

**После добавления — нужен /restart gateway** (или `hermes gateway restart` в терминале).

**Проверка:** убедись что команда видна в Telegram меню — `/commands` или набери `/evening`.

**Существующие команды через quick_commands (09.06.2026):**
- `/english` → english-lesson
- `/python` → python-road
- `/hub` → hermes-hub
- `/morning` → morning-ritual
- `/evening` → evening-diary-brief

---

## Полный путь (с кодом) — для кастомных команд

Если нужна НЕ загрузка навыка, а кастомная логика (аргументы, парсинг, состояния) — править три файла:

## Architecture

Telegram slash commands in Hermes span three layers:

```
hermes_cli/commands.py   <- COMMAND_REGISTRY (source of truth)
       │
       ▼
gateway/run.py           <- dispatch chain + handler methods
       │
       ▼
gateway/platforms/telegram.py  <- BotCommand menu registration
```

## How to Add a New Slash Command for Telegram

### 1. Register in `hermes_cli/commands.py`

```python
CommandDef("mycommand", "Description of the command", "Category",
           args_hint="[arg]", subcommands=("arg1", "arg2")),
```

Key flags:
- `cli_only=True` — only in CLI/TUI. **Excluded from Telegram entirely.**
- `gateway_only=True` — only in messaging platforms (Telegram, Discord, etc.)
- Neither — available everywhere (CLI + Telegram + gateway)
- `gateway_config_gate="section.key"` — CLI-only by default, but available in gateway when config value is truthy

**Common mistake:** leaving `cli_only=True` on commands that should work in Telegram.

### 2. Add dispatch branch in `gateway/run.py`

Find the big if-chain (around line 7595) and add:

```python
if canonical == "mycommand":
    return await self._handle_mycommand_command(event)
```

### 3. Implement handler method in `gateway/run.py`

Pattern:

```python
async def _handle_mycommand_command(self, event: MessageEvent) -> str:
    """Handle /mycommand."""
    args = event.get_command_args().strip()
    
    if not args or args == 'list':
        # Show listing
        ...
    
    # Handle subcommands
    if args.startswith('enable '):
        ...
    
    return "Result text for Telegram"
```

The method must return a string (or Optional[str], Union[str, EphemeralReply]).

### 4. Telegram menu auto-registration

Commands are automatically registered in Telegram's bot command menu via `telegram_menu_commands()` in `commands.py`. This calls `telegram_bot_commands()` which filters using `_is_gateway_available()`. Commands with `cli_only=True` are filtered out.

No manual Telegram API calls needed — adding to COMMAND_REGISTRY is sufficient.

## How Telegram Processes a Slash Command

1. User types `/command` — Telegram sends it to the bot webhook/polling
2. `telegram.py` adapter parses the message, detects `/` prefix, creates a `MessageEvent` with `get_command()` = "command"
3. `gateway/run.py::_handle_message()` is called, which routes to `_dispatch_command()`
4. The dispatch if-chain checks `canonical` against built-in command names
5. If matched → handler runs → returns string
6. If NOT a built-in → checks skill commands (`agent/skill_commands.py`)
7. If NOT a skill → `"Unknown command"` response

## Existing Commands Available in Telegram

See `GATEWAY_KNOWN_COMMANDS` in `commands.py` (line ~301). Commands with `cli_only=True` are excluded from this set unless they have a `gateway_config_gate`.

## Pitfalls

- **`cli_only=True` blocks everything.** The command won't even be dispatchable in the gateway — `GATEWAY_KNOWN_COMMANDS` filters it out.
- **`gateway_config_gate`** — use this pattern instead of `cli_only=True` when you want a config toggle rather than a hard block. Config path must exist in config.yaml.
- **Handler must be async.** Gateway runs in asyncio event loop.
- **No user interaction in handlers.** Handlers cannot call LLM or ask the user — they return a string synchronously (or via async methods).
- **Aliases are resolved** automatically by `resolve_command()` in the dispatch chain — no need to write separate handlers.
- **`telegram_menu_commands` caps at 30** (MAX_COMMANDS_PER_SCOPE). Beyond that, skills are hidden but still dispatchable manually by typing `/command-name`.

## Quick Reference: Change Flow

```
1. commands.py:  cli_only=True  →  gateway_config_gate="..."  (or remove cli_only)
2. run.py:       add if canonical == "name" branch
3. run.py:       add async def _handle_NAME_command method
4. Restart gateway or /restart in Telegram
```