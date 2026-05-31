from src.app.core.errors import ErrorCode, error_payload
from src.app.core.rate_limit import RateLimiter
from src.app.core.request_context import set_request_id


def test_error_payload_shape_includes_request_id():
    set_request_id("req-1")
    payload = error_payload(ErrorCode.INVALID_REQUEST, "bad request")
    assert payload == {
        "error": {
            "code": "INVALID_REQUEST",
            "message": "bad request",
            "request_id": "req-1",
        }
    }


def test_rate_limiter_allows_basic_requests():
    limiter = RateLimiter()
    assert limiter.allow("client:/path") is True


def test_security_path_rules():
    from src.app.core.security import is_protected_path

    assert is_protected_path("/v1/chat/completions") is True
    assert is_protected_path("/chat/completions") is True
    assert is_protected_path("/images/a.png") is True
    assert is_protected_path("/corrections/candidates") is True
    assert is_protected_path("/health") is False


def test_metrics_snapshot_shape():
    from src.app.core.metrics import Metrics

    metrics = Metrics()
    metrics.increment_request("/v1/chat/completions")
    metrics.increment_error("LLM_REQUEST_FAILED", "/v1/chat/completions")
    snapshot = metrics.snapshot()
    assert snapshot["requests_total"] == 1
    assert snapshot["chat_requests_total"] == 1
    assert snapshot["chat_errors_total"] == 1
    assert snapshot["llm_errors_total"] == 1
