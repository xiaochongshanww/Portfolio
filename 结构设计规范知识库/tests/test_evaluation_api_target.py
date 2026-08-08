import httpx
import pytest

from src.app.core.urls import normalize_http_base_url
from src.evaluation.api_target import probe_api_readiness


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_normalize_http_base_url_rejects_unsafe_components():
    assert normalize_http_base_url("HTTPS://example.com/kb/") == "https://example.com/kb"

    for value in (
        "file:///tmp/api",
        "http://user:secret@example.com",
        "http://example.com?target=other",
        "http:///missing-host",
    ):
        with pytest.raises(ValueError):
            normalize_http_base_url(value, field_name="TARGET")


def test_readiness_probe_accepts_ready_target_and_preserves_prefix():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://127.0.0.1:8017/internal/ready"
        return httpx.Response(
            200,
            json={
                "ready": True,
                "reasons": [],
                "checks": {"chroma": "ok"},
                "data_version_hash": "v1",
            },
        )

    with _client(handler) as client:
        result = probe_api_readiness("http://127.0.0.1:8017/internal/", client=client)

    assert result["ok"] is True
    assert result["api_base"] == "http://127.0.0.1:8017/internal"
    assert result["data_version_hash"] == "v1"


def test_readiness_probe_surfaces_machine_readable_reasons():
    with _client(
        lambda request: httpx.Response(
            503,
            json={
                "ready": False,
                "reasons": ["CHROMA_MISSING", "MIMO_KEY_MISSING"],
                "checks": {"chroma": "missing"},
            },
        )
    ) as client:
        result = probe_api_readiness("http://127.0.0.1:8017", client=client)

    assert result["ok"] is False
    assert result["status_code"] == 503
    assert result["reasons"] == ["CHROMA_MISSING", "MIMO_KEY_MISSING"]
    assert "CHROMA_MISSING, MIMO_KEY_MISSING" in result["error"]


def test_readiness_probe_reports_invalid_json():
    with _client(lambda request: httpx.Response(200, text="not-json")) as client:
        result = probe_api_readiness("http://127.0.0.1:8017", client=client)

    assert result["ok"] is False
    assert "未返回有效 JSON" in result["error"]

    with _client(lambda request: httpx.Response(200, json=[])) as client:
        result = probe_api_readiness("http://127.0.0.1:8017", client=client)
    assert result["ok"] is False
    assert "JSON 必须是对象" in result["error"]
