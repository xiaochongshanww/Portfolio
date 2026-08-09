from pathlib import Path

from scripts.validate_ci_actions import build_report, default_workflow_directory


def _write_workflow(directory: Path, body: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "ci.yml").write_text(body, encoding="utf-8")


def test_repository_actions_are_immutable_and_runtime_current():
    report = build_report(default_workflow_directory())

    assert report["ok"] is True
    assert report["workflow_count"] >= 1
    assert report["external_reference_count"] >= 1


def test_mutable_action_and_missing_version_comment_are_rejected(tmp_path: Path):
    workflows = tmp_path / "workflows"
    _write_workflow(
        workflows,
        "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@v6\n",
    )

    report = build_report(workflows)
    codes = {error["code"] for error in report["errors"]}

    assert report["ok"] is False
    assert "ACTION_REF_MUTABLE" in codes
    assert "ACTION_VERSION_COMMENT_MISSING" in codes


def test_deprecated_action_runtime_generation_is_rejected(tmp_path: Path):
    workflows = tmp_path / "workflows"
    _write_workflow(
        workflows,
        (
            "jobs:\n  test:\n    steps:\n"
            "      - uses: actions/upload-artifact@"
            "1111111111111111111111111111111111111111 # v4.6.2\n"
        ),
    )

    report = build_report(workflows)

    assert report["ok"] is False
    assert [error["code"] for error in report["errors"]] == [
        "ACTION_RUNTIME_DEPRECATED"
    ]


def test_local_and_container_actions_do_not_require_git_commit_refs(tmp_path: Path):
    workflows = tmp_path / "workflows"
    _write_workflow(
        workflows,
        (
            "jobs:\n  test:\n    steps:\n"
            "      - uses: ./local-action\n"
            "      - uses: docker://alpine:3.22\n"
            "      - uses: owner/action@"
            "2222222222222222222222222222222222222222 # v1.2.3\n"
        ),
    )

    report = build_report(workflows)

    assert report["ok"] is True
    assert report["external_reference_count"] == 1


def test_dependabot_maintains_github_action_pins():
    config = default_workflow_directory().parent / "dependabot.yml"
    text = config.read_text(encoding="utf-8")

    assert 'package-ecosystem: "github-actions"' in text
    assert 'directory: "/"' in text
    assert "interval: weekly" in text
