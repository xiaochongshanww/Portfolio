from src.app.core.config import settings
from src.app.retrieval.hybrid_search import tokenize_chinese


def test_default_settings_are_current_provider():
    assert settings.mimo_model == "mimo-v2.5"
    assert settings.rag_top_k == 12
    assert settings.rag_min_score == 0.65


def test_expected_routes_exist():
    import pytest

    pytest.importorskip("fastapi")
    from src.app.main import app

    paths = set(app.openapi()["paths"])
    assert "/health" in paths
    assert "/v1/models" in paths
    assert "/models" in paths
    assert "/v1/chat/completions" in paths
    assert "/chat/completions" in paths
    assert "/images/{filename}" in paths
    assert "/page-images/{doc}/{page}" in paths
    assert "/integrations/deepseek-harness/ready" in paths
    assert "/integrations/deepseek-harness/search" in paths
    assert "/integrations/deepseek-harness/page" in paths
    assert "/knowledge/documents" in paths
    assert "/evaluation/status" in paths
    assert "/corrections/candidates" in paths
    assert "/corrections/candidates/{doc}" in paths
    assert "/corrections/candidates/{doc}/{candidate_id}" in paths
    assert "/corrections/promote/{doc}" in paths
    assert "/admin/status" in paths
    assert "/admin/jobs/rebuild" in paths
    assert "/admin/jobs/audit" in paths
    assert "/admin/jobs/evaluate" in paths
    assert "/admin/jobs/evaluate-answers" in paths
    assert "/admin/evaluation/cases" in paths
    assert "/admin/corrections/approved/{doc}" in paths
    assert "/admin/manual-structuring" in paths
    assert "/admin/manual-structuring/scan" in paths
    assert "/admin/manual-structuring/ai-suggestions/batch" in paths
    assert "/admin/manual-structuring/{doc}" in paths
    assert "/admin/manual-structuring/{doc}/{item_id}" in paths
    assert "/admin/manual-structuring/{doc}/{item_id}/draft" in paths
    assert "/admin/manual-structuring/{doc}/{item_id}/ai-suggestion" in paths
    assert "/admin/manual-structuring/{doc}/{item_id}/validate" in paths
    assert "/admin/manual-structuring/{doc}/{item_id}/publish" in paths
    assert "/admin/manual-structuring/{doc}/{item_id}/versions" in paths
    assert "/admin/manual-structuring/{doc}/{item_id}/rollback" in paths
    assert "/admin/elements/{doc}/{element_index}" in paths
    assert "/admin/page-image/{doc}/{page}" in paths
    assert "/admin/quality/status" in paths

    admin_source = __import__("pathlib").Path("src/app/api/admin.py").read_text(encoding="utf-8")
    assert "unresolved_failed_job_count" in admin_source
    assert "historical_failed_job_count" in admin_source
    assert "quality_gate" in admin_source


def test_chinese_trigram_tokenizer_keeps_keyword_and_trigrams():
    tokens = tokenize_chinese("重力荷载代表值")
    assert "重力荷载代表值" in tokens
    assert "重力荷" in tokens
    assert "代表值" in tokens
