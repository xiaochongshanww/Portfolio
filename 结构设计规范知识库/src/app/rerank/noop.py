from ..retrieval.models import RetrievalResult
from .base import BaseReranker


class NoopReranker(BaseReranker):
    name = "none"

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        *,
        top_n: int | None = None,
    ) -> list[RetrievalResult]:
        del query
        return results if top_n is None else results[:top_n]
