#!/bin/bash
# Disk space checker for cron — пишет в stdout только если диск >75%
# Пустой stdout = тишина (cron no_agent=True)

pct=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
free=$(df -h / | tail -1 | awk '{print $4}')

if [ "$pct" -gt 75 ]; then
    echo "⚡ Диск забит на ${pct}% (свободно ${free})"
    echo ""
    echo "Запусти чистку: скажи мне \"почисти диск\""
    echo ""
    echo "Или сделай сам:"
    echo "  bash ~/.hermes/skills/clean-disk/scripts/clean-disk.sh"
    echo ""
    echo "Для полной очистки (с sudo):"
    echo "  sudo journalctl --vacuum-time=7d && sudo apt clean"
elif [ "$pct" -gt 60 ]; then
    echo "💿 Диск на ${pct}% — пока норм (свободно ${free})"
fi
