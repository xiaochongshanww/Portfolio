from pathlib import Path

import pytest

from src.evaluation.answer_runner import (
    ANSWER_EVAL_PATH,
    AnswerEvaluationCase,
    evaluate_answer,
    extract_markdown_images,
    load_answer_cases,
    summarize_answer_results,
    validate_trace_citations,
    validate_answer_cases,
)


def _case(**overrides):
    values = {
        "id": "case",
        "query": "办公楼荷载是多少？",
        "type": "direct_value",
        "expected_all": ["2.0"],
        "expected_any_groups": [["办公楼", "办公室"]],
        "forbidden_terms": ["3.5"],
        "expected_citations": ["GB 50009-2012", "5.1.1"],
        "expected_unit_groups": [["kN/m²", "kN/m^2"]],
        "requires_refusal": False,
        "requires_image": True,
    }
    values.update(overrides)
    return AnswerEvaluationCase(**values)


def test_committed_answer_holdout_satisfies_contract():
    cases = load_answer_cases(ANSWER_EVAL_PATH)
    assert len(cases) >= 24
    assert {"direct_value", "formula", "boundary", "false_premise", "no_evidence"} <= {
        case.type for case in cases
    }


def test_answer_contract_rejects_duplicate_and_empty_cases():
    cases = [
        _case(id="same", query=""),
        _case(id="same", type="unknown"),
    ]
    errors = validate_answer_cases(cases)
    assert any("query 不能为空" in error for error in errors)
    assert any("id 重复" in error for error in errors)
    assert any("未知 type" in error for error in errors)


def test_answer_evaluator_accepts_grounded_formatted_answer():
    answer = """【结论】
办公楼取2.0 kN/m²。
【依据】
《建筑结构荷载规范》GB 50009-2012 表5.1.1。
【说明】
适用于一般办公楼。
![第30页](/page-images/GB%2050009-2012_.%E5%BB%BA%E7%AD%91%E7%BB%93%E6%9E%84%E8%8D%B7%E8%BD%BD%E8%A7%84%E8%8C%83.pdf/30)
"""
    result = evaluate_answer(_case(), answer)
    assert result["passed"] is True
    assert result["checks"]["image_routes"] is True


def test_answer_evaluator_reports_missing_fact_and_image():
    answer = "【结论】不确定。【依据】GB 50009-2012。【说明】暂无。"
    result = evaluate_answer(_case(), answer)
    assert result["passed"] is False
    assert "facts_all" in result["failed_checks"]
    assert "image_present" in result["failed_checks"]


def test_refusal_case_requires_explicit_refusal():
    case = _case(
        type="no_evidence",
        expected_all=[],
        expected_any_groups=[],
        forbidden_terms=[],
        expected_citations=[],
        expected_unit_groups=[],
        requires_refusal=True,
        requires_image=False,
    )
    result = evaluate_answer(
        case,
        "【结论】当前材料中未找到明确依据，无法可靠回答。【依据】未检索到足够依据。【说明】请补充页面。",
    )
    assert result["passed"] is True


def test_refusal_case_accepts_equivalent_nonexistent_wording():
    case = _case(
        type="no_evidence",
        expected_all=[],
        expected_any_groups=[],
        forbidden_terms=[],
        expected_citations=[],
        expected_unit_groups=[],
        requires_refusal=True,
        requires_image=False,
    )
    result = evaluate_answer(
        case,
        "【结论】当前材料中未找到该规定，该条文不存在。【依据】无。【说明】请核对编号。",
    )
    assert result["checks"]["refusal"] is True


def test_unit_check_accepts_latex_text_notation():
    answer = "【结论】办公楼取2.0。 【依据】GB 50009-2012 表5.1.1。 【说明】单位为 $\\text{kN/m}^2$。"
    result = evaluate_answer(
        _case(requires_image=False),
        answer,
    )
    assert result["checks"]["units"] is True


def test_formula_check_normalizes_latex_formatting_and_greek_symbols():
    answer = (
        "【结论】$w_{\\mathrm{k}} = \\beta_{\\mathrm{z}} "
        "\\mu_{\\mathrm{s}} \\mu_{\\mathrm{z}} w_{0}$。"
        "【依据】GB 50009-2012 第8.1.1条。"
        "【说明】单位为 $\\text{kN/m}^2$。"
    )
    case = _case(
        type="formula",
        expected_all=[],
        expected_any_groups=[
            ["w_k", "w_{k}"],
            ["β_z", "\\beta_z"],
            ["μ_s", "\\mu_s"],
            ["μ_z", "\\mu_z"],
            ["w_0", "w_{0}"],
        ],
        expected_citations=["GB 50009-2012", "8.1.1"],
        requires_image=False,
    )

    result = evaluate_answer(case, answer)

    assert result["checks"]["facts_any"] is True
    assert result["passed"] is True


def test_markdown_image_parser_rejects_unsupported_route():
    images = extract_markdown_images("![图](https://example.com/fake.png)")
    assert images[0]["url"] == "https://example.com/fake.png"
    result = evaluate_answer(_case(), "【结论】2.0 kN/m² 办公楼。【依据】GB 50009-2012 表5.1.1。【说明】。![图](https://example.com/fake.png)")
    assert result["checks"]["image_routes"] is False


def test_trace_citation_validator_rejects_unsupported_table():
    trace = {
        "sources": [
            {
                "code": "GB 50009-2012",
                "clause_number": "5.1.1",
                "table_id": "5.1.1",
            }
        ]
    }
    valid, unsupported = validate_trace_citations(
        "依据 GB 50009-2012 表5.3.1。",
        trace,
    )
    assert valid is False
    assert unsupported["tables"] == ["5.3.1"]


def test_answer_evaluator_requires_images_to_be_offered_by_trace():
    answer = "【结论】2.0 kN/m² 办公楼。【依据】GB 50009-2012 表5.1.1。【说明】。![图](/page-images/GB%2050009-2012_.%E5%BB%BA%E7%AD%91%E7%BB%93%E6%9E%84%E8%8D%B7%E8%BD%BD%E8%A7%84%E8%8C%83.pdf/30)"
    result = evaluate_answer(
        _case(),
        answer,
        trace={
            "sources": [{"code": "GB 50009-2012", "table_id": "5.1.1"}],
            "image_urls": [],
        },
    )
    assert result["checks"]["citation_grounded"] is True
    assert result["checks"]["image_offered"] is False


def test_load_answer_cases_rejects_invalid_file(tmp_path: Path):
    path = tmp_path / "invalid.jsonl"
    path.write_text('{"id":"x","query":"","type":"direct_value"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="契约校验失败"):
        load_answer_cases(path)


def test_answer_summary_distinguishes_request_failure_from_quality_failure(tmp_path: Path):
    path = tmp_path / "answers.jsonl"
    path.write_text("{}", encoding="utf-8")
    cases = [_case(id="request"), _case(id="quality")]
    results = [
        {
            "id": "request",
            "type": "direct_value",
            "passed": False,
            "checks": {"request": False},
            "failed_checks": ["request"],
            "error": "connection refused",
        },
        {
            "id": "quality",
            "type": "direct_value",
            "passed": False,
            "checks": {"facts_all": False},
            "failed_checks": ["facts_all"],
        },
    ]

    summary = summarize_answer_results(cases, results, path=path)

    assert summary["ok"] is False
    assert "1/2 个请求未完成" in summary["error"]
    assert summary["failure_count"] == 2


def test_answer_summary_keeps_assertion_failure_as_completed(tmp_path: Path):
    path = tmp_path / "answers.jsonl"
    path.write_text("{}", encoding="utf-8")
    cases = [_case(id="quality")]
    results = [
        {
            "id": "quality",
            "type": "direct_value",
            "passed": False,
            "checks": {"facts_all": False},
            "failed_checks": ["facts_all"],
        }
    ]

    summary = summarize_answer_results(cases, results, path=path)

    assert summary["ok"] is True
    assert summary["pass_rate"] == 0
