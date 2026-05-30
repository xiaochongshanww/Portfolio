from ..core.config import settings
from .base import BaseReranker
from .noop import NoopReranker


def get_reranker() -> BaseReranker:
    if not settings.rerank_enabled:
        return NoopReranker()
    # Stage 3 only establishes the extension point. Unknown providers degrade safely.
    return NoopReranker()

