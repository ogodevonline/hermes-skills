#!/usr/bin/env bash
# Gateway healthcheck
# Проверяет, жив ли гейтвей через systemd, и перезапускает если нет
#
# ВАЖНО: используется полный путь к systemd-утилитам, потому что
# cron/scheduled-задачи запускаются с минимальным PATH, где нет /usr/bin/
# (см. gateway-zombie-process skill → Pitfalls)

SYSTEMCTL="/usr/bin/systemctl"
LOGGER="/usr/bin/logger"
JOURNALCTL="/usr/bin/journalctl"
SERVICE="hermes-gateway"

if ! $SYSTEMCTL --user is-active --quiet "$SERVICE" 2>/dev/null; then
    $LOGGER -t "gateway-hc" "⚠️  $SERVICE inactive, restarting..."
    $SYSTEMCTL --user restart "$SERVICE"
    exit 0
fi

# Проверяем что есть свежие логи (нет логов >10 мин = возможно завис)
LAST_LOG=$($JOURNALCTL --user -u "$SERVICE" -n 1 --no-pager -o short-unix 2>/dev/null | /usr/bin/tail -1 | /usr/bin/cut -d' ' -f1)
if [ -n "$LAST_LOG" ]; then
    NOW=$(date +%s)
    LAST_TS=$(date -d "$LAST_LOG" +%s 2>/dev/null || echo 0)
    if [ "$LAST_TS" -gt 0 ] && [ $((NOW - LAST_TS)) -gt 600 ]; then
        $LOGGER -t "gateway-hc" "⚠️  No $SERVICE logs for 10+ min — restarting..."
        $SYSTEMCTL --user restart "$SERVICE"
        exit 0
    fi
fi

# всё ок
exit 0
