import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
RUFF_VERSION = "0.16.2"
RUFF_TARGETS = "src scripts tests"


def test_ruff_configuration_is_explicit_and_has_no_global_waiver():
    config = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ruff = config["tool"]["ruff"]

    assert ruff["target-version"] == "py311"
    assert ruff["line-length"] == 100
    assert ruff["src"] == ["src", "scripts", "tests"]
    assert ruff["lint"]["select"] == ["E4", "E7", "E9", "F", "I", "B", "UP"]
    assert "ignore" not in ruff["lint"]
    assert "per-file-ignores" not in ruff["lint"]
    assert ruff["format"]["line-ending"] == "lf"


def test_ruff_is_pinned_only_in_development_dependencies():
    development_input = (PROJECT_ROOT / "requirements-dev.in").read_text(encoding="utf-8")
    development_lock = (PROJECT_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    runtime_lock = (PROJECT_ROOT / "requirements-runtime.txt").read_text(encoding="utf-8")
    parser_lock = (PROJECT_ROOT / "requirements-parser.txt").read_text(encoding="utf-8")

    requirement = f"ruff=={RUFF_VERSION}"
    assert requirement in development_input.splitlines()
    assert requirement in development_lock
    assert requirement not in runtime_lock
    assert requirement not in parser_lock


def test_backend_ci_runs_the_same_lint_and_format_commands():
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "structural-spec-kb-ci.yml").read_text(
        encoding="utf-8"
    )
    backend = workflow.split("  backend:", 1)[1].split("  frontend:", 1)[0]

    assert f"python -m ruff check {RUFF_TARGETS}" in backend
    assert f"python -m ruff format --check {RUFF_TARGETS}" in backend
    assert "matrix:" in backend and "ubuntu-latest" in backend and "windows-latest" in backend


def test_git_normalizes_python_quality_files_to_lf():
    attributes = (PROJECT_ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "*.py text eol=lf" in attributes.splitlines()
    assert "pyproject.toml text eol=lf" in attributes.splitlines()
