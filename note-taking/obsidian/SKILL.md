---
name: obsidian
description: Git-synced Obsidian vault — Hermes writes notes and auto-pushes, user reads on phone via git pull.
---

# Obsidian Git-Synced Vault

Vault location is configured via `OBSIDIAN_VAULT_PATH` env var.
Default: `~/Documents/Obsidian Vault`.

The vault is a **git repository** — Hermes writes notes, commits, and pushes automatically.
User pulls on phone (Termux + Obsidian) to read.

## ⚙️ Setup (one-time)

### 1. User creates a GitHub repo
e.g. `hermes-vault` (public or private).

### 2. User generates a GitHub token
GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic).
Scope: `repo`. Set "No expiration".

### 3. Initialize vault on server

```bash
mkdir -p ~/hermes-vault && cd ~/hermes-vault
mkdir -p "Дневник" "OSINT" "Идеи" "Проекты" "Research" "Привычки" "Inbox"
git init
git remote add origin <github-url-with-token>
git config user.email "hermes@local"
git config user.name "Hermes"
echo ".DS_Store" > .gitignore
```

Store git credential: `git config credential.helper store`, then first push will prompt.

Set env in agent config: add `OBSIDIAN_VAULT_PATH=<path>` to env file.

### 4. First commit and push

```bash
git add -A && git commit -m "init: vault structure"
git branch -m main && git push -u origin main
```

## 📱 User setup on phone

### Android (Termux)

```bash
pkg install git
cd /storage/shared/Obsidian
git clone <github-url-with-token> Hermes
```

Then Obsidian → "Open folder as vault" → `Obsidian/Hermes`.

### iOS (Working Copy)
Install Working Copy → clone the repo → open in Obsidian.

## 📝 Writing notes

```bash
VAULT="${OBSIDIAN_VAULT_PATH}"
```

### Read: `cat "$VAULT/Path/Note.md"`
### List: `find "$VAULT" -name "*.md" -type f`
### Search by content: `grep -rli "keyword" "$VAULT" --include="*.md"`
### Create: `cat > "$VAULT/Note.md" << 'ENDNOTE' ... ENDNOTE`
### Append: `echo -e "\n## Section\n\nContent." >> "$VAULT/Note.md"`

Use `[[Title]]` wikilinks to connect notes.

## 🚀 Auto-push (mandatory)

After every note write:

```bash
cd "$VAULT"
git add -A && git commit -m "brief description" && git push
```

## 📁 Recommended structure

```
hermes-vault/
├── Дневник/YYYY-MM-DD.md       # daily notes
├── OSINT/                      # analysis results
├── Идеи/                       # project ideas
├── Проекты/                    # per-project notes
├── Research/                   # summaries
├── Привычки/Tracker.md         # habit tracking
├── Inbox/                      # quick captures
└── index.md                    # landing with wiki links
```

## ⚠️ Pitfalls

- Token must not expire — remind user "No expiration"
- User must create GitHub repo before first push
- Termux: use `/storage/shared/Obsidian/` so files are visible to Obsidian
- Full git history: deleted notes recoverable via `git revert`
- Occasional `git gc` keeps repo small
