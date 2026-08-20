from __future__ import annotations

from typing import Any

from .config import Settings


def embedding_request_kwargs(
    config: Settings,
    inputs: str | list[str],
) -> dict[str, Any]:
    """Build a provider request while keeping legacy embedding-2 calls compatible."""
    request: dict[str, Any] = {
        "model": config.embedding_model,
        "input": inputs,
    }
    if config.embedding_model == "embedding-3":
        request["dimensions"] = config.embedding_dimensions
    return request
