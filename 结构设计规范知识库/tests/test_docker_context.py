from pathlib import Path

from scripts.validate_docker_context import build_report, validate_policy_text

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _rules() -> list[str]:
    return [
        line.strip()
        for line in (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def test_docker_context_uses_default_deny_allowlist() -> None:
    rules = _rules()

    assert rules[0] == "**"
    assert "!requirements-runtime.txt" in rules
    assert "!src/**" in rules
    assert "!frontend/**" not in rules
    assert "!frontend/src/**" in rules
    assert "!frontend/public/**" in rules
    assert "!frontend/vite.config.ts" in rules
    assert "!data/evaluation/**" in rules
    assert "!data/metadata/**" in rules


def test_docker_context_rejects_nested_generated_and_secret_inputs() -> None:
    rules = _rules()

    for rule in (
        "**/.env*",
        "**/__pycache__/",
        "**/*.pyc",
    ):
        assert rule in rules


def test_repository_docker_context_policy_passes() -> None:
    report = build_report(
        dockerignore_path=PROJECT_ROOT / ".dockerignore",
        dockerfile_path=PROJECT_ROOT / "Dockerfile",
    )

    assert report == {
        "ok": True,
        "allow_rule_count": 21,
        "copy_source_count": 12,
        "errors": [],
    }


def test_validator_rejects_missing_default_deny() -> None:
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    errors = validate_policy_text(dockerignore.replace("**\n", "", 1), dockerfile)

    assert "DEFAULT_DENY_MISSING" in {error.code for error in errors}


def test_validator_rejects_unreviewed_allow_rule() -> None:
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    errors = validate_policy_text(f"{dockerignore}\n!docs/**\n", dockerfile)

    assert "UNREVIEWED_ALLOW_RULE" in {error.code for error in errors}


def test_validator_rejects_missing_nested_exclusion() -> None:
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    errors = validate_policy_text(
        dockerignore.replace("**/.env*\n", ""),
        dockerfile,
    )

    assert "NESTED_DENY_MISSING" in {error.code for error in errors}


def test_validator_rejects_unreviewed_local_copy_source() -> None:
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    errors = validate_policy_text(
        f"{dockerignore}\n!docs/**\n", f"{dockerfile}\nCOPY docs/ docs/\n"
    )

    codes = {error.code for error in errors}
    assert "UNREVIEWED_ALLOW_RULE" in codes
    assert "UNREVIEWED_COPY_SOURCE" in codes
