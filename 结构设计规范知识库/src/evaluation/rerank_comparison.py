from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.app.rag.structured_tables import find_structured_table_matches
from src.app.rerank.base import BaseReranker
from src.app.rerank.factory import get_reranker
from src.app.retrieval.hybrid_search import RetrievalState, retrieval_state
from src.pipeline.active_db import read_active_manifest

from .runner import DEFAULT_EVAL_PATH, load_cases, summarize_results

COMPARISON_METRICS = (
    "source_hit_rate",
    "top1_source_hit_rate",
    "clause_hit_rate",
    "keyword_hit_rate",
    "table_hit_rate",
    "authority_hit_rate",
    "qualified_hit_rate",
    "qualified_top1_hit_rate",
    "qualified_hit_at_3",
    "qualified_hit_at_5",
    "qualified_mrr",
)


def _rank_map(summary: dict[str, Any]) -> dict[str, int | None]:
    return {
        str(item["id"]): item.get("first_qualified_rank")
        for item in summary.get("ranking_cases", [])
    }


def _rank_change(before: int | None, after: int | None) -> str:
    if before == after:
        return "unchanged"
    if before is None:
        return "improved"
    if after is None:
        return "regressed"
    return "improved" if after < before else "regressed"


def _has_rerank_metadata(results: list[Any]) -> bool:
    return bool(results) and any("_rerank_rank" in result.meta for result in results)


def run_rerank_comparison(
    path: Path = DEFAULT_EVAL_PATH,
    *,
    top_k: int = 5,
    state: RetrievalState | None = None,
    reranker: BaseReranker | None = None,
) -> dict[str, Any]:
    if top_k <= 0:
        raise ValueError("top_k 必须大于 0")
    cases = load_cases(path)
    comparable_cases = [case for case in cases if case.type != "structured_table"]
    if not comparable_cases:
        return {"ok": False, "error": "评估集没有可用于候选精排对照的用例"}

    evaluation_state = state or retrieval_state
    if state is None and not evaluation_state.ready:
        evaluation_state.initialize()
    if not evaluation_state.ready:
        return {"ok": False, "error": "知识库检索服务未就绪，无法执行精排对照"}

    selected_reranker = reranker or get_reranker(evaluation_state.config)
    if selected_reranker.name == "none":
        return {"ok": False, "error": "未启用可用的精排提供方，无法执行精排对照"}

    multiplier = evaluation_state.config.rerank_candidate_multiplier
    candidate_limit = min(128, max(top_k, top_k * multiplier))
    baseline_by_id = {}
    candidate_by_id = {}
    for case in comparable_cases:
        normalized_query, pool = evaluation_state.retrieve_candidates(case.query, candidate_limit)
        baseline_by_id[case.id] = pool[:top_k]
        candidate_results = selected_reranker.rerank(normalized_query, pool, top_n=top_k)
        candidate_by_id[case.id] = candidate_results
        if pool and not _has_rerank_metadata(candidate_results):
            manifest = read_active_manifest()
            return {
                "ok": False,
                "comparison_complete": False,
                "generated_at": datetime.now(UTC).isoformat(),
                "evaluation_set": str(path.resolve()),
                "evaluation_set_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
                "data_version_hash": str(manifest.get("data_version_hash") or ""),
                "provider": selected_reranker.name,
                "model": evaluation_state.config.rerank_model,
                "top_k": top_k,
                "candidate_limit": candidate_limit,
                "case_count": len(comparable_cases),
                "processed_case_count": len(candidate_by_id),
                "reranked_case_count": 0,
                "fallback_case_count": 1,
                "error": ("精排对照在首个降级用例处提前停止，不能将基线结果解释为真实精排结果"),
            }

    structured_by_id = {
        case.id: find_structured_table_matches(case.query, limit=top_k)
        for case in cases
        if case.expected_table_id
    }
    baseline = summarize_results(comparable_cases, baseline_by_id, structured_by_id)
    candidate = summarize_results(comparable_cases, candidate_by_id, structured_by_id)
    baseline_ranks = _rank_map(baseline)
    candidate_ranks = _rank_map(candidate)
    case_changes = []
    change_counts = {"improved": 0, "unchanged": 0, "regressed": 0}
    for case in comparable_cases:
        before = baseline_ranks.get(case.id)
        after = candidate_ranks.get(case.id)
        change = _rank_change(before, after)
        change_counts[change] += 1
        case_changes.append(
            {
                "id": case.id,
                "type": case.type,
                "query": case.query,
                "baseline_rank": before,
                "reranked_rank": after,
                "change": change,
            }
        )

    metric_deltas = {
        metric: float(candidate.get(metric, 0)) - float(baseline.get(metric, 0))
        for metric in COMPARISON_METRICS
    }
    reranked_case_count = sum(_has_rerank_metadata(results) for results in candidate_by_id.values())
    fallback_case_count = len(comparable_cases) - reranked_case_count
    manifest = read_active_manifest()
    report = {
        "ok": True,
        "comparison_complete": fallback_case_count == 0,
        "generated_at": datetime.now(UTC).isoformat(),
        "evaluation_set": str(path.resolve()),
        "evaluation_set_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
        "data_version_hash": str(manifest.get("data_version_hash") or ""),
        "provider": selected_reranker.name,
        "model": evaluation_state.config.rerank_model,
        "top_k": top_k,
        "candidate_limit": candidate_limit,
        "case_count": len(comparable_cases),
        "reranked_case_count": reranked_case_count,
        "fallback_case_count": fallback_case_count,
        "baseline": baseline,
        "reranked": candidate,
        "metric_deltas": metric_deltas,
        "change_counts": change_counts,
        "case_changes": case_changes,
    }
    if fallback_case_count:
        report["ok"] = False
        report["error"] = (
            f"精排对照未完成：{fallback_case_count} 个用例发生提供方降级，"
            "不能将基线结果解释为真实精排结果"
        )
    return report


def render_rerank_comparison_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 候选精排对照评估",
        "",
        f"- 执行状态：{'完成' if result.get('ok') else '失败'}",
        f"- 生成时间：`{result.get('generated_at', '-')}`",
        f"- 提供方 / 模型：`{result.get('provider', '-')}` / `{result.get('model', '-')}`",
        f"- 数据版本：`{result.get('data_version_hash', '-')}`",
        f"- 评估集哈希：`{result.get('evaluation_set_hash', '-')}`",
        f"- 用例数：{result.get('case_count', 0)}",
        f"- 最终 Top K / 候选池：{result.get('top_k', 0)} / {result.get('candidate_limit', 0)}",
        f"- 对照完整性：{'完整' if result.get('comparison_complete') else '不完整'}",
        f"- 实际精排 / 降级用例：{result.get('reranked_case_count', 0)} / "
        f"{result.get('fallback_case_count', 0)}",
        "",
    ]
    if result.get("error"):
        lines.extend(["## 执行提示", "", str(result["error"]), ""])
        if "baseline" not in result:
            return "\n".join(lines) + "\n"

    baseline = result.get("baseline", {})
    reranked = result.get("reranked", {})
    deltas = result.get("metric_deltas", {})
    lines.extend(
        [
            "## 指标对照",
            "",
            "| 指标 | 基线 | 精排 | 变化 |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for metric in COMPARISON_METRICS:
        lines.append(
            f"| `{metric}` | {float(baseline.get(metric, 0)):.4f} | "
            f"{float(reranked.get(metric, 0)):.4f} | {float(deltas.get(metric, 0)):+.4f} |"
        )

    counts = result.get("change_counts", {})
    lines.extend(
        [
            "",
            "## 位次变化",
            "",
            f"- 改善：{counts.get('improved', 0)}",
            f"- 不变：{counts.get('unchanged', 0)}",
            f"- 退化：{counts.get('regressed', 0)}",
            "",
            "| 用例 | 类型 | 基线位次 | 精排位次 | 结果 |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )
    for item in result.get("case_changes", []):
        baseline_rank = item.get("baseline_rank") or "-"
        reranked_rank = item.get("reranked_rank") or "-"
        lines.append(
            f"| `{item.get('id', '')}` | `{item.get('type', '')}` | {baseline_rank} | "
            f"{reranked_rank} | {item.get('change', '')} |"
        )
    lines.extend(
        [
            "",
            "> 本报告只比较候选排序；是否启用还必须结合回答级盲测、时延、费用与降级率。",
            "",
        ]
    )
    return "\n".join(lines)
