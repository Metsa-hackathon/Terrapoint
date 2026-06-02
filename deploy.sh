#!/bin/bash
# Auto-deploy Terrapoint API from GitHub
set -e
cd /root/projects/terrapoint
git fetch origin master
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/master)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$(date): Updating from $LOCAL to $REMOTE"
    git pull --rebase origin master
    systemctl restart terrapoint-api
    echo "$(date): Restarted terrapoint-api"
else
    echo "$(date): Already up to date ($LOCAL)"
fi
