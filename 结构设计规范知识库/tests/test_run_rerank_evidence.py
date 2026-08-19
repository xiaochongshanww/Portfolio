import pytest
from scripts.run_rerank_evidence import (
    RerankEvidenceError,
    _configure_rerank_environment,
    _read_api_key,
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
