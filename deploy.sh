#!/bin/bash
# Auto-deploy Terrapoint API from GitHub without mutating a dirty or diverged
# production checkout.
set -euo pipefail

exec 9>/run/lock/terrapoint-deploy.lock
if ! flock -n 9; then
    echo "$(date): Another Terrapoint deployment is already running"
    exit 0
fi

cd /root/projects/terrapoint

if [ -n "$(git status --porcelain)" ]; then
    echo "$(date): Refusing to deploy a dirty checkout" >&2
    exit 1
fi

git fetch origin master
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/master)
NEEDS_RESTART=0

# Fast-forward only when GitHub is ahead. Never rebase a live checkout.
if [ "$LOCAL" != "$REMOTE" ]; then
    if git merge-base --is-ancestor "$LOCAL" "$REMOTE"; then
        echo "$(date): Updating from $LOCAL to $REMOTE"
        git merge --ff-only "$REMOTE"
        LOCAL=$REMOTE
        NEEDS_RESTART=1
    elif git merge-base --is-ancestor "$REMOTE" "$LOCAL"; then
        echo "$(date): Local checkout is ahead of origin/master"
    else
        echo "$(date): Refusing to deploy diverged Git histories" >&2
        exit 1
    fi
fi

STAMP_FILE="/var/lib/terrapoint/.last-deploy-commit"
LAST_DEPLOYED=$(cat "$STAMP_FILE" 2>/dev/null || true)

if [ "$LAST_DEPLOYED" != "$LOCAL" ]; then
    NEEDS_RESTART=1
fi

if [ "$NEEDS_RESTART" -eq 1 ]; then
    echo "$(date): Restarting terrapoint-api for commit $LOCAL"
    systemctl restart terrapoint-api
    install -d -m 0755 /var/lib/terrapoint
    printf '%s\n' "$LOCAL" > "$STAMP_FILE"
    echo "$(date): Restarted terrapoint-api"
else
    echo "$(date): Already up to date ($LOCAL)"
fi
