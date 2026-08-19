from scripts.publish_equivalent_quality_evidence import _patch_markdown, _patch_quality_payload


def test_patch_quality_payload_rebinds_identity_without_claiming_new_model_run():
    payload = {
        "verification_run_id": "old",
        "data_version_hash": "old-hash",
        "checks": [
            {
                "name": "knowledge_base",
                "message": "知识库包含 6 份文档、1635 个 chunk",
            },
            {
                "name": "evaluation_run_consistency",
                "details": {"verification_run_id": "old"},
            },
        ],
    }

    patched = _patch_quality_payload(
        payload,
        new_run_id="new",
        candidate_hash="new-hash",
        source_run_id="old-run",
        source_hash="old-hash",
        corpus_digest="corpus-hash",
        manifest={"document_count": 5, "chunk_count": 1635},
    )

    assert patched["verification_run_id"] == "new"
    assert patched["data_version_hash"] == "new-hash"
    assert patched["evidence_mode"] == "inherited_runtime_corpus_equivalence"
    assert patched["inherited_from_verification_run_id"] == "old-run"
    assert patched["checks"][0]["message"] == "知识库包含 5 份文档、1635 个 chunk"
    assert patched["checks"][1]["details"]["verification_run_id"] == "new"
    assert payload["verification_run_id"] == "old"


def test_patch_markdown_explains_evidence_inheritance():
    result = _patch_markdown(
        "验证运行：`old-run`\n数据版本：`old-hash`\n知识库包含 6 份文档",
        source_run_id="old-run",
        new_run_id="new-run",
        source_hash="old-hash",
        candidate_hash="new-hash",
        source_run_note="old-run",
        corpus_digest="corpus-hash",
    )

    assert "`new-run`" in result
    assert "`new-hash`" in result
    assert "5 份文档" in result
    assert "继承等价运行语料" in result
    assert "未重新调用模型" in result
