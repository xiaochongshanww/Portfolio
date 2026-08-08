import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.app.core.config import ConfigurationError, Settings


CONFIG_ENV_NAMES = {
    "ANSWER_EVALUATION_API_BASE",
    "API_AUTH_ENABLED",
    "API_KEYS",
    "ASSET_SIGNING_KEY",
    "ASSET_URL_TTL_SECONDS",
    "CORS_ALLOW_CREDENTIALS",
    "CORS_ORIGINS",
    "DATA_DIR",
    "DB_DIR",
    "IMG_DIR",
    "LLM_TIMEOUT_SECONDS",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "JOB_HEARTBEAT_SECONDS",
    "JOB_STALE_AFTER_SECONDS",
    "MAX_REQUEST_BYTES",
    "OPENWEBUI_API_KEY",
    "RAG_MIN_SCORE",
    "RAG_TOP_K",
    "RATE_LIMIT_ENABLED",
    "RATE_LIMIT_PER_MINUTE",
    "RERANK_ENABLED",
    "RERANK_PROVIDER",
    "RETRIEVAL_BM25_WEIGHT",
    "RETRIEVAL_CLAUSE_BOOST",
    "RETRIEVAL_DENSE_WEIGHT",
    "SOURCE_METADATA_PATH",
    "STATIC_DIR",
    "VERSION_RETENTION_FAILED_DAYS",
    "VERSION_RETENTION_HIGH_WATERMARK_BYTES",
    "VERSION_RETENTION_KEEP_RECENT_PASSED",
    "VERSION_RETENTION_LOW_WATERMARK_BYTES",
    "VERSION_RETENTION_MINIMUM_AGE_HOURS",
    "VERSION_RETENTION_PLAN_TTL_MINUTES",
    "VERSION_RETENTION_SUCCESS_DAYS",
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def settings_from_env(monkeypatch, **values: str) -> Settings:
    for name in CONFIG_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return Settings()


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("RAG_TOP_K", "many", "RAG_TOP_K 必须是整数"),
        ("RAG_MIN_SCORE", "nan", "RAG_MIN_SCORE 必须是有限数字"),
        ("RATE_LIMIT_ENABLED", "sometimes", "RATE_LIMIT_ENABLED 必须是布尔值"),
        ("LOG_FORMAT", "xml", "LOG_FORMAT 必须是 json, text 之一"),
    ],
)
def test_invalid_environment_value_has_actionable_error(monkeypatch, name, value, message):
    with pytest.raises(ConfigurationError, match=message):
        settings_from_env(monkeypatch, **{name: value})


def test_authentication_requires_real_api_key(monkeypatch):
    with pytest.raises(ConfigurationError, match="API_KEYS 至少需要一个非空 Key"):
        settings_from_env(monkeypatch, API_AUTH_ENABLED="true", API_KEYS="")

    with pytest.raises(ConfigurationError, match="API_KEYS 不能使用示例占位值"):
        settings_from_env(monkeypatch, API_AUTH_ENABLED="true", API_KEYS="not-needed")

    with pytest.raises(ConfigurationError, match="ASSET_SIGNING_KEY 至少需要 32 个字符"):
        settings_from_env(monkeypatch, API_AUTH_ENABLED="true", API_KEYS="real-api-key")


def test_openwebui_key_must_match_api_keys_when_present(monkeypatch):
    with pytest.raises(ConfigurationError, match="OPENWEBUI_API_KEY 必须与 API_KEYS"):
        settings_from_env(
            monkeypatch,
            API_AUTH_ENABLED="true",
            API_KEYS="api-key-one",
            ASSET_SIGNING_KEY="s" * 32,
            OPENWEBUI_API_KEY="different-key",
        )


def test_cors_wildcard_cannot_be_combined_with_credentials(monkeypatch):
    with pytest.raises(ConfigurationError, match="CORS_ORIGINS 不能包含通配符"):
        settings_from_env(
            monkeypatch,
            CORS_ORIGINS="*",
            CORS_ALLOW_CREDENTIALS="true",
        )


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"LLM_TIMEOUT_SECONDS": "0"}, "LLM_TIMEOUT_SECONDS 必须大于 0"),
        ({"RAG_TOP_K": "101"}, "RAG_TOP_K 必须在 1 到 100"),
        ({"MAX_REQUEST_BYTES": "0"}, "MAX_REQUEST_BYTES 必须大于 0"),
        ({"JOB_HEARTBEAT_SECONDS": "0"}, "JOB_HEARTBEAT_SECONDS 必须在 1 到 300"),
        (
            {"JOB_HEARTBEAT_SECONDS": "20", "JOB_STALE_AFTER_SECONDS": "30"},
            "JOB_STALE_AFTER_SECONDS 必须至少为 30",
        ),
        ({"ASSET_URL_TTL_SECONDS": "59"}, "ASSET_URL_TTL_SECONDS 必须在 60 到 604800"),
        (
            {"RETRIEVAL_DENSE_WEIGHT": "0", "RETRIEVAL_BM25_WEIGHT": "0"},
            "不能同时为 0",
        ),
        (
            {
                "VERSION_RETENTION_HIGH_WATERMARK_BYTES": "100",
                "VERSION_RETENTION_LOW_WATERMARK_BYTES": "101",
            },
            "LOW_WATERMARK_BYTES 不能大于高水位",
        ),
        ({"VERSION_RETENTION_PLAN_TTL_MINUTES": "0"}, "必须在 1 到 1440"),
    ],
)
def test_invalid_numeric_ranges_are_rejected(monkeypatch, values, message):
    with pytest.raises(ConfigurationError, match=message):
        settings_from_env(monkeypatch, **values)


def test_unimplemented_reranker_cannot_be_silently_enabled(monkeypatch):
    with pytest.raises(ConfigurationError, match="尚未实现可用 reranker"):
        settings_from_env(monkeypatch, RERANK_ENABLED="true", RERANK_PROVIDER="none")


def test_valid_protected_configuration_is_accepted(monkeypatch):
    configured = settings_from_env(
        monkeypatch,
        API_AUTH_ENABLED="true",
        API_KEYS="api-key-one,api-key-two",
        ASSET_SIGNING_KEY="s" * 32,
        OPENWEBUI_API_KEY="api-key-two",
        CORS_ORIGINS="https://console.example.com",
        CORS_ALLOW_CREDENTIALS="true",
    )

    assert configured.api_auth_enabled is True
    assert configured.openwebui_api_key == "api-key-two"


def test_answer_evaluation_target_is_normalized_and_validated(monkeypatch):
    configured = settings_from_env(
        monkeypatch,
        ANSWER_EVALUATION_API_BASE="https://api.example.com/internal/",
    )
    assert configured.answer_evaluation_api_base == "https://api.example.com/internal"

    for value in ("file:///tmp/api", "http://user:secret@example.com", "http:///missing"):
        with pytest.raises(ConfigurationError, match="ANSWER_EVALUATION_API_BASE"):
            settings_from_env(monkeypatch, ANSWER_EVALUATION_API_BASE=value)


def test_runtime_paths_follow_data_dir_with_explicit_overrides(monkeypatch, tmp_path):
    data_dir = tmp_path / "runtime-data"
    configured = settings_from_env(monkeypatch, DATA_DIR=str(data_dir))

    assert configured.data_dir == data_dir.resolve()
    assert configured.img_dir == (data_dir / "images").resolve()
    assert configured.source_metadata_path == (data_dir / "metadata" / "specs.json").resolve()
    assert configured.db_dir == (PROJECT_ROOT / "db").resolve()

    override_images = tmp_path / "separate-images"
    override_metadata = tmp_path / "policies.json"
    configured = settings_from_env(
        monkeypatch,
        DATA_DIR="runtime-data",
        DB_DIR="legacy-db",
        IMG_DIR=str(override_images),
        SOURCE_METADATA_PATH=str(override_metadata),
        STATIC_DIR="custom-static",
    )

    assert configured.data_dir == (PROJECT_ROOT / "runtime-data").resolve()
    assert configured.db_dir == (PROJECT_ROOT / "legacy-db").resolve()
    assert configured.img_dir == override_images.resolve()
    assert configured.source_metadata_path == override_metadata.resolve()
    assert configured.static_dir == (PROJECT_ROOT / "custom-static").resolve()


def run_config_preflight(**values: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for name in CONFIG_ENV_NAMES:
        env.pop(name, None)
    env.update(values)
    return subprocess.run(
        [sys.executable, "-m", "src.app.core.config"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_config_preflight_reports_success():
    result = run_config_preflight()

    assert result.returncode == 0
    assert json.loads(result.stdout) == {"ok": True, "message": "configuration: ok"}
    assert result.stderr == ""


def test_config_preflight_fails_before_application_startup():
    result = run_config_preflight(API_AUTH_ENABLED="true", API_KEYS="")

    assert result.returncode == 2
    payload = json.loads(result.stderr)
    assert payload["ok"] is False
    assert payload["error"] == "configuration_invalid"
    assert "启用 API 鉴权时 API_KEYS 至少需要一个非空 Key" in payload["issues"]
    assert "Traceback" not in result.stderr
    assert result.stderr.isascii()
