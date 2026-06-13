import os
from pathlib import Path


def _load_dotenv() -> None:
    """Load .env file if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parents[2] / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass


_load_dotenv()


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key, "").strip().lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


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
RAW_ARCHIVE_DIR = DATA_DIR / "raw"

# --- App ---
APP_ENV: str = os.environ.get("APP_ENV", "development")
APP_HOST: str = os.environ.get("APP_HOST", "127.0.0.1")
APP_PORT: int = _env_int("APP_PORT", 8001)

# --- LLM / DeepSeek ---
LLM_API_KEY: str | None = (
    os.environ.get("LLM_API_KEY")
    or os.environ.get("ANTHROPIC_API_KEY")
    or "sk-378e29cb7dd54caf9c711a225e0cbb43"
)
LLM_MODEL: str = os.environ.get("LLM_MODEL", "deepseek-chat")
LLM_BASE_URL: str = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
LLM_DAILY_LIMIT: int = _env_int("LLM_DAILY_LIMIT", 200)
LLM_MAX_JOBS: int = _env_int("LLM_MAX_JOBS", 20)
LLM_TIMEOUT_SECONDS: int = _env_int("LLM_TIMEOUT_SECONDS", 60)

# --- API Security ---
CORS_ALLOWED_ORIGINS: str = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173" if APP_ENV == "development" else "",
)
API_ACCESS_TOKEN: str | None = os.environ.get("API_ACCESS_TOKEN") or None
RATE_LIMIT_ENABLED: bool = _env_bool("RATE_LIMIT_ENABLED", APP_ENV != "development")
RATE_LIMIT_REQUESTS: int = _env_int("RATE_LIMIT_REQUESTS", 30)
RATE_LIMIT_WINDOW_SECONDS: int = _env_int("RATE_LIMIT_WINDOW_SECONDS", 60)
MAX_REQUEST_BODY_BYTES: int = _env_int("MAX_REQUEST_BODY_BYTES", 65536)

# --- Collection ---
HTTP_CONCURRENCY: int = _env_int("HTTP_CONCURRENCY", 5)
BROWSER_CONCURRENCY: int = _env_int("BROWSER_CONCURRENCY", 1)
DETAIL_CONCURRENCY: int = _env_int("DETAIL_CONCURRENCY", 3)
COLLECT_TIMEOUT_SECONDS: int = _env_int("COLLECT_TIMEOUT_SECONDS", 30)
COLLECT_MAX_RETRIES: int = _env_int("COLLECT_MAX_RETRIES", 2)

# --- Logging ---
LOG_FORMAT: str = os.environ.get("LOG_FORMAT", "text")  # "text" or "json"
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
