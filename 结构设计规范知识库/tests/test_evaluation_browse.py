import asyncio
from types import SimpleNamespace

from src.app.api import admin


def test_evaluation_cases_endpoint_filters_and_serializes_regular_cases(monkeypatch):
    monkeypatch.setattr(
        admin,
        "load_cases",
        lambda path: [
            SimpleNamespace(
                id="office-001",
                query="办公楼楼面活荷载取多少？",
                type="table",
                expected_sources=["GB 50009-2012"],
                expected_clause="5.1.1",
                expected_keywords=["活荷载"],
                expected_authority_type="正文表格",
                top1_source_required=True,
                keyword_required=True,
                expected_table_id="表5.1.1",
            ),
            SimpleNamespace(id="formula-001", query="计算公式是什么？", type="formula"),
        ],
    )

    payload = asyncio.run(
        admin.admin_evaluation_cases(
            evaluation_set="regular",
            search="办公楼",
            case_type="table",
            offset=0,
            limit=50,
        )
    )

    assert payload["total"] == 1
    assert payload["type_counts"] == {"table": 1, "formula": 1}
    assert payload["cases"][0]["expected_table_id"] == "表5.1.1"
    assert payload["cases"][0]["expected_keywords"] == ["活荷载"]


def test_evaluation_cases_endpoint_exposes_answer_assertions(monkeypatch):
    monkeypatch.setattr(
        admin,
        "load_answer_cases",
        lambda path: [
            SimpleNamespace(
                id="answer-001",
                query="办公楼活荷载是多少？",
                type="direct_value",
                expected_all=["2.0"],
                expected_any_groups=[["kN/m²", "kN/m2"]],
                forbidden_terms=["无法回答"],
                expected_citations=["GB 50009-2012", "表5.1.1"],
                expected_unit_groups=[["kN/m²"]],
                requires_refusal=False,
                requires_image=True,
            )
        ],
    )

    payload = asyncio.run(
        admin.admin_evaluation_cases(
            evaluation_set="answer",
            search="",
            case_type="",
            offset=0,
            limit=50,
        )
    )

    case = payload["cases"][0]
    assert case["expected_all"] == ["2.0"]
    assert case["expected_citations"] == ["GB 50009-2012", "表5.1.1"]
    assert case["expected_any_groups"] == [["kN/m²", "kN/m2"]]
