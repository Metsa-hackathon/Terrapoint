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
REQUIREMENTS_STAMP_FILE="/var/lib/terrapoint/.requirements-sha256"
LAST_DEPLOYED=$(cat "$STAMP_FILE" 2>/dev/null || true)
REQUIREMENTS_HASH=$(sha256sum requirements.txt | cut -d' ' -f1)
LAST_REQUIREMENTS_HASH=$(cat "$REQUIREMENTS_STAMP_FILE" 2>/dev/null || true)
INSTALL_REQUIREMENTS=0

if [ "$LAST_DEPLOYED" != "$LOCAL" ]; then
    NEEDS_RESTART=1
fi
if [ "$LAST_REQUIREMENTS_HASH" != "$REQUIREMENTS_HASH" ]; then
    INSTALL_REQUIREMENTS=1
    NEEDS_RESTART=1
fi

find_service_python() {
    local service_exec candidate
    service_exec=$(systemctl show --property=ExecStart --value terrapoint-api)
    while IFS= read -r candidate; do
        if [[ "$candidate" == */bin/uvicorn ]]; then
            candidate="${candidate%/uvicorn}/python"
        fi
        if [ -x "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done < <(printf '%s\n' "$service_exec" | grep -oE '/[^ ;}]*/bin/(python3?|uvicorn)' || true)
    for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python"; do
        if [ -x "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

if [ "$NEEDS_RESTART" -eq 1 ]; then
    if [ "$INSTALL_REQUIREMENTS" -eq 1 ]; then
        PYTHON_BIN=$(find_service_python) || {
            echo "$(date): Could not locate the terrapoint-api Python environment" >&2
            exit 1
        }
        echo "$(date): Installing pinned runtime dependencies with $PYTHON_BIN"
        "$PYTHON_BIN" -m pip install --disable-pip-version-check --no-input \
            --requirement requirements.txt
        "$PYTHON_BIN" -m pip check
    fi

    echo "$(date): Restarting terrapoint-api for commit $LOCAL"
    systemctl restart terrapoint-api

    HEALTHY=0
    for _attempt in $(seq 1 20); do
        if curl --fail --silent --show-error --max-time 3 \
            http://127.0.0.1:8099/api/health >/dev/null \
            && curl --fail --silent --show-error --max-time 3 \
            http://127.0.0.1:8099/ >/dev/null \
            && curl --fail --silent --show-error --max-time 3 \
            http://127.0.0.1:8099/static/js/app.js >/dev/null; then
            HEALTHY=1
            break
        fi
        sleep 0.5
    done
    if [ "$HEALTHY" -ne 1 ]; then
        echo "$(date): terrapoint-api failed its post-restart health check" >&2
        systemctl status --no-pager terrapoint-api >&2 || true
        exit 1
    fi

    # Record only a commit that actually reached a healthy process. If startup
    # fails, the timer retries this same commit on its next run.
    install -d -m 0755 /var/lib/terrapoint
    printf '%s\n' "$LOCAL" > "$STAMP_FILE"
    printf '%s\n' "$REQUIREMENTS_HASH" > "$REQUIREMENTS_STAMP_FILE"
    echo "$(date): Restarted terrapoint-api"
else
    echo "$(date): Already up to date ($LOCAL)"
fi
