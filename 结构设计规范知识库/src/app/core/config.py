import json
import os
import sys
from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path

from src.app.core.urls import normalize_http_base_url
from src.pipeline.paths import configured_project_path

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv() -> bool:
        return False


load_dotenv()


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}
PLACEHOLDER_API_KEYS = {"change-me", "changeme", "not-needed", "your-api-key"}
VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
VALID_LOG_FORMATS = {"json", "text"}
VALID_RERANK_PROVIDERS = {"none", "zhipu"}
VALID_EMBEDDING_DIMENSIONS = {256, 512, 1024, 2048}


class ConfigurationError(ValueError):
    def __init__(self, issues: list[str] | str):
        self.issues = (issues,) if isinstance(issues, str) else tuple(issues)
        super().__init__("配置校验失败：\n- " + "\n- ".join(self.issues))


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_bool(name: str, default: str = "false") -> bool:
    value = os.getenv(name, default).strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise ConfigurationError(
        f"{name} 必须是布尔值（true/false、1/0、yes/no 或 on/off），当前为 {value!r}"
    )


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


def _env_http_base_url(name: str, default: str) -> str:
    try:
        return normalize_http_base_url(os.getenv(name, default), field_name=name)
    except ValueError as exc:
        raise ConfigurationError(str(exc)) from exc


@dataclass(frozen=True)
class Settings:
    app_title: str = "结构设计规范知识库 RAG API (多模态)"
    app_version: str = "3.1.0"
    collection_name: str = "design_specs"

    zhipuai_api_key: str = field(default_factory=lambda: os.getenv("ZHIPUAI_API_KEY", ""))
    mimo_api_key: str = field(default_factory=lambda: os.getenv("MIMO_API_KEY", ""))
    mimo_base_url: str = field(
        default_factory=lambda: os.getenv("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1")
    )
    mimo_model: str = field(default_factory=lambda: os.getenv("MIMO_MODEL", "mimo-v2.5"))
    llm_timeout_seconds: int = field(default_factory=lambda: _env_int("LLM_TIMEOUT_SECONDS", "180"))

    rag_top_k: int = field(default_factory=lambda: _env_int("RAG_TOP_K", "12"))
    rag_min_score: float = field(default_factory=lambda: _env_float("RAG_MIN_SCORE", "0.65"))
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "embedding-2")
    )
    embedding_dimensions: int = field(
        default_factory=lambda: _env_int("EMBEDDING_DIMENSIONS", "1024")
    )
    retrieval_dense_weight: float = field(
        default_factory=lambda: _env_float("RETRIEVAL_DENSE_WEIGHT", "1.0")
    )
    retrieval_bm25_weight: float = field(
        default_factory=lambda: _env_float("RETRIEVAL_BM25_WEIGHT", "0.18")
    )
    retrieval_clause_boost: float = field(
        default_factory=lambda: _env_float("RETRIEVAL_CLAUSE_BOOST", "5.0")
    )
    rerank_enabled: bool = field(default_factory=lambda: _env_bool("RERANK_ENABLED", "false"))
    rerank_provider: str = field(
        default_factory=lambda: os.getenv("RERANK_PROVIDER", "none").strip().lower()
    )
    rerank_base_url: str = field(
        default_factory=lambda: _env_http_base_url(
            "RERANK_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"
        )
    )
    rerank_model: str = field(default_factory=lambda: os.getenv("RERANK_MODEL", "rerank").strip())
    rerank_timeout_seconds: int = field(
        default_factory=lambda: _env_int("RERANK_TIMEOUT_SECONDS", "10")
    )
    rerank_candidate_multiplier: int = field(
        default_factory=lambda: _env_int("RERANK_CANDIDATE_MULTIPLIER", "3")
    )
    rerank_model_weight: float = field(
        default_factory=lambda: _env_float("RERANK_MODEL_WEIGHT", "0.35")
    )
    api_auth_enabled: bool = field(default_factory=lambda: _env_bool("API_AUTH_ENABLED", "false"))
    api_keys: list[str] = field(default_factory=lambda: _split_csv(os.getenv("API_KEYS", "")))
    openwebui_api_key: str = field(
        default_factory=lambda: os.getenv("OPENWEBUI_API_KEY", "").strip()
    )
    asset_signing_key: str = field(
        default_factory=lambda: os.getenv("ASSET_SIGNING_KEY", "").strip()
    )
    asset_url_ttl_seconds: int = field(
        default_factory=lambda: _env_int("ASSET_URL_TTL_SECONDS", "3600")
    )
    max_request_bytes: int = field(default_factory=lambda: _env_int("MAX_REQUEST_BYTES", "1048576"))
    rate_limit_enabled: bool = field(
        default_factory=lambda: _env_bool("RATE_LIMIT_ENABLED", "true")
    )
    rate_limit_per_minute: int = field(
        default_factory=lambda: _env_int("RATE_LIMIT_PER_MINUTE", "30")
    )
    job_heartbeat_seconds: int = field(
        default_factory=lambda: _env_int("JOB_HEARTBEAT_SECONDS", "15")
    )
    job_stale_after_seconds: int = field(
        default_factory=lambda: _env_int("JOB_STALE_AFTER_SECONDS", "7200")
    )
    answer_evaluation_api_base: str = field(
        default_factory=lambda: _env_http_base_url(
            "ANSWER_EVALUATION_API_BASE",
            "http://127.0.0.1:8000",
        )
    )
    version_retention_keep_recent_passed: int = field(
        default_factory=lambda: _env_int("VERSION_RETENTION_KEEP_RECENT_PASSED", "2")
    )
    version_retention_success_days: int = field(
        default_factory=lambda: _env_int("VERSION_RETENTION_SUCCESS_DAYS", "30")
    )
    version_retention_failed_days: int = field(
        default_factory=lambda: _env_int("VERSION_RETENTION_FAILED_DAYS", "7")
    )
    version_retention_minimum_age_hours: int = field(
        default_factory=lambda: _env_int("VERSION_RETENTION_MINIMUM_AGE_HOURS", "24")
    )
    version_retention_high_watermark_bytes: int = field(
        default_factory=lambda: _env_int(
            "VERSION_RETENTION_HIGH_WATERMARK_BYTES", str(20 * 1024**3)
        )
    )
    version_retention_low_watermark_bytes: int = field(
        default_factory=lambda: _env_int("VERSION_RETENTION_LOW_WATERMARK_BYTES", str(16 * 1024**3))
    )
    version_retention_plan_ttl_minutes: int = field(
        default_factory=lambda: _env_int("VERSION_RETENTION_PLAN_TTL_MINUTES", "15")
    )

    data_dir: Path = field(default_factory=lambda: configured_project_path("DATA_DIR", "data"))
    db_dir: Path = field(default_factory=lambda: configured_project_path("DB_DIR", "db"))
    img_dir: Path = field(
        default_factory=lambda: configured_project_path(
            "IMG_DIR",
            configured_project_path("DATA_DIR", "data") / "images",
        )
    )
    img_base_url: str = field(default_factory=lambda: os.getenv("IMG_BASE_URL", "/images"))
    public_asset_base_url: str = field(
        default_factory=lambda: os.getenv("PUBLIC_ASSET_BASE_URL", "").rstrip("/")
    )
    source_metadata_path: Path = field(
        default_factory=lambda: configured_project_path(
            "SOURCE_METADATA_PATH",
            configured_project_path("DATA_DIR", "data") / "metadata" / "specs.json",
        )
    )
    static_dir: Path = field(
        default_factory=lambda: configured_project_path("STATIC_DIR", "frontend/dist")
    )

    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")
        )
    )
    cors_allow_credentials: bool = field(
        default_factory=lambda: _env_bool("CORS_ALLOW_CREDENTIALS", "false")
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())
    log_format: str = field(default_factory=lambda: os.getenv("LOG_FORMAT", "json").strip().lower())

    def __post_init__(self) -> None:
        issues: list[str] = []
        if self.llm_timeout_seconds <= 0:
            issues.append("LLM_TIMEOUT_SECONDS 必须大于 0")
        if not 1 <= self.rag_top_k <= 100:
            issues.append("RAG_TOP_K 必须在 1 到 100 之间")
        if self.rag_min_score < 0:
            issues.append("RAG_MIN_SCORE 不能小于 0")
        if self.embedding_dimensions not in VALID_EMBEDDING_DIMENSIONS:
            issues.append("EMBEDDING_DIMENSIONS 必须是 256、512、1024 或 2048 之一")
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
        if not 1 <= self.job_heartbeat_seconds <= 300:
            issues.append("JOB_HEARTBEAT_SECONDS 必须在 1 到 300 之间")
        if self.job_stale_after_seconds < max(30, self.job_heartbeat_seconds * 2):
            issues.append("JOB_STALE_AFTER_SECONDS 必须至少为 30 且不小于心跳间隔的 2 倍")
        retention_non_negative = {
            "VERSION_RETENTION_KEEP_RECENT_PASSED": self.version_retention_keep_recent_passed,
            "VERSION_RETENTION_SUCCESS_DAYS": self.version_retention_success_days,
            "VERSION_RETENTION_FAILED_DAYS": self.version_retention_failed_days,
            "VERSION_RETENTION_MINIMUM_AGE_HOURS": self.version_retention_minimum_age_hours,
            "VERSION_RETENTION_LOW_WATERMARK_BYTES": self.version_retention_low_watermark_bytes,
        }
        issues.extend(
            f"{name} 不能小于 0" for name, value in retention_non_negative.items() if value < 0
        )
        if self.version_retention_high_watermark_bytes <= 0:
            issues.append("VERSION_RETENTION_HIGH_WATERMARK_BYTES 必须大于 0")
        if self.version_retention_low_watermark_bytes > self.version_retention_high_watermark_bytes:
            issues.append("VERSION_RETENTION_LOW_WATERMARK_BYTES 不能大于高水位")
        if not 1 <= self.version_retention_plan_ttl_minutes <= 1440:
            issues.append("VERSION_RETENTION_PLAN_TTL_MINUTES 必须在 1 到 1440 之间")
        if not 60 <= self.asset_url_ttl_seconds <= 604800:
            issues.append("ASSET_URL_TTL_SECONDS 必须在 60 到 604800 之间")
        if self.api_auth_enabled:
            if not self.api_keys:
                issues.append("启用 API 鉴权时 API_KEYS 至少需要一个非空 Key")
            placeholders = sorted(
                key for key in self.api_keys if key.casefold() in PLACEHOLDER_API_KEYS
            )
            if placeholders:
                issues.append("API_KEYS 不能使用示例占位值")
            if self.openwebui_api_key and self.openwebui_api_key not in self.api_keys:
                issues.append("OPENWEBUI_API_KEY 必须与 API_KEYS 中的一项一致")
            if len(self.asset_signing_key) < 32:
                issues.append("启用 API 鉴权时 ASSET_SIGNING_KEY 至少需要 32 个字符")
        if self.cors_allow_credentials and "*" in self.cors_origins:
            issues.append("CORS_ALLOW_CREDENTIALS=true 时 CORS_ORIGINS 不能包含通配符 *")
        if self.rerank_provider not in VALID_RERANK_PROVIDERS:
            issues.append(
                f"RERANK_PROVIDER 必须是 {', '.join(sorted(VALID_RERANK_PROVIDERS))} 之一"
            )
        if not 1 <= self.rerank_timeout_seconds <= 180:
            issues.append("RERANK_TIMEOUT_SECONDS 必须在 1 到 180 之间")
        if not 1 <= self.rerank_candidate_multiplier <= 10:
            issues.append("RERANK_CANDIDATE_MULTIPLIER 必须在 1 到 10 之间")
        if not 0 <= self.rerank_model_weight <= 1:
            issues.append("RERANK_MODEL_WEIGHT 必须在 0 到 1 之间")
        if self.rerank_enabled:
            if self.rerank_provider == "none":
                issues.append("启用 RERANK_ENABLED 时 RERANK_PROVIDER 不能为 none")
            if not self.rerank_model:
                issues.append("启用 RERANK_ENABLED 时 RERANK_MODEL 不能为空")
            if not self.zhipuai_api_key:
                issues.append("启用智谱 reranker 时 ZHIPUAI_API_KEY 不能为空")
            elif self.zhipuai_api_key.casefold() in PLACEHOLDER_API_KEYS:
                issues.append("启用智谱 reranker 时 ZHIPUAI_API_KEY 不能使用示例占位值")
        if self.log_level not in VALID_LOG_LEVELS:
            issues.append(f"LOG_LEVEL 必须是 {', '.join(sorted(VALID_LOG_LEVELS))} 之一")
        if self.log_format not in VALID_LOG_FORMATS:
            issues.append(f"LOG_FORMAT 必须是 {', '.join(sorted(VALID_LOG_FORMATS))} 之一")
        if issues:
            raise ConfigurationError(issues)


try:
    settings = Settings()
except ConfigurationError as exc:
    if __name__ != "__main__":
        raise
    print(
        json.dumps(
            {
                "ok": False,
                "error": "configuration_invalid",
                "issues": list(exc.issues),
            },
            ensure_ascii=True,
        ),
        file=sys.stderr,
    )
    raise SystemExit(2) from None


if __name__ == "__main__":
    print(json.dumps({"ok": True, "message": "configuration: ok"}, ensure_ascii=True))
