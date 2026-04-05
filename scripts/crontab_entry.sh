#!/usr/bin/env bash
# Run this script once to register the @reboot crontab entry.
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENTRY="@reboot cd $REPO_DIR && bash scripts/start_all.sh >> data/logs/boot.log 2>&1"

( crontab -l 2>/dev/null | grep -v 'start_all'; echo "$ENTRY" ) | crontab -
echo "Crontab registered:"
crontab -l | grep start_all
