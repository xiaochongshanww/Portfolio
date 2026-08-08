from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import validate_configuration_example


def test_repository_configuration_example_is_valid():
    result = validate_configuration_example.validate_configuration_example()

    assert result["ok"] is True
    assert result["key_count"] > 30
    assert result["sensitive_key_count"] >= 6
    assert result["configuration_preflight"] == "passed"


def test_configuration_example_rejects_duplicate_keys_without_values_in_error():
    content = "RAG_TOP_K=12\nrag_top_k=99\n"

    with pytest.raises(
        validate_configuration_example.ConfigurationExampleError,
        match="变量 rag_top_k 与 RAG_TOP_K.*重复",
    ) as error:
        validate_configuration_example._parse_stream(
            io.StringIO(content),
            path=Path("duplicate.env"),
        )

    assert "12" not in str(error.value)
    assert "99" not in str(error.value)


def test_configuration_example_rejects_nonportable_variable_name():
    with pytest.raises(
        validate_configuration_example.ConfigurationExampleError,
        match="不符合环境变量格式",
    ):
        validate_configuration_example._parse_stream(
            io.StringIO("INVALID.NAME=value\n"),
            path=Path("invalid-name.env"),
        )


def test_configuration_example_rejects_invalid_dotenv_syntax():
    with pytest.raises(
        validate_configuration_example.ConfigurationExampleError,
        match="不是有效的 dotenv 语法",
    ):
        validate_configuration_example._parse_stream(
            io.StringIO("BROKEN='unterminated\n"),
            path=Path("broken.env"),
        )


@pytest.mark.parametrize(
    "name",
    [
        "ZHIPUAI_API_KEY",
        "API_KEYS",
        "ASSET_SIGNING_SECRET",
        "SERVICE_TOKEN",
        "PASSWORD",
    ],
)
def test_configuration_example_rejects_nonempty_sensitive_values(name: str):
    secret = "must-not-leak"

    with pytest.raises(
        validate_configuration_example.ConfigurationExampleError,
        match=f"敏感变量 {name}.*必须留空",
    ) as error:
        validate_configuration_example._parse_stream(
            io.StringIO(f"{name}={secret}\n"),
            path=Path("secret.env"),
        )

    assert secret not in str(error.value)


def test_application_preflight_isolated_from_invalid_host_environment(
    monkeypatch,
    tmp_path: Path,
):
    path = tmp_path / "valid.env"
    path.write_text("RAG_TOP_K=12\nAPI_AUTH_ENABLED=false\n", encoding="utf-8")
    monkeypatch.setenv("RAG_TOP_K", "0")
    monkeypatch.setenv("RERANK_ENABLED", "true")

    example = validate_configuration_example.parse_configuration_example(path)
    validate_configuration_example.validate_application_configuration(example)


def test_application_preflight_rejects_invalid_example_without_echoing_value(
    tmp_path: Path,
):
    path = tmp_path / "invalid.env"
    path.write_text("RAG_TOP_K=999\n", encoding="utf-8")
    example = validate_configuration_example.parse_configuration_example(path)

    with pytest.raises(
        validate_configuration_example.ConfigurationExampleError,
        match="应用配置预检失败",
    ) as error:
        validate_configuration_example.validate_application_configuration(example)

    assert "999" not in str(error.value)


def test_configuration_contract_rejects_unknown_typo_without_value():
    example = validate_configuration_example.ConfigurationExample(
        path=Path("typo.env"),
        values={
            **{name: "" for name in validate_configuration_example.EXPECTED_EXAMPLE_KEYS},
            "RAG_TOPK": "sensitive-value",
        },
        sensitive_key_count=0,
    )

    with pytest.raises(
        validate_configuration_example.ConfigurationExampleError,
        match="包含未知变量：RAG_TOPK",
    ) as error:
        validate_configuration_example.validate_example_key_contract(example)

    assert "sensitive-value" not in str(error.value)


def test_configuration_contract_rejects_missing_expected_key():
    values = {name: "" for name in validate_configuration_example.EXPECTED_EXAMPLE_KEYS}
    values.pop("RAG_TOP_K")
    example = validate_configuration_example.ConfigurationExample(
        path=Path("missing.env"),
        values=values,
        sensitive_key_count=0,
    )

    with pytest.raises(
        validate_configuration_example.ConfigurationExampleError,
        match="缺少约定变量：RAG_TOP_K",
    ):
        validate_configuration_example.validate_example_key_contract(example)


def test_configuration_example_cli_returns_safe_json():
    completed = subprocess.run(
        [sys.executable, "scripts/validate_configuration_example.py"],
        cwd=validate_configuration_example.PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert set(payload) == {
        "ok",
        "path",
        "key_count",
        "sensitive_key_count",
        "configuration_preflight",
    }
    for secret_name in (
        "ZHIPUAI_API_KEY",
        "MIMO_API_KEY",
        "API_KEYS",
        "ASSET_SIGNING_KEY",
    ):
        assert secret_name not in completed.stdout
