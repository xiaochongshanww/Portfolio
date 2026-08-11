import asyncio
import time
from types import SimpleNamespace

import httpx
from src.app.core.config import Settings
from src.app.core.provider_probe import probe_model_providers


class FakeEmbeddings:
    def __init__(self, result=None, error: BaseException | None = None, delay: float = 0) -> None:
        self.result = result
        self.error = error
        self.delay = delay

    def create(self, **kwargs):
        assert kwargs["model"] == "embedding-test"
        assert kwargs["input"] == ["connectivity"]
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        return self.result


class FakeEmbeddingClient:
    def __init__(self, embeddings: FakeEmbeddings) -> None:
        self.embeddings = embeddings


class ProviderHttpError(RuntimeError):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__("upstream body must not leak")


def config() -> Settings:
    return Settings(
        zhipuai_api_key="zhipu-secret",
        mimo_api_key="mimo-secret",
        mimo_base_url="https://provider.invalid/v1",
        mimo_model="mimo-test",
        embedding_model="embedding-test",
    )


def embedding_success() -> FakeEmbeddingClient:
    return FakeEmbeddingClient(
        FakeEmbeddings(SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])]))
    )


def test_provider_probe_reports_two_successful_capabilities_without_payloads() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer mimo-secret"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "private generated output"}}]},
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await probe_model_providers(
                embedding_client=embedding_success(),
                config=config(),
                http_client=client,
            )

    result = asyncio.run(run())

    assert result["ok"] is True
    assert [item["status"] for item in result["providers"]] == ["ok", "ok"]
    rendered = str(result)
    assert "mimo-secret" not in rendered
    assert "zhipu-secret" not in rendered
    assert "private generated output" not in rendered


def test_provider_probe_classifies_auth_and_rate_limit_without_error_text() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="sensitive upstream body")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await probe_model_providers(
                embedding_client=FakeEmbeddingClient(FakeEmbeddings(error=ProviderHttpError(429))),
                config=config(),
                http_client=client,
            )

    result = asyncio.run(run())

    assert result["ok"] is False
    assert result["providers"][0]["status"] == "rate_limited"
    assert result["providers"][0]["http_status"] == 429
    assert result["providers"][1]["status"] == "auth_failed"
    assert result["providers"][1]["http_status"] == 401
    assert "sensitive upstream body" not in str(result)
    assert "upstream body must not leak" not in str(result)


def test_provider_probe_classifies_timeout_and_invalid_response() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await probe_model_providers(
                embedding_client=FakeEmbeddingClient(FakeEmbeddings(delay=0.05)),
                config=config(),
                timeout_seconds=0.01,
                http_client=client,
            )

    result = asyncio.run(run())

    assert result["ok"] is False
    assert result["providers"][0]["status"] == "timeout"
    assert result["providers"][1]["status"] == "invalid_response"


def test_provider_probe_classifies_server_and_transport_unavailability() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="sensitive outage detail")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await probe_model_providers(
                embedding_client=FakeEmbeddingClient(
                    FakeEmbeddings(error=OSError("private network destination"))
                ),
                config=config(),
                http_client=client,
            )

    result = asyncio.run(run())

    assert result["ok"] is False
    assert result["providers"][0]["status"] == "unavailable"
    assert result["providers"][0]["http_status"] is None
    assert result["providers"][1]["status"] == "unavailable"
    assert result["providers"][1]["http_status"] == 503
    assert "private network destination" not in str(result)
    assert "sensitive outage detail" not in str(result)


def test_provider_probe_reports_missing_configuration_without_network() -> None:
    result = asyncio.run(
        probe_model_providers(
            embedding_client=None,
            config=Settings(zhipuai_api_key="", mimo_api_key=""),
        )
    )

    assert result["ok"] is False
    assert [item["status"] for item in result["providers"]] == [
        "not_configured",
        "not_configured",
    ]
