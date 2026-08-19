import os
import subprocess
import sys

import pytest
from scripts.run_rerank_quality_evidence import (
    RerankQualityEvidenceError,
    _read_secret,
    _temporary_environment,
)


def test_read_secret_requires_a_non_empty_file(tmp_path):
    empty = tmp_path / "empty.key"
    empty.write_text("\n", encoding="utf-8")

    with pytest.raises(RerankQualityEvidenceError, match="为空"):
        _read_secret(empty, "测试 Key")


def test_temporary_environment_restores_provider_values(monkeypatch):
    monkeypatch.setenv("ZHIPUAI_API_KEY", "previous-key")
    monkeypatch.delenv("RERANK_ENABLED", raising=False)
    monkeypatch.setenv("RERANK_PROVIDER", "previous-provider")
    monkeypatch.delenv("MIMO_API_KEY", raising=False)

    with _temporary_environment(
        {
            "ZHIPUAI_API_KEY": "temporary-key",
            "RERANK_ENABLED": "true",
            "RERANK_PROVIDER": "zhipu",
            "MIMO_API_KEY": "temporary-mimo-key",
        }
    ):
        assert os.environ["ZHIPUAI_API_KEY"] == "temporary-key"
        assert os.environ["RERANK_ENABLED"] == "true"
        assert os.environ["RERANK_PROVIDER"] == "zhipu"
        assert os.environ["MIMO_API_KEY"] == "temporary-mimo-key"

    assert os.environ["ZHIPUAI_API_KEY"] == "previous-key"
    assert "RERANK_ENABLED" not in os.environ
    assert os.environ["RERANK_PROVIDER"] == "previous-provider"
    assert "MIMO_API_KEY" not in os.environ


def test_cli_help_is_utf8_safe():
    completed = subprocess.run(
        [sys.executable, "scripts/run_rerank_quality_evidence.py", "--help"],
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    stdout = completed.stdout.decode("utf-8")
    assert "执行启用精排的完整对照与回答盲测" in stdout
    assert "乱码" not in stdout
