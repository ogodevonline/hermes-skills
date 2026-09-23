#!/bin/bash
# Check for stuck Chromium renderer processes (>5 min runtime)
# Use: bash ~/.hermes/skills/productivity/insta-flat-parser/scripts/check-stuck-renderers.sh

THRESHOLD_MINUTES=5

echo "=== Chromium renderer processes ==="
ps -eo pid,etimes,args --sort=etimes | grep 'type=renderer' | grep -v grep | while read pid etimes rest; do
  if [ "$etimes" -gt $((THRESHOLD_MINUTES * 60)) ]; then
    echo "⚠️  PID=$pid runtime=${etimes}s (>${THRESHOLD_MINUTES}min) — STUCK"
    echo "   Kill with: kill $pid"
  else
    echo "   PID=$pid runtime=${etimes}s — OK"
  fi
done

# Count renderers
count=$(ps aux | grep 'type=renderer' | grep -v grep | wc -l)
echo "---"
echo "Total renderer processes: $count"

if [ "$count" -gt 3 ]; then
  echo "⚠️  WARNING: $count renderers suggests stuck pages accumulating"
fi
