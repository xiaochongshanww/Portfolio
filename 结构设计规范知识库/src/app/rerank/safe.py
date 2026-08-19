import logging
from time import perf_counter

from ..core.metrics import metrics
from ..retrieval.models import RetrievalResult
from .base import BaseReranker
from .errors import RerankerError


class FailOpenReranker(BaseReranker):
    def __init__(self, delegate: BaseReranker) -> None:
        self.delegate = delegate
        self.name = delegate.name
        self.last_failure: dict[str, int | str | None] | None = None

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        *,
        top_n: int | None = None,
    ) -> list[RetrievalResult]:
        started = perf_counter()
        requested = len(results) if top_n is None else max(top_n, 0)
        self.last_failure = None
        try:
            reranked = self.delegate.rerank(query, results, top_n=top_n)
        except Exception as exc:
            duration_ms = int((perf_counter() - started) * 1000)
            code = exc.code if isinstance(exc, RerankerError) else "unexpected_error"
            http_status = exc.http_status if isinstance(exc, RerankerError) else None
            self.last_failure = {"code": code, "http_status": http_status}
            metrics.record_rerank(success=False, duration_ms=duration_ms)
            logging.warning(
                "rerank_fallback",
                extra={
                    "extra_data": {
                        "provider": self.name,
                        "candidate_count": len(results),
                        "duration_ms": duration_ms,
                        "error_code": code,
                    }
                },
            )
            return results[:requested]

        duration_ms = int((perf_counter() - started) * 1000)
        metrics.record_rerank(success=True, duration_ms=duration_ms)
        logging.info(
            "rerank_completed",
            extra={
                "extra_data": {
                    "provider": self.name,
                    "candidate_count": len(results),
                    "result_count": len(reranked),
                    "duration_ms": duration_ms,
                }
            },
        )
        return reranked
