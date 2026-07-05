from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
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
DB_DIR = PROJECT_ROOT / "db"
LOGS_DIR = PROJECT_ROOT / "logs"
