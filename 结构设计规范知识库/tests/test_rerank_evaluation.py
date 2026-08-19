import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from src.app.rerank.fusion import fuse_rankings
from src.app.retrieval.models import RetrievalResult
from src.evaluation.rerank_comparison import (
    render_rerank_comparison_markdown,
    run_rerank_comparison,
)
from src.evaluation.runner import EvaluationCase, summarize_results


def retrieval_result(
    doc_id: str,
    *,
    source: str,
    text: str,
    section_type: str = "body",
    score: float = 1,
) -> RetrievalResult:
    return RetrievalResult(
        doc_id=doc_id,
        text=text,
        meta={"source_file": source, "section_type": section_type},
        score=score,
        source="bm25",
        reason="baseline",
    )


def test_evaluation_reports_first_qualified_rank_and_mrr():
    cases = [
        EvaluationCase("one", "q1", ["spec-a"], expected_keywords=["目标"]),
        EvaluationCase("two", "q2", ["spec-b"], expected_keywords=["目标"]),
        EvaluationCase("miss", "q3", ["spec-c"], expected_keywords=["目标"]),
    ]
    results = {
        "one": [retrieval_result("a", source="spec-a", text="目标")],
        "two": [
            retrieval_result("x", source="other", text="目标"),
            retrieval_result("b", source="spec-b", text="目标"),
        ],
        "miss": [retrieval_result("c", source="other", text="目标")],
    }

    summary = summarize_results(cases, results)

    assert summary["qualified_case_count"] == 3
    assert summary["qualified_hit_rate"] == pytest.approx(2 / 3)
    assert summary["qualified_top1_hit_rate"] == pytest.approx(1 / 3)
    assert summary["qualified_hit_at_3"] == pytest.approx(2 / 3)
    assert summary["qualified_mrr"] == pytest.approx(0.5)
    assert [item["first_qualified_rank"] for item in summary["ranking_cases"]] == [1, 2, None]


def test_rerank_comparison_uses_one_candidate_pool_and_renders_report(tmp_path: Path, monkeypatch):
    path = tmp_path / "eval.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "case-1",
                "query": "目标问题",
                "expected_sources": ["right-spec"],
                "expected_keywords": ["目标"],
                "type": "general",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    class FakeState:
        ready = True
        config = SimpleNamespace(rerank_candidate_multiplier=3, rerank_model="test-model")

        def __init__(self):
            self.calls = 0

        def retrieve_candidates(self, query, candidate_limit):
            self.calls += 1
            assert query == "目标问题"
            assert candidate_limit == 6
            return query, [
                retrieval_result("wrong", source="other-spec", text="目标", score=2),
                retrieval_result("right", source="right-spec", text="目标", score=1),
            ]

    class ImprovingReranker:
        name = "fake"

        def rerank(self, query, results, *, top_n=None):
            del query
            return fuse_rankings(results, {1: 1.0, 0: 0.0}, model_weight=1, top_n=top_n)

    state = FakeState()
    monkeypatch.setattr(
        "src.evaluation.rerank_comparison.read_active_manifest",
        lambda: {"data_version_hash": "data-hash"},
    )

    report = run_rerank_comparison(path, top_k=2, state=state, reranker=ImprovingReranker())
    markdown = render_rerank_comparison_markdown(report)

    assert report["ok"] is True
    assert state.calls == 1
    assert report["baseline"]["qualified_top1_hit_rate"] == 0
    assert report["reranked"]["qualified_top1_hit_rate"] == 1
    assert report["metric_deltas"]["qualified_mrr"] == pytest.approx(0.5)
    assert report["change_counts"] == {"improved": 1, "unchanged": 0, "regressed": 0}
    assert report["reranked_case_count"] == 1
    assert report["fallback_case_count"] == 0
    assert "候选精排对照评估" in markdown
    assert "`qualified_mrr`" in markdown
    assert "data-hash" in markdown


def test_rerank_comparison_rejects_noop_provider(tmp_path: Path):
    path = tmp_path / "eval.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "case-1",
                "query": "query",
                "expected_sources": ["source"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    class Noop:
        name = "none"

    state = SimpleNamespace(
        ready=True,
        config=SimpleNamespace(rerank_candidate_multiplier=3, rerank_model="none"),
    )
    report = run_rerank_comparison(path, state=state, reranker=Noop())

    assert report["ok"] is False
    assert "未启用" in report["error"]


def test_rerank_comparison_fails_closed_when_provider_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    path = tmp_path / "eval.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(
                {
                    "id": f"case-{index}",
                    "query": "query",
                    "expected_sources": ["source"],
                }
            )
            for index in (1, 2)
        )
        + "\n",
        encoding="utf-8",
    )

    class FailingReranker:
        name = "zhipu"

        def rerank(self, query, results, *, top_n=None):
            del query
            return results[:top_n]

    state = SimpleNamespace(
        ready=True,
        config=SimpleNamespace(rerank_candidate_multiplier=3, rerank_model="rerank"),
    )
    state.calls = 0

    def retrieve_candidates(query, candidate_limit):
        state.calls += 1
        return (
            query,
            [
                retrieval_result("wrong", source="other", text="目标", score=2),
                retrieval_result("right", source="source", text="目标", score=1),
            ][:candidate_limit],
        )

    state.retrieve_candidates = retrieve_candidates
    monkeypatch.setattr(
        "src.evaluation.rerank_comparison.read_active_manifest",
        lambda: {"data_version_hash": "data-hash"},
    )
    report = run_rerank_comparison(
        path,
        state=state,
        reranker=FailingReranker(),
    )

    assert report["ok"] is False
    assert report["comparison_complete"] is False
    assert report["reranked_case_count"] == 0
    assert report["fallback_case_count"] == 1
    assert report["processed_case_count"] == 1
    assert state.calls == 1
    assert "不能将基线结果解释为真实精排结果" in report["error"]


def test_rerank_comparison_fails_closed_when_candidate_pool_is_empty(tmp_path, monkeypatch):
    path = tmp_path / "eval.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "case-empty",
                "query": "query",
                "expected_sources": ["source"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    state = SimpleNamespace(
        ready=True,
        config=SimpleNamespace(rerank_candidate_multiplier=3, rerank_model="rerank"),
    )
    state.retrieve_candidates = lambda query, candidate_limit: (query, [])

    class EmptyPoolReranker:
        name = "fake"

        def rerank(self, query, results, *, top_n=None):
            del query, results, top_n
            return []

    monkeypatch.setattr(
        "src.evaluation.rerank_comparison.read_active_manifest",
        lambda: {"data_version_hash": "data-hash"},
    )

    report = run_rerank_comparison(
        path,
        state=state,
        reranker=EmptyPoolReranker(),
    )

    assert report["ok"] is False
    assert report["comparison_complete"] is False
    assert report["reranked_case_count"] == 0
    assert report["fallback_case_count"] == 1
    assert "不能将基线结果解释为真实精排结果" in report["error"]
