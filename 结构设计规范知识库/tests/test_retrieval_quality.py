from src.app.rag.context import format_result_context
from src.app.rerank.noop import NoopReranker
from src.app.retrieval.models import RetrievalCandidate, RetrievalResult
from src.app.retrieval.query import analyze_query
from src.evaluation.runner import EvaluationCase, summarize_results


def test_query_analysis_extracts_clause_code_and_alias():
    info = analyze_query("GB50011 第 8.2.1 条，抗规怎么要求？")
    assert "8.2.1" in info.clause_numbers
    assert "GB 50011" in info.spec_codes
    assert "抗规" in info.spec_aliases
    assert "建筑抗震设计规范" in info.spec_names


def test_retrieval_candidate_combines_reasons_and_sources():
    candidate = RetrievalCandidate(doc_id="1", text="正文", meta={"source": "a.pdf"})
    candidate.score += 1
    candidate.add_source("dense")
    candidate.add_source("bm25")
    candidate.add_reason("dense semantic match")
    candidate.add_reason("bm25 keyword match")
    result = candidate.to_result()
    assert result.source == "bm25+dense"
    assert "dense semantic match" in result.reason
    assert "bm25 keyword match" in result.reason


def test_noop_reranker_preserves_order():
    results = [
        RetrievalResult("a", "A", {}, 2.0, "dense", "dense"),
        RetrievalResult("b", "B", {}, 1.0, "bm25", "bm25"),
    ]
    assert NoopReranker().rerank("query", results) == results


def test_rag_context_includes_source_header():
    result = RetrievalResult(
        doc_id="1",
        text="条文正文",
        meta={
            "name": "建筑抗震设计规范",
            "code": "GB 50011-2010",
            "version": "2016年版",
            "clause_number": "8.2.1",
            "pages": "10",
        },
        score=5.0,
        source="clause",
        reason="clause exact match 8.2.1",
        clause_match=True,
    )
    context = format_result_context(result)
    assert "来源规范：建筑抗震设计规范" in context
    assert "规范编号：GB 50011-2010" in context
    assert "条文号：8.2.1" in context
    assert "命中原因：clause exact match 8.2.1" in context


def test_evaluation_summary_detects_hits():
    case = EvaluationCase(
        id="case-1",
        query="抗震规范第 8.2.1 条",
        expected_sources=["建筑抗震设计规范"],
        expected_clause="8.2.1",
        expected_keywords=["构件"],
    )
    result = RetrievalResult(
        doc_id="1",
        text="构件要求",
        meta={"name": "建筑抗震设计规范", "clause_number": "8.2.1"},
        score=5.0,
        source="clause",
        reason="clause exact match",
    )
    summary = summarize_results([case], {"case-1": [result]})
    assert summary["source_hit_rate"] == 1
    assert summary["clause_hit_rate"] == 1
    assert summary["keyword_hit_rate"] == 1
