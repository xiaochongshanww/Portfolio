import asyncio

from src.app.rag import service
from src.app.retrieval.models import RetrievalResult
from src.app.schemas.chat import ChatCompletionRequest, ChatMessage


def _request() -> ChatCompletionRequest:
    return ChatCompletionRequest(messages=[ChatMessage(role="user", content="测试问题")])


def _result() -> RetrievalResult:
    return RetrievalResult(
        doc_id="chunk-1",
        text="测试规范正文",
        meta={"source": "test.pdf", "pages": "30", "_distance": 0.1},
        score=1.0,
        source="bm25",
        reason="test",
    )


def _prepare_retrieval(monkeypatch) -> None:
    monkeypatch.setattr(service.retrieval_state, "chroma_collection", object())
    monkeypatch.setattr(service.retrieval_state, "zhipu_client", object())
    monkeypatch.setattr(service.retrieval_state, "hybrid_search", lambda *_: [_result()])
    monkeypatch.setattr(service, "find_structured_table_matches", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(service, "load_images_by_name", lambda *_: [])
    monkeypatch.setattr(service, "load_page_images", lambda *_: [])
    monkeypatch.setattr(service, "page_image_filenames", lambda *_: [])


def test_payload_does_not_offer_missing_page_images(monkeypatch):
    _prepare_retrieval(monkeypatch)
    monkeypatch.setattr(service, "source_pdf_available", lambda *_: False)

    payload, images, trace = asyncio.run(service.build_mimo_payload(_request()))
    user_text = payload["messages"][-1]["content"][0]["text"]

    assert images == []
    assert trace["image_urls"] == []
    assert "/page-images/" not in user_text
    assert "当前知识包未提供可引用的页面截图" in user_text


def test_payload_offers_page_images_when_source_pdf_exists(monkeypatch):
    _prepare_retrieval(monkeypatch)
    monkeypatch.setattr(service, "source_pdf_available", lambda *_: True)

    payload, _images, trace = asyncio.run(service.build_mimo_payload(_request()))
    user_text = payload["messages"][-1]["content"][0]["text"]

    assert trace["image_urls"] == ["/page-images/test.pdf/30"]
    assert "![第30页](/page-images/test.pdf/30)" in user_text
