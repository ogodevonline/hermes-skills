# x-ui / 3x-ui proxy panel — install, update, GitHub-rot resilience

Session: 2026-08 — user's install command pointed at `mhtsll/x-ui` → 404 (repo deleted).

## Repo status (verified 2026-08 via GitHub API)

| Repo | Status | Last release | Notes |
|------|--------|--------------|-------|
| `MHSanaei/3x-ui` | ✅ active | v3.6.0 (2026-07-30), commits 2026-08 | **Use this one.** Actively maintained fork |
| `vaxilu/x-ui` | 💀 abandoned | 0.3.2 (2021-08-25) | Original; dead since 2021, still reachable (19k ⭐) |
| `mhtsll/x-ui` | ❌ 404 | — | Obsolete fork from some tutorial; deleted |

## Why links rot (user's question "как так происходит?")

1. Original abandoned → dozens of forks, tutorials copy random fork URLs.
2. GitHub periodically bans proxy/circumvention repos (late 2024 wave hit x-ui, Hiddify, etc.; original was removed then restored).
3. Small fork repos get deleted by authors or GitHub → old tutorials keep broken links.

## Install (current, stable)

```bash
bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)
```

Update via panel menu or `x-ui update` (on server, as root).

## What breaks if GitHub drops the repo again

Install.sh fetches version from `api.github.com/repos/MHSanaei/3x-ui/releases/latest`
and downloads tarball from `github.com/MHSanaei/3x-ui/releases/download/...`.
→ If repo is deleted: NEW installs and updates break. A panel ALREADY installed
keeps running (binary + systemd service), only updating dies.

## Resilience / backup (2 min, do once)

```bash
mkdir -p ~/backup/3x-ui && cd ~/backup/3x-ui
curl -Ls https://raw.githubusercontent.com/MHSanaei/3x-ui/master/install.sh -o install.sh
curl -Ls https://api.github.com/repos/MHSanaei/3x-ui/releases/latest \
  | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/' > VERSION
curl -Lso x-ui-linux-amd64.tar.gz \
  https://github.com/MHSanaei/3x-ui/releases/download/$(cat VERSION)/x-ui-linux-amd64.tar.gz
```

~40 MB. Manual install from local archive possible if GitHub dies.

## Alternative sources if GitHub blocked

- Docker Hub image `mhsanaei/3x-ui` (not controlled by GitHub).
- Official Telegram channels listed in README — authors publish mirrors during bans.
- 3x-ui survived the 2024 ban wave (original vaxilu/x-ui was removed, fork survived).

## Verification pattern before running ANY github install script

```bash
curl -s -o /dev/null -w "%{http_code}" https://raw.githubusercontent.com/OWNER/REPO/master/install.sh
# 404 → repo gone, find the active fork instead of debugging the old URL
```
