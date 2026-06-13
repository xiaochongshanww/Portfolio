import os
from pathlib import Path


def find_project_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").exists() and (cwd / "config").exists():
        return cwd

    package_root = Path(__file__).resolve().parents[2]
    if (package_root / "pyproject.toml").exists():
        return package_root

    return cwd


PROJECT_ROOT = find_project_root()
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = DATA_DIR / "recruitment.sqlite"

LLM_API_KEY: str | None = os.environ.get(
    "LLM_API_KEY"
) or os.environ.get(
    "ANTHROPIC_API_KEY"
) or "sk-378e29cb7dd54caf9c711a225e0cbb43"
LLM_MODEL: str = os.environ.get("LLM_MODEL", "deepseek-chat")
LLM_BASE_URL: str = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
