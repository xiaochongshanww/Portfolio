import os
from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}
PLACEHOLDER_API_KEYS = {"change-me", "changeme", "not-needed", "your-api-key"}
VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


class ConfigurationError(ValueError):
    def __init__(self, issues: list[str] | str):
        self.issues = (issues,) if isinstance(issues, str) else tuple(issues)
        super().__init__("配置校验失败：\n- " + "\n- ".join(self.issues))


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_or_default(name: str, default: str) -> str:
    return os.getenv(name) or default


def _env_bool(name: str, default: str = "false") -> bool:
    value = os.getenv(name, default).strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise ConfigurationError(f"{name} 必须是布尔值（true/false、1/0、yes/no 或 on/off），当前为 {value!r}")


def _env_int(name: str, default: str) -> int:
    value = os.getenv(name, default).strip()
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} 必须是整数，当前为 {value!r}") from exc


def _env_float(name: str, default: str) -> float:
    value = os.getenv(name, default).strip()
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} 必须是数字，当前为 {value!r}") from exc
    if not isfinite(parsed):
        raise ConfigurationError(f"{name} 必须是有限数字，当前为 {value!r}")
    return parsed


@dataclass(frozen=True)
class Settings:
    app_title: str = "结构设计规范知识库 RAG API (多模态)"
    app_version: str = "3.1.0"
    collection_name: str = "design_specs"

    zhipuai_api_key: str = field(default_factory=lambda: os.getenv("ZHIPUAI_API_KEY", ""))
    mimo_api_key: str = field(default_factory=lambda: os.getenv("MIMO_API_KEY", ""))
    mimo_base_url: str = field(default_factory=lambda: os.getenv("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1"))
    mimo_model: str = field(default_factory=lambda: os.getenv("MIMO_MODEL", "mimo-v2.5"))
    llm_timeout_seconds: int = field(default_factory=lambda: _env_int("LLM_TIMEOUT_SECONDS", "180"))

    rag_top_k: int = field(default_factory=lambda: _env_int("RAG_TOP_K", "12"))
    rag_min_score: float = field(default_factory=lambda: _env_float("RAG_MIN_SCORE", "0.65"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "embedding-2"))
    retrieval_dense_weight: float = field(default_factory=lambda: _env_float("RETRIEVAL_DENSE_WEIGHT", "1.0"))
    retrieval_bm25_weight: float = field(default_factory=lambda: _env_float("RETRIEVAL_BM25_WEIGHT", "0.18"))
    retrieval_clause_boost: float = field(default_factory=lambda: _env_float("RETRIEVAL_CLAUSE_BOOST", "5.0"))
    rerank_enabled: bool = field(default_factory=lambda: _env_bool("RERANK_ENABLED", "false"))
    rerank_provider: str = field(default_factory=lambda: os.getenv("RERANK_PROVIDER", "none"))
    api_auth_enabled: bool = field(default_factory=lambda: _env_bool("API_AUTH_ENABLED", "false"))
    api_keys: list[str] = field(default_factory=lambda: _split_csv(os.getenv("API_KEYS", "")))
    openwebui_api_key: str = field(default_factory=lambda: os.getenv("OPENWEBUI_API_KEY", "").strip())
    asset_signing_key: str = field(default_factory=lambda: os.getenv("ASSET_SIGNING_KEY", "").strip())
    asset_url_ttl_seconds: int = field(default_factory=lambda: _env_int("ASSET_URL_TTL_SECONDS", "3600"))
    max_request_bytes: int = field(default_factory=lambda: _env_int("MAX_REQUEST_BYTES", "1048576"))
    rate_limit_enabled: bool = field(default_factory=lambda: _env_bool("RATE_LIMIT_ENABLED", "true"))
    rate_limit_per_minute: int = field(default_factory=lambda: _env_int("RATE_LIMIT_PER_MINUTE", "30"))

    db_dir: Path = field(default_factory=lambda: Path(_env_or_default("DB_DIR", "db")))
    img_dir: Path = field(default_factory=lambda: Path(_env_or_default("IMG_DIR", str(PROJECT_ROOT / "data" / "images"))))
    img_base_url: str = field(default_factory=lambda: os.getenv("IMG_BASE_URL", "/images"))
    public_asset_base_url: str = field(default_factory=lambda: os.getenv("PUBLIC_ASSET_BASE_URL", "").rstrip("/"))
    source_metadata_path: Path = field(
        default_factory=lambda: Path(
            _env_or_default("SOURCE_METADATA_PATH", str(PROJECT_ROOT / "data" / "metadata" / "specs.json"))
        )
    )
    static_dir: Path = field(default_factory=lambda: Path(_env_or_default("STATIC_DIR", str(PROJECT_ROOT / "frontend" / "dist"))))

    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080"))
    )
    cors_allow_credentials: bool = field(
        default_factory=lambda: _env_bool("CORS_ALLOW_CREDENTIALS", "false")
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())

    def __post_init__(self) -> None:
        issues: list[str] = []
        if self.llm_timeout_seconds <= 0:
            issues.append("LLM_TIMEOUT_SECONDS 必须大于 0")
        if not 1 <= self.rag_top_k <= 100:
            issues.append("RAG_TOP_K 必须在 1 到 100 之间")
        if self.rag_min_score < 0:
            issues.append("RAG_MIN_SCORE 不能小于 0")
        weights = {
            "RETRIEVAL_DENSE_WEIGHT": self.retrieval_dense_weight,
            "RETRIEVAL_BM25_WEIGHT": self.retrieval_bm25_weight,
            "RETRIEVAL_CLAUSE_BOOST": self.retrieval_clause_boost,
        }
        issues.extend(f"{name} 不能小于 0" for name, value in weights.items() if value < 0)
        if self.retrieval_dense_weight == 0 and self.retrieval_bm25_weight == 0:
            issues.append("RETRIEVAL_DENSE_WEIGHT 与 RETRIEVAL_BM25_WEIGHT 不能同时为 0")
        if self.max_request_bytes <= 0:
            issues.append("MAX_REQUEST_BYTES 必须大于 0")
        if self.rate_limit_enabled and self.rate_limit_per_minute <= 0:
            issues.append("启用限流时 RATE_LIMIT_PER_MINUTE 必须大于 0")
        if not 60 <= self.asset_url_ttl_seconds <= 604800:
            issues.append("ASSET_URL_TTL_SECONDS 必须在 60 到 604800 之间")
        if self.api_auth_enabled:
            if not self.api_keys:
                issues.append("启用 API 鉴权时 API_KEYS 至少需要一个非空 Key")
            placeholders = sorted(key for key in self.api_keys if key.casefold() in PLACEHOLDER_API_KEYS)
            if placeholders:
                issues.append("API_KEYS 不能使用示例占位值")
            if self.openwebui_api_key and self.openwebui_api_key not in self.api_keys:
                issues.append("OPENWEBUI_API_KEY 必须与 API_KEYS 中的一项一致")
            if len(self.asset_signing_key) < 32:
                issues.append("启用 API 鉴权时 ASSET_SIGNING_KEY 至少需要 32 个字符")
        if self.cors_allow_credentials and "*" in self.cors_origins:
            issues.append("CORS_ALLOW_CREDENTIALS=true 时 CORS_ORIGINS 不能包含通配符 *")
        if self.rerank_enabled:
            issues.append("当前版本尚未实现可用 reranker，不能启用 RERANK_ENABLED")
        if self.log_level not in VALID_LOG_LEVELS:
            issues.append(f"LOG_LEVEL 必须是 {', '.join(sorted(VALID_LOG_LEVELS))} 之一")
        if issues:
            raise ConfigurationError(issues)


settings = Settings()


if __name__ == "__main__":
    print("configuration: ok")
