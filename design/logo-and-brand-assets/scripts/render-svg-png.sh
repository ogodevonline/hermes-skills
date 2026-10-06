#!/usr/bin/env bash
# Render .svg files to same-named .png using Playwright's bundled Chromium (no network, no extra deps).
# Usage: render-svg-png.sh [SIZE] file.svg [file2.svg ...]     SIZE defaults to 1024.
set -euo pipefail

SIZE=1024
if [[ "${1:-}" =~ ^[0-9]+$ ]]; then SIZE="$1"; shift; fi
[[ $# -gt 0 ]] || { echo "usage: $0 [SIZE] file.svg [file2.svg ...]" >&2; exit 2; }

CHROME="$(ls -d "$HOME"/.cache/ms-playwright/chromium-*/chrome-linux64/chrome 2>/dev/null | head -1 || true)"
if [[ -z "$CHROME" || ! -x "$CHROME" ]]; then
  echo "chromium not found under ~/.cache/ms-playwright - install with: npx playwright install chromium" >&2
  exit 1
fi

for svg in "$@"; do
  svg="$(realpath "$svg")"
  out="${svg%.svg}.png"
  "$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=1 --window-size="$SIZE,$SIZE" \
    --screenshot="$out" "file://$svg" >/dev/null 2>&1
  echo "rendered: $out"
done
