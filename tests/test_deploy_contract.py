from pathlib import Path


DEPLOY_SCRIPT = (Path(__file__).parents[1] / "deploy.sh").read_text()


def test_deploy_is_serialized_and_fast_forward_only():
    assert "flock -n" in DEPLOY_SCRIPT
    assert "git merge --ff-only" in DEPLOY_SCRIPT
    assert "git pull --rebase" not in DEPLOY_SCRIPT


def test_deploy_refuses_dirty_or_diverged_checkout():
    assert "git status --porcelain" in DEPLOY_SCRIPT
    assert "git merge-base --is-ancestor" in DEPLOY_SCRIPT
    assert "exit 1" in DEPLOY_SCRIPT


def test_deploy_installs_changed_runtime_dependencies_before_restart():
    install_index = DEPLOY_SCRIPT.index("--requirement requirements.txt")
    check_index = DEPLOY_SCRIPT.index('"$PYTHON_BIN" -m pip check')
    restart_index = DEPLOY_SCRIPT.index("systemctl restart terrapoint-api")

    assert install_index < check_index < restart_index
    assert "sha256sum requirements.txt" in DEPLOY_SCRIPT
    assert "systemctl show --property=ExecStart" in DEPLOY_SCRIPT
    assert "REQUIREMENTS_STAMP_FILE" in DEPLOY_SCRIPT


def test_deploy_records_commit_only_after_the_restarted_api_is_healthy():
    restart_index = DEPLOY_SCRIPT.index("systemctl restart terrapoint-api")
    health_index = DEPLOY_SCRIPT.index("http://127.0.0.1:8099/api/health")
    stamp_index = DEPLOY_SCRIPT.index("printf '%s\\n' \"$LOCAL\" > \"$STAMP_FILE\"")
    requirements_stamp_index = DEPLOY_SCRIPT.index(
        "printf '%s\\n' \"$REQUIREMENTS_HASH\" > \"$REQUIREMENTS_STAMP_FILE\""
    )

    assert restart_index < health_index < stamp_index
    assert health_index < requirements_stamp_index
    assert "curl --fail" in DEPLOY_SCRIPT
    assert "http://127.0.0.1:8099/ >/dev/null" in DEPLOY_SCRIPT
    assert "http://127.0.0.1:8099/static/js/app.js" in DEPLOY_SCRIPT
