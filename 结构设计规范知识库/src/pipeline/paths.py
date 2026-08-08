import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env")


def configured_project_path(name: str, default: str | Path) -> Path:
    """Resolve an environment-backed path consistently from the project root."""
    raw_value = os.getenv(name)
    candidate = (Path(raw_value) if raw_value else Path(default)).expanduser()
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve()


DATA_DIR = configured_project_path("DATA_DIR", "data")
RAW_DIR = DATA_DIR / "raw"
METADATA_DIR = DATA_DIR / "metadata"
PROCESSED_DIR = DATA_DIR / "processed"
IMAGES_DIR = DATA_DIR / "images"
MINERU_DIR = DATA_DIR / "mineru"
AUDIT_DIR = DATA_DIR / "audit"
CORRECTIONS_DIR = DATA_DIR / "corrections"
MANUAL_STRUCTURING_DIR = DATA_DIR / "manual_structuring"
STRUCTURED_TABLES_DIR = DATA_DIR / "structured_tables"
MANIFEST_PATH = DATA_DIR / "manifest.json"
DB_VERSIONS_DIR = DATA_DIR / "db_versions"
ACTIVE_DB_PATH = DATA_DIR / "active_db.json"
DB_DIR = configured_project_path("DB_DIR", "db")
LOGS_DIR = PROJECT_ROOT / "logs"
