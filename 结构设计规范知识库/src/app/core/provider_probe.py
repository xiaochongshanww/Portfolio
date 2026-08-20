from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from .config import Settings, settings
from .embeddings import embedding_request_kwargs

PROBE_TIMEOUT_SECONDS = 15.0
PROBE_INPUT = "connectivity"


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))


def _http_status(exc: BaseException) -> int | None:
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if not isinstance(status_code, int):
        status_code = getattr(exc, "status_code", None)
    return status_code if isinstance(status_code, int) else None


def _failure_status(exc: BaseException) -> tuple[str, int | None]:
    status_code = _http_status(exc)
    if status_code in {401, 403}:
        return "auth_failed", status_code
    if status_code == 429:
        return "rate_limited", status_code
    if status_code is not None and status_code >= 500:
        return "unavailable", status_code
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError, httpx.TimeoutException)) or (
        "timeout" in type(exc).__name__.lower()
    ):
        return "timeout", status_code
    if isinstance(exc, (OSError, httpx.RequestError)):
        return "unavailable", status_code
    return "request_failed", status_code


def _result(
    *,
    provider: str,
    capability: str,
    model: str,
    ok: bool,
    status: str,
    started: float,
    http_status: int | None = None,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "capability": capability,
        "model": model,
        "ok": ok,
        "status": status,
        "latency_ms": _elapsed_ms(started),
        "http_status": http_status,
    }


async def _probe_embedding(
    embedding_client: Any,
    config: Settings,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    started = time.monotonic()
    common = {
        "provider": "zhipuai",
        "capability": "embedding",
        "model": config.embedding_model,
        "started": started,
    }
    if not config.zhipuai_api_key:
        return _result(ok=False, status="not_configured", **common)
    if embedding_client is None:
        return _result(ok=False, status="unavailable", **common)
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                embedding_client.embeddings.create,
                **embedding_request_kwargs(config, [PROBE_INPUT]),
            ),
            timeout=timeout_seconds,
        )
        data = getattr(response, "data", None)
        embedding = getattr(data[0], "embedding", None) if data else None
        if not isinstance(embedding, (list, tuple)) or not embedding:
            return _result(ok=False, status="invalid_response", **common)
        return _result(ok=True, status="ok", **common)
    except Exception as exc:
        status, status_code = _failure_status(exc)
        return _result(ok=False, status=status, http_status=status_code, **common)


async def _probe_chat(
    config: Settings,
    *,
    timeout_seconds: float,
    http_client: httpx.AsyncClient | None,
) -> dict[str, Any]:
    started = time.monotonic()
    common = {
        "provider": "mimo",
        "capability": "chat",
        "model": config.mimo_model,
        "started": started,
    }
    if not config.mimo_api_key:
        return _result(ok=False, status="not_configured", **common)

    client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
    owns_client = http_client is None
    try:
        response = await client.post(
            f"{config.mimo_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.mimo_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.mimo_model,
                "messages": [{"role": "user", "content": PROBE_INPUT}],
                "max_tokens": 1,
                "stream": False,
            },
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices") if isinstance(payload, dict) else None
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            return _result(ok=False, status="invalid_response", **common)
        return _result(ok=True, status="ok", **common)
    except Exception as exc:
        status, status_code = _failure_status(exc)
        return _result(ok=False, status=status, http_status=status_code, **common)
    finally:
        if owns_client:
            await client.aclose()


async def probe_model_providers(
    *,
    embedding_client: Any,
    config: Settings = settings,
    timeout_seconds: float = PROBE_TIMEOUT_SECONDS,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise ValueError("供应商探测超时必须大于 0")
    embedding, chat = await asyncio.gather(
        _probe_embedding(embedding_client, config, timeout_seconds=timeout_seconds),
        _probe_chat(config, timeout_seconds=timeout_seconds, http_client=http_client),
    )
    providers = [embedding, chat]
    return {
        "ok": all(item["ok"] for item in providers),
        "checked_at": datetime.now(UTC).isoformat(),
        "providers": providers,
    }
