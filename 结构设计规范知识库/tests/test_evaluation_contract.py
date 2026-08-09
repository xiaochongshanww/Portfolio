from pathlib import Path

import pytest
from src.evaluation.runner import (
    DEFAULT_EVAL_PATH,
    STRUCTURED_EVAL_PATH,
    EvaluationCase,
    load_cases,
    validate_cases,
)


def test_committed_evaluation_sets_satisfy_contract():
    assert len(load_cases(DEFAULT_EVAL_PATH)) >= 100
    assert len(load_cases(STRUCTURED_EVAL_PATH)) >= 12


def test_contract_rejects_duplicate_and_incomplete_cases():
    cases = [
        EvaluationCase(id="same", query="", expected_sources=[]),
        EvaluationCase(id="same", query="有效问题", expected_sources=["GB"], type="unknown"),
    ]

    errors = validate_cases(cases)

    assert any("query 不能为空" in error for error in errors)
    assert any("至少需要一种期望" in error for error in errors)
    assert any("id 重复" in error for error in errors)
    assert any("未知 type" in error for error in errors)


def test_structured_case_requires_table_id():
    errors = validate_cases(
        [
            EvaluationCase(
                id="structured",
                query="查表",
                expected_sources=["GB"],
                type="structured_table",
            )
        ]
    )
    assert any("expected_table_id" in error for error in errors)


def test_load_cases_rejects_invalid_file(tmp_path: Path):
    path = tmp_path / "invalid.jsonl"
    path.write_text(
        '{"id":"x","query":"","expected_sources":[],"type":"general"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="契约校验失败"):
        load_cases(path)
