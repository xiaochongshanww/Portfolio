from dataclasses import replace

from ..retrieval.models import RetrievalResult


def _rank_points(rank: int, count: int) -> float:
    if count <= 1:
        return 1.0
    return 1.0 - ((rank - 1) / (count - 1))


def fuse_rankings(
    results: list[RetrievalResult],
    model_scores: dict[int, float],
    *,
    model_weight: float,
    top_n: int,
) -> list[RetrievalResult]:
    """Fuse baseline and learned ranks while retaining baseline score semantics."""
    if not results or top_n <= 0:
        return []

    baseline_ranks = {index: index + 1 for index in range(len(results))}
    model_order = sorted(model_scores, key=lambda index: (-model_scores[index], index))
    missing = [index for index in range(len(results)) if index not in model_scores]
    model_order.extend(missing)
    model_ranks = {index: rank for rank, index in enumerate(model_order, start=1)}

    fused: list[tuple[float, int, RetrievalResult]] = []
    for index, result in enumerate(results):
        baseline_rank = baseline_ranks[index]
        model_rank = model_ranks[index]
        fusion_score = (1 - model_weight) * _rank_points(
            baseline_rank, len(results)
        ) + model_weight * _rank_points(model_rank, len(results))
        metadata = dict(result.meta)
        metadata.update(
            {
                "_retrieval_rank": baseline_rank,
                "_rerank_rank": model_rank,
                "_rerank_fusion_score": round(fusion_score, 12),
            }
        )
        if index in model_scores:
            metadata["_rerank_score"] = model_scores[index]
        source_parts = set(result.source.split("+")) if result.source else set()
        source_parts.add("rerank")
        reason = result.reason
        if "learned rerank fusion" not in reason:
            reason = f"{reason} + learned rerank fusion"
        fused.append(
            (
                fusion_score,
                baseline_rank,
                replace(
                    result,
                    meta=metadata,
                    source="+".join(sorted(source_parts)),
                    reason=reason,
                ),
            )
        )

    fused.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in fused[:top_n]]
