import importlib.util
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HTTPX2_REQUIREMENT = "httpx2>=2,<3"
STARLETTE_FALLBACK_WARNING = "error::DeprecationWarning:starlette"


def _requirement_lines(filename: str) -> set[str]:
    return {
        line.strip()
        for line in (PROJECT_ROOT / filename).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def test_httpx2_is_a_development_only_direct_dependency():
    assert HTTPX2_REQUIREMENT in _requirement_lines("requirements-dev.in")
    assert HTTPX2_REQUIREMENT not in _requirement_lines("requirements-runtime.in")
    assert HTTPX2_REQUIREMENT not in _requirement_lines("requirements-parser.in")


def test_pytest_rejects_starlette_httpx_fallback_warning():
    config = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert STARLETTE_FALLBACK_WARNING in config["tool"]["pytest"]["ini_options"]["filterwarnings"]


def test_httpx2_is_installed_for_starlette_testclient():
    assert importlib.util.find_spec("httpx2") is not None
