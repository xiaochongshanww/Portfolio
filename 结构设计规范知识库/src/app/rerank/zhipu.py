from __future__ import annotations

from math import isfinite
from typing import Any

import httpx

from ..retrieval.models import RetrievalResult
from .base import BaseReranker
from .errors import RerankerError
from .fusion import fuse_rankings

MAX_CANDIDATES = 128
MAX_TEXT_CHARS = 4096


def _candidate_document(result: RetrievalResult) -> str:
    meta = result.meta
    header = [
        f"规范：{meta.get('name', '')} {meta.get('code', '')}".strip(),
        f"标题：{meta.get('title', '')}".strip(),
        f"条文号：{meta.get('clause_number', '')}".strip(),
        f"依据类型：{meta.get('section_type', '')}".strip(),
        f"表号与表名：{meta.get('table_id', '')} {meta.get('table_name', '')}".strip(),
        "内容：",
    ]
    prefix = "\n".join(header)
    remaining = max(0, MAX_TEXT_CHARS - len(prefix) - 1)
    return f"{prefix}\n{result.text[:remaining]}"[:MAX_TEXT_CHARS]


def _model_scores(payload: Any, candidate_count: int) -> dict[int, float]:
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise RerankerError("invalid_response", "精排响应缺少 results 数组")
    rows = payload["results"]
    if not rows:
        raise RerankerError("empty_response", "精排响应没有候选结果")

    scores: dict[int, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise RerankerError("invalid_response", "精排结果项不是对象")
        index = row.get("index")
        raw_score = row.get("relevance_score")
        if isinstance(index, bool) or not isinstance(index, int):
            raise RerankerError("invalid_index", "精排结果索引不是整数")
        if index < 0 or index >= candidate_count:
            raise RerankerError("invalid_index", "精排结果索引越界")
        if index in scores:
            raise RerankerError("duplicate_index", "精排结果包含重复索引")
        if isinstance(raw_score, bool):
            raise RerankerError("invalid_score", "精排相关性分数不是有限数字")
        try:
            score = float(raw_score)
        except (TypeError, ValueError) as exc:
            raise RerankerError("invalid_score", "精排相关性分数不是有限数字") from exc
        if not isfinite(score):
            raise RerankerError("invalid_score", "精排相关性分数不是有限数字")
        scores[index] = score
    return scores


class ZhipuReranker(BaseReranker):
    name = "zhipu"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        model_weight: float,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._model_weight = model_weight
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        *,
        top_n: int | None = None,
    ) -> list[RetrievalResult]:
        if not results:
            return []
        limited = results[:MAX_CANDIDATES]
        requested = len(limited) if top_n is None else min(max(top_n, 0), len(limited))
        if requested == 0:
            return []
        try:
            response = self._client.post(
                f"{self._base_url}/rerank",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "query": query[:MAX_TEXT_CHARS],
                    "documents": [_candidate_document(result) for result in limited],
                    "top_n": len(limited),
                    "return_documents": False,
                },
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RerankerError("timeout", "精排请求超时") from exc
        except httpx.HTTPStatusError as exc:
            raise RerankerError(
                "http_error", f"精排服务返回 HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise RerankerError("network_error", "精排服务网络请求失败") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise RerankerError("invalid_json", "精排响应不是有效 JSON") from exc
        scores = _model_scores(payload, len(limited))
        return fuse_rankings(
            limited,
            scores,
            model_weight=self._model_weight,
            top_n=requested,
        )
