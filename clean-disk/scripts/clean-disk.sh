#!/bin/bash
# Disk cleanup script for cron — не требует sudo
# Запуск: bash ~/.hermes/skills/clean-disk/scripts/clean-disk.sh

set -e

freed=0

echo "=== Clean Disk: $(date) ==="

# 1. uv cache
if command -v uv &>/dev/null; then
    echo "[uv] Cleaning cache..."
    freed_uv=$(uv cache clean 2>&1 | grep -oP '[\d.]+[KMG]?i?B' | tail -1)
    echo "[uv] Freed: $freed_uv"
fi

# 2. npm cache
if command -v npm &>/dev/null; then
    echo "[npm] Cleaning cache..."
    npm cache clean --force 2>/dev/null
    echo "[npm] Done"
fi

# 3. npm-local (_npx cache)
if [ -d "$HOME/.npm-local" ]; then
    size=$(du -sh "$HOME/.npm-local" 2>/dev/null | cut -f1)
    rm -rf "$HOME/.npm-local"
    echo "[npm-local] Freed: $size"
fi

# 4. pip cache
if [ -d "$HOME/.cache/pip" ]; then
    size=$(du -sh "$HOME/.cache/pip" 2>/dev/null | cut -f1)
    rm -rf "$HOME/.cache/pip"
    echo "[pip] Freed: $size"
fi

# 5. Старые сессии Hermes (>7 дней)
if [ -d "$HOME/.hermes/sessions" ]; then
    before=$(ls "$HOME/.hermes/sessions" 2>/dev/null | wc -l)
    cutoff=$(date -d '7 days ago' +%Y%m%d)
    for f in "$HOME/.hermes/sessions"/[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_*.jsonl; do
        [ -f "$f" ] || continue
        d=$(basename "$f" | cut -c1-8)
        if [ "$d" -lt "$cutoff" ]; then
            rm -f "$f"
        fi
    done
    after=$(ls "$HOME/.hermes/sessions" 2>/dev/null | wc -l)
    removed=$((before - after))
    echo "[sessions] Removed: $removed files"
fi

# 6. ms-playwright (если вдруг появился после переустановки)
if [ -d "$HOME/.cache/ms-playwright" ]; then
    size=$(du -sh "$HOME/.cache/ms-playwright" 2>/dev/null | cut -f1)
    rm -rf "$HOME/.cache/ms-playwright"
    echo "[ms-playwright] Freed: $size"
fi

# 7. camoufox (если появился)
if [ -d "$HOME/.cache/camoufox" ]; then
    size=$(du -sh "$HOME/.cache/camoufox" 2>/dev/null | cut -f1)
    rm -rf "$HOME/.cache/camoufox"
    echo "[camoufox] Freed: $size"
fi

# 8. huggingface cache
if [ -d "$HOME/.cache/huggingface" ]; then
    size=$(du -sh "$HOME/.cache/huggingface" 2>/dev/null | cut -f1)
    rm -rf "$HOME/.cache/huggingface"
    echo "[huggingface] Freed: $size"
fi

echo "=== Complete ==="
df -h / | tail -1
