#!/usr/bin/env bash
# Weekly Hermes update check — no_agent watchdog
# Prints nothing if up-to-date, prints changelog if behind
# Intended to be run as a cron job: script=hermes-update-check.sh, no_agent=true

set -eo pipefail

REPO="$HOME/.hermes/hermes-agent"
cd "$REPO" || exit 0

# Fetch latest tags/commits
git fetch --tags origin main --quiet 2>/dev/null || exit 0

CURRENT=$(git rev-parse HEAD 2>/dev/null || exit 0)
LATEST_TAG=$(git tag --sort=-creatordate | head -1)

[ -n "$LATEST_TAG" ] || exit 0

# Check if current HEAD is at or past the latest tag
if git merge-base --is-ancestor "$LATEST_TAG" HEAD 2>/dev/null; then
    # Up to date or ahead — silent exit
    exit 0
fi

# Count commits behind
BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo "?")
CURRENT_TAG=$(git describe --tags --always 2>/dev/null || echo "unknown")

echo "📦 Hermes update available!"
echo "   Current: $CURRENT_TAG"
echo "   Latest:  $LATEST_TAG ($BEHIND commits behind)"
echo ""
echo "📝 Key changes:"
git log --oneline HEAD..origin/main --no-merges --format="- %s" | head -30
echo ""
echo "Run \`hermes update\` or ask the agent to update."
