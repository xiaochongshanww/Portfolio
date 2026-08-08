from src.app.core.errors import ErrorCode, error_payload
from src.app.core.rate_limit import RateLimiter
from src.app.core.request_context import reset_request_id, set_request_id


def test_error_payload_shape_includes_request_id():
    token = set_request_id("req-1")
    try:
        payload = error_payload(ErrorCode.INVALID_REQUEST, "bad request")
        assert payload == {
            "error": {
                "code": "INVALID_REQUEST",
                "message": "bad request",
                "request_id": "req-1",
            }
        }
    finally:
        reset_request_id(token)


def test_rate_limiter_allows_basic_requests():
    limiter = RateLimiter()
    assert limiter.allow("client:/path") is True


def test_security_path_rules():
    from types import SimpleNamespace

    from src.app.core.security import is_protected_path, is_trusted_local_request

    assert is_protected_path("/v1/chat/completions") is True
    assert is_protected_path("/chat/completions") is True
    assert is_protected_path("/images/a.png") is True
    assert is_protected_path("/page-images/doc.pdf/1") is True
    assert is_protected_path("/corrections/candidates") is True
    assert is_protected_path("/admin/jobs/rebuild") is True
    assert is_protected_path("/health") is False
    direct_local = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))
    tunneled = SimpleNamespace(
        headers={"x-forwarded-for": "203.0.113.8"},
        client=SimpleNamespace(host="127.0.0.1"),
    )
    assert is_trusted_local_request(direct_local) is True
    assert is_trusted_local_request(tunneled) is False


def test_metrics_snapshot_shape():
    from src.app.core.metrics import Metrics

    metrics = Metrics()
    metrics.increment_request("/v1/chat/completions")
    metrics.request_finished("/v1/chat/completions", 502, 25)
    metrics.increment_error("LLM_REQUEST_FAILED", "/v1/chat/completions")
    snapshot = metrics.snapshot()
    assert snapshot["requests_total"] == 1
    assert snapshot["chat_requests_total"] == 1
    assert snapshot["chat_errors_total"] == 1
    assert snapshot["llm_errors_total"] == 1
    assert snapshot["responses_total"] == 1
    assert snapshot["requests_in_flight"] == 0
    assert snapshot["requests_by_group"] == {"chat": 1}
    assert snapshot["responses_by_status"] == {"502": 1}
    assert snapshot["errors_by_code"] == {"LLM_REQUEST_FAILED": 1}
    assert snapshot["request_duration_ms"] == {"count": 1, "average": 25.0, "max": 25}
