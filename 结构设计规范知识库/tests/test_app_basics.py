from src.app.core.config import settings
from src.app.retrieval.hybrid_search import tokenize_chinese


def test_default_settings_are_current_provider():
    assert settings.mimo_model == "mimo-v2-omni"
    assert settings.rag_top_k == 12
    assert settings.rag_min_score == 0.65


def test_expected_routes_exist():
    import pytest

    pytest.importorskip("fastapi")
    from src.app.main import app

    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/v1/models" in paths
    assert "/models" in paths
    assert "/v1/chat/completions" in paths
    assert "/chat/completions" in paths
    assert "/images/{filename:path}" in paths
    assert "/knowledge/documents" in paths
    assert "/evaluation/status" in paths


def test_chinese_trigram_tokenizer_keeps_keyword_and_trigrams():
    tokens = tokenize_chinese("重力荷载代表值")
    assert "重力荷载代表值" in tokens
    assert "重力荷" in tokens
    assert "代表值" in tokens
