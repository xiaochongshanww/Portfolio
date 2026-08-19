import os

import pytest
from scripts.run_rerank_evidence import (
    RerankEvidenceError,
    _configure_rerank_environment,
    _read_api_key,
    _temporary_rerank_environment,
)


def test_read_api_key_requires_non_empty_utf8_file(tmp_path):
    empty = tmp_path / "empty.key"
    empty.write_text("  \n", encoding="utf-8")

    with pytest.raises(RerankEvidenceError, match="为空"):
        _read_api_key(empty)


def test_rerank_environment_is_explicit_and_does_not_persist_key():
    key = "temporary-key"
    environ = {}
    _configure_rerank_environment(key, environ)

    assert environ == {
        "ZHIPUAI_API_KEY": key,
        "RERANK_ENABLED": "true",
        "RERANK_PROVIDER": "zhipu",
    }


def test_temporary_rerank_environment_restores_previous_values(monkeypatch):
    monkeypatch.setenv("ZHIPUAI_API_KEY", "previous-key")
    monkeypatch.delenv("RERANK_ENABLED", raising=False)
    monkeypatch.setenv("RERANK_PROVIDER", "previous-provider")

    with _temporary_rerank_environment("temporary-key"):
        assert {
            name: os.environ.get(name)
            for name in ("ZHIPUAI_API_KEY", "RERANK_ENABLED", "RERANK_PROVIDER")
        } == {
            "ZHIPUAI_API_KEY": "temporary-key",
            "RERANK_ENABLED": "true",
            "RERANK_PROVIDER": "zhipu",
        }

    assert os.environ["ZHIPUAI_API_KEY"] == "previous-key"
    assert "RERANK_ENABLED" not in os.environ
    assert os.environ["RERANK_PROVIDER"] == "previous-provider"
