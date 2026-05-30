#!/bin/bash
# Auto-deploy Terrapoint API from GitHub
cd /root/projects/terrapoint
git fetch origin master
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/master)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$(date): Updating from $LOCAL to $REMOTE"
    git pull origin master
    systemctl restart terrapoint-api
    echo "$(date): Restarted terrapoint-api"
fi
