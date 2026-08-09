from dataclasses import replace

import pytest
from src.app.core.config import settings
from src.quality.evidence_context import (
    current_evidence_context,
    new_verification_run_id,
    runtime_config_hash,
    runtime_contract_payload,
    validate_runtime_config_hash,
    validate_verification_run_id,
)


def test_evidence_context_identifiers_require_canonical_lowercase_format():
    run_id = new_verification_run_id()
    context = current_evidence_context()

    assert validate_verification_run_id(run_id) == run_id
    assert (
        validate_runtime_config_hash(context["runtime_config_hash"])
        == context["runtime_config_hash"]
    )
    with pytest.raises(ValueError, match="32 位"):
        validate_verification_run_id("not-a-run")
    with pytest.raises(ValueError, match="32 位"):
        validate_verification_run_id("A" * 32)
    with pytest.raises(ValueError, match="32 位"):
        validate_verification_run_id(" " + run_id)
    with pytest.raises(ValueError, match="64 位"):
        validate_runtime_config_hash("not-a-hash")
    with pytest.raises(ValueError, match="64 位"):
        validate_runtime_config_hash("B" * 64)
    with pytest.raises(ValueError, match="64 位"):
        validate_runtime_config_hash(context["runtime_config_hash"] + " ")


def test_runtime_contract_excludes_secrets_and_changes_with_retrieval_config(tmp_path):
    configured = replace(
        settings,
        zhipuai_api_key="zhipu-secret",
        mimo_api_key="mimo-secret",
        api_keys=["api-secret"],
        asset_signing_key="asset-secret",
    )
    payload = runtime_contract_payload(configured, project_root=tmp_path)
    serialized = repr(payload)

    assert "zhipu-secret" not in serialized
    assert "mimo-secret" not in serialized
    assert "api-secret" not in serialized
    assert "asset-secret" not in serialized
    baseline = runtime_config_hash(configured, project_root=tmp_path)
    changed = runtime_config_hash(
        replace(configured, retrieval_bm25_weight=configured.retrieval_bm25_weight + 0.01),
        project_root=tmp_path,
    )
    assert baseline != changed


def test_runtime_contract_changes_when_controlled_source_changes(tmp_path):
    source = tmp_path / "src" / "app" / "rag" / "prompt.py"
    source.parent.mkdir(parents=True)
    source.write_text("PROMPT = 'v1'\n", encoding="utf-8")
    before = runtime_config_hash(settings, project_root=tmp_path)

    source.write_text("PROMPT = 'v2'\n", encoding="utf-8")
    after = runtime_config_hash(settings, project_root=tmp_path)

    assert before != after
