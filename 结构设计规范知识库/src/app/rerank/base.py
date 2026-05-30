from abc import ABC, abstractmethod

from ..retrieval.models import RetrievalResult


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, results: list[RetrievalResult]) -> list[RetrievalResult]:
        """Return reranked retrieval results."""

