from ..retrieval.models import RetrievalResult
from .base import BaseReranker


class NoopReranker(BaseReranker):
    def rerank(self, query: str, results: list[RetrievalResult]) -> list[RetrievalResult]:
        return results

