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
