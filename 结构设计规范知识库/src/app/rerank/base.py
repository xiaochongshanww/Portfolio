from abc import ABC, abstractmethod

from ..retrieval.models import RetrievalResult


class BaseReranker(ABC):
    name = "unknown"

    @abstractmethod
    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        *,
        top_n: int | None = None,
    ) -> list[RetrievalResult]:
        """Return reranked retrieval results."""
