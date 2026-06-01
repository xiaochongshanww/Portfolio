import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_or_default(name: str, default: str) -> str:
    return os.getenv(name) or default


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_title: str = "结构设计规范知识库 RAG API (多模态)"
    app_version: str = "3.1.0"
    collection_name: str = "design_specs"

    zhipuai_api_key: str = field(default_factory=lambda: os.getenv("ZHIPUAI_API_KEY", ""))
    mimo_api_key: str = field(default_factory=lambda: os.getenv("MIMO_API_KEY", ""))
    mimo_base_url: str = field(default_factory=lambda: os.getenv("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1"))
    mimo_model: str = field(default_factory=lambda: os.getenv("MIMO_MODEL", "mimo-v2-omni"))
    llm_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("LLM_TIMEOUT_SECONDS", "180")))

    rag_top_k: int = field(default_factory=lambda: int(os.getenv("RAG_TOP_K", "12")))
    rag_min_score: float = field(default_factory=lambda: float(os.getenv("RAG_MIN_SCORE", "0.65")))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "embedding-2"))
    retrieval_dense_weight: float = field(default_factory=lambda: float(os.getenv("RETRIEVAL_DENSE_WEIGHT", "1.0")))
    retrieval_bm25_weight: float = field(default_factory=lambda: float(os.getenv("RETRIEVAL_BM25_WEIGHT", "0.18")))
    retrieval_clause_boost: float = field(default_factory=lambda: float(os.getenv("RETRIEVAL_CLAUSE_BOOST", "5.0")))
    rerank_enabled: bool = field(default_factory=lambda: _env_bool("RERANK_ENABLED", "false"))
    rerank_provider: str = field(default_factory=lambda: os.getenv("RERANK_PROVIDER", "none"))
    api_auth_enabled: bool = field(default_factory=lambda: _env_bool("API_AUTH_ENABLED", "false"))
    api_keys: list[str] = field(default_factory=lambda: _split_csv(os.getenv("API_KEYS", "")))
    max_request_bytes: int = field(default_factory=lambda: int(os.getenv("MAX_REQUEST_BYTES", "1048576")))
    rate_limit_enabled: bool = field(default_factory=lambda: _env_bool("RATE_LIMIT_ENABLED", "true"))
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "30")))

    db_dir: Path = field(default_factory=lambda: Path(_env_or_default("DB_DIR", "db")))
    img_dir: Path = field(default_factory=lambda: Path(_env_or_default("IMG_DIR", str(PROJECT_ROOT / "data" / "images"))))
    img_base_url: str = field(default_factory=lambda: os.getenv("IMG_BASE_URL", "/images"))
    static_dir: Path = field(default_factory=lambda: Path(_env_or_default("STATIC_DIR", str(PROJECT_ROOT / "src" / "static"))))

    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080"))
    )
    cors_allow_credentials: bool = field(
        default_factory=lambda: os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())


settings = Settings()
