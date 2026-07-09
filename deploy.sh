#!/bin/bash
# Auto-deploy Terrapoint API from GitHub
# Restarts the service when new code is available — whether pushed from
# GitHub (REMOTE != LOCAL) or committed directly on this VPS (HEAD changed
# since the service last started).
set -e
cd /root/projects/terrapoint
git fetch origin master 2>/dev/null || true
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/master)
NEEDS_RESTART=0

# Case 1: GitHub has newer code than local — pull and restart
if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$(date): Updating from $LOCAL to $REMOTE"
    git pull --rebase origin master
    NEEDS_RESTART=1
fi

# Case 2: Local HEAD is ahead of or equal to remote (committed on VPS),
# but the running service started before the latest commit — restart
# so it picks up the new code.
COMMIT_TIME=$(git log -1 --format=%ct HEAD)
SERVICE_START=$(systemctl show terrapoint-api --property=ActiveEnterTimestampMonotonic --value 2>/dev/null)
if [ -n "$SERVICE_START" ] && [ "$SERVICE_START" != "0" ]; then
    # ActiveEnterTimestampMonotonic is in monotonic clock microseconds,
    # not comparable to epoch. Use ActivatedSince from systemctl instead.
    :
fi
# Get service start time as epoch seconds
SERVICE_START_EPOCH=$(systemctl show terrapoint-api --property=ExecMainStartTimestampMonotonic --value 2>/dev/null || echo 0)
# ExecMainStartTimestamp is monotonic; use a simpler check: compare HEAD
# commit epoch vs the file that deploy.sh touches on each restart.
STAMP_FILE="/var/lib/terrapoint/.last-deploy-commit"
LAST_DEPLOYED=$(cat "$STAMP_FILE" 2>/dev/null || echo "")

if [ "$LAST_DEPLOYED" != "$LOCAL" ]; then
    NEEDS_RESTART=1
fi

if [ "$NEEDS_RESTART" -eq 1 ]; then
    echo "$(date): Restarting terrapoint-api for commit $LOCAL"
    systemctl restart terrapoint-api
    mkdir -p /var/lib/terrapoint
    echo "$LOCAL" > "$STAMP_FILE"
    echo "$(date): Restarted terrapoint-api"
else
    echo "$(date): Already up to date ($LOCAL)"
fi