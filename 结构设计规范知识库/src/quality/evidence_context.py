from __future__ import annotations

import hashlib
import json
import re
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.app.core.config import Settings, settings

EVIDENCE_CONTEXT_SCHEMA_VERSION = 1
VERIFICATION_RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
RUNTIME_CONFIG_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")

_RUNTIME_SOURCE_DIRECTORIES = (
    "src/app/llm",
    "src/app/rag",
    "src/app/rerank",
    "src/app/retrieval",
    "src/evaluation",
)
_RUNTIME_SOURCE_FILES = (
    "src/app/core/config.py",
    "src/quality/evidence_context.py",
    "src/quality/gate.py",
)


def new_verification_run_id() -> str:
    return uuid.uuid4().hex


def validate_verification_run_id(value: str) -> str:
    if not VERIFICATION_RUN_ID_PATTERN.fullmatch(value):
        raise ValueError("verification_run_id 必须是 32 位小写十六进制字符串")
    return value


def validate_runtime_config_hash(value: str) -> str:
    if not RUNTIME_CONFIG_HASH_PATTERN.fullmatch(value):
        raise ValueError("runtime_config_hash 必须是 64 位小写十六进制字符串")
    return value


def _source_hashes(project_root: Path) -> dict[str, str]:
    paths = {project_root / relative for relative in _RUNTIME_SOURCE_FILES}
    for directory in _RUNTIME_SOURCE_DIRECTORIES:
        root = project_root / directory
        if root.is_dir():
            paths.update(root.rglob("*.py"))

    hashes: dict[str, str] = {}
    for path in sorted(paths, key=lambda item: item.as_posix()):
        relative = path.relative_to(project_root).as_posix()
        if not path.is_file():
            hashes[relative] = "missing"
            continue
        normalized = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
        hashes[relative] = hashlib.sha256(normalized).hexdigest()
    return hashes


def runtime_contract_payload(
    config: Settings = settings,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    root = project_root or Path(__file__).resolve().parents[2]
    return {
        "schema_version": EVIDENCE_CONTEXT_SCHEMA_VERSION,
        "settings": {
            "app_version": config.app_version,
            "collection_name": config.collection_name,
            "embedding_model": config.embedding_model,
            "rag_top_k": config.rag_top_k,
            "rag_min_score": config.rag_min_score,
            "retrieval_dense_weight": config.retrieval_dense_weight,
            "retrieval_bm25_weight": config.retrieval_bm25_weight,
            "retrieval_clause_boost": config.retrieval_clause_boost,
            "rerank_enabled": config.rerank_enabled,
            "rerank_provider": config.rerank_provider,
            "rerank_model": config.rerank_model,
            "rerank_candidate_multiplier": config.rerank_candidate_multiplier,
            "rerank_model_weight": config.rerank_model_weight,
            "mimo_base_url": config.mimo_base_url,
            "mimo_model": config.mimo_model,
            "img_base_url": config.img_base_url,
            "public_asset_base_url": config.public_asset_base_url,
            "asset_url_ttl_seconds": config.asset_url_ttl_seconds,
        },
        "source_hashes": _source_hashes(root),
    }


def runtime_config_hash(
    config: Settings = settings,
    *,
    project_root: Path | None = None,
) -> str:
    payload = runtime_contract_payload(config, project_root=project_root)
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@lru_cache(maxsize=1)
def _default_runtime_config_hash() -> str:
    return runtime_config_hash(settings)


def current_evidence_context(config: Settings = settings) -> dict[str, Any]:
    return {
        "evidence_context_schema": EVIDENCE_CONTEXT_SCHEMA_VERSION,
        "runtime_config_hash": (
            _default_runtime_config_hash() if config is settings else runtime_config_hash(config)
        ),
    }
