from __future__ import annotations

import json
import logging
from typing import Any

import httpx
import pytest
from src.app.core.config import Settings
from src.app.core.metrics import metrics
from src.app.rerank.errors import RerankerError
from src.app.rerank.fusion import fuse_rankings
from src.app.rerank.safe import FailOpenReranker
from src.app.rerank.zhipu import MAX_TEXT_CHARS, ZhipuReranker, _candidate_document
from src.app.retrieval.hybrid_search import RetrievalState
from src.app.retrieval.models import RetrievalCandidate, RetrievalResult


def result(index: int, *, text: str | None = None) -> RetrievalResult:
    return RetrievalResult(
        doc_id=f"doc-{index}",
        text=text or f"候选正文 {index}",
        meta={
            "name": "建筑结构荷载规范",
            "code": "GB 50009-2012",
            "title": f"表 {index}",
            "section_type": "body_table",
        },
        score=float(10 - index),
        source="bm25",
        reason="baseline",
    )


def client_for(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def reranker_with(client: httpx.Client, *, weight: float = 1.0) -> ZhipuReranker:
    return ZhipuReranker(
        api_key="secret-test-key",
        base_url="https://example.test/api/paas/v4",
        model="rerank",
        timeout_seconds=3,
        model_weight=weight,
        client=client,
    )


def test_zhipu_reranker_sends_bounded_contract_and_fuses_results():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["Authorization"]
        captured["path"] = request.url.path
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "results": [
                    {"index": 2, "relevance_score": 0.95},
                    {"index": 0, "relevance_score": 0.5},
                    {"index": 1, "relevance_score": 0.1},
                ]
            },
        )

    inputs = [result(0, text="长文本" * 3000), result(1), result(2)]
    outputs = reranker_with(client_for(handler)).rerank("问题" * 3000, inputs, top_n=2)

    assert [item.doc_id for item in outputs] == ["doc-2", "doc-0"]
    assert outputs[0].score == inputs[2].score
    assert outputs[0].meta["_retrieval_rank"] == 3
    assert outputs[0].meta["_rerank_rank"] == 1
    assert outputs[0].meta["_rerank_score"] == 0.95
    assert "rerank" in outputs[0].source
    assert captured["authorization"] == "Bearer secret-test-key"
    assert captured["path"] == "/api/paas/v4/rerank"
    assert captured["payload"]["top_n"] == 3
    assert captured["payload"]["return_documents"] is False
    assert len(captured["payload"]["query"]) == MAX_TEXT_CHARS
    assert all(len(document) <= MAX_TEXT_CHARS for document in captured["payload"]["documents"])


def test_rank_fusion_can_preserve_baseline_and_append_partial_response():
    inputs = [result(0), result(1), result(2)]

    baseline = fuse_rankings(inputs, {2: 1.0, 0: 0.5, 1: 0.1}, model_weight=0, top_n=3)
    assert [item.doc_id for item in baseline] == ["doc-0", "doc-1", "doc-2"]

    partial = fuse_rankings(inputs, {1: 0.9}, model_weight=1, top_n=3)
    assert [item.doc_id for item in partial] == ["doc-1", "doc-0", "doc-2"]
    assert "_rerank_score" not in partial[1].meta


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({}, "invalid_response"),
        ({"results": []}, "empty_response"),
        ({"results": [{"index": 3, "relevance_score": 1}]}, "invalid_index"),
        (
            {
                "results": [
                    {"index": 0, "relevance_score": 1},
                    {"index": 0, "relevance_score": 0.5},
                ]
            },
            "duplicate_index",
        ),
        ({"results": [{"index": 0, "relevance_score": "nan"}]}, "invalid_score"),
    ],
)
def test_zhipu_reranker_rejects_invalid_provider_responses(payload, code):
    client = client_for(lambda _request: httpx.Response(200, json=payload))

    with pytest.raises(RerankerError) as error:
        reranker_with(client).rerank("query", [result(0), result(1)])

    assert error.value.code == code


def test_zhipu_reranker_sanitizes_http_and_timeout_failures():
    http_client = client_for(lambda _request: httpx.Response(401, text="secret provider body"))
    with pytest.raises(RerankerError, match="HTTP 401") as http_error:
        reranker_with(http_client).rerank("private query", [result(0)])
    assert "secret provider body" not in str(http_error.value)

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("private timeout body", request=request)

    with pytest.raises(RerankerError) as timeout_error:
        reranker_with(client_for(timeout_handler)).rerank("private query", [result(0)])
    assert timeout_error.value.code == "timeout"
    assert "private" not in str(timeout_error.value)


def test_fail_open_reranker_returns_baseline_and_records_fallback(caplog):
    class BrokenReranker(ZhipuReranker):
        name = "broken"

        def __init__(self) -> None:
            pass

        def rerank(self, query, results, *, top_n=None):
            raise RerankerError("provider_down", f"must not log {query}")

    inputs = [result(0), result(1), result(2)]
    before = metrics.snapshot()
    caplog.set_level(logging.WARNING)

    outputs = FailOpenReranker(BrokenReranker()).rerank("private-query-value", inputs, top_n=2)

    after = metrics.snapshot()
    assert outputs == inputs[:2]
    assert after["rerank_requests_total"] == before["rerank_requests_total"] + 1
    assert after["rerank_fallback_total"] == before["rerank_fallback_total"] + 1
    assert "private-query-value" not in caplog.text
    assert caplog.records[-1].extra_data["error_code"] == "provider_down"


def test_fail_open_reranker_records_success():
    class WorkingReranker:
        name = "working"

        def rerank(self, query, results, *, top_n=None):
            del query
            return list(reversed(results))[:top_n]

    inputs = [result(0), result(1)]
    before = metrics.snapshot()

    outputs = FailOpenReranker(WorkingReranker()).rerank("query", inputs, top_n=1)

    after = metrics.snapshot()
    assert outputs == [inputs[1]]
    assert after["rerank_requests_total"] == before["rerank_requests_total"] + 1
    assert after["rerank_success_total"] == before["rerank_success_total"] + 1
    assert after["rerank_duration_ms"]["count"] == before["rerank_duration_ms"]["count"] + 1


def test_candidate_document_includes_authority_context_and_stays_bounded():
    document = _candidate_document(result(0, text="正文" * 5000))

    assert "规范：建筑结构荷载规范 GB 50009-2012" in document
    assert "依据类型：body_table" in document
    assert len(document) == MAX_TEXT_CHARS


def test_retrieval_expands_candidate_pool_before_reranking():
    class SpyReranker:
        name = "spy"

        def __init__(self) -> None:
            self.candidate_count = 0
            self.top_n = 0

        def rerank(self, query, results, *, top_n=None):
            del query
            self.candidate_count = len(results)
            self.top_n = top_n
            return results[:top_n]

    class FakeCollection:
        def __bool__(self):
            return True

        def get(self):
            return {"ids": [], "documents": [], "metadatas": []}

    spy = SpyReranker()
    config = Settings(
        rerank_enabled=True,
        rerank_provider="zhipu",
        zhipuai_api_key="test-key",
        rerank_candidate_multiplier=3,
    )
    state = RetrievalState(config, reranker=spy)
    state.chroma_collection = FakeCollection()
    state.zhipu_client = None
    observed_limits: list[int] = []

    state._add_clause_matches = lambda *_args: None

    def add_candidates(_query_info, limit, _all_data, _docs, _metas, pool):
        observed_limits.append(limit)
        for index in range(limit):
            pool[str(index)] = RetrievalCandidate(
                doc_id=str(index),
                text=f"candidate {index}",
                meta={"section_type": "body"},
                score=float(limit - index),
            )

    state._add_bm25_matches = add_candidates
    state._add_table_intent_matches = lambda *_args: None
    state._add_value_table_matches = lambda *_args: None
    state._apply_domain_ranking = lambda *_args: None

    outputs = state.hybrid_search("query", 5)

    assert observed_limits == [15]
    assert spy.candidate_count == 15
    assert spy.top_n == 5
    assert len(outputs) == 5


@pytest.mark.parametrize("candidate_limit", [0, 129])
def test_retrieval_candidate_pool_rejects_provider_limit_violations(candidate_limit):
    state = RetrievalState()

    with pytest.raises(ValueError, match="1 到 128"):
        state.retrieve_candidates("query", candidate_limit)
