import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.app.retrieval.models import RetrievalResult
from src.app.retrieval.hybrid_search import retrieval_state


DEFAULT_EVAL_PATH = Path(__file__).resolve().parents[2] / "data" / "evaluation" / "queries.jsonl"


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    query: str
    expected_sources: list[str]
    expected_clause: str = ""
    expected_keywords: list[str] | None = None
    type: str = "general"


def load_cases(path: Path = DEFAULT_EVAL_PATH) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    if not path.exists():
        return cases
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        cases.append(
            EvaluationCase(
                id=data["id"],
                query=data["query"],
                expected_sources=data.get("expected_sources", []),
                expected_clause=data.get("expected_clause", ""),
                expected_keywords=data.get("expected_keywords", []),
                type=data.get("type", "general"),
            )
        )
    return cases


def _source_hit(case: EvaluationCase, results: list[RetrievalResult]) -> bool:
    if not case.expected_sources:
        return True
    haystack = "\n".join(
        " ".join(str(result.meta.get(key, "")) for key in ("source_file", "code", "name"))
        for result in results
    )
    return any(source in haystack for source in case.expected_sources)


def _clause_hit(case: EvaluationCase, results: list[RetrievalResult]) -> bool:
    if not case.expected_clause:
        return True
    return any(case.expected_clause == str(result.meta.get("clause_number", "")) for result in results)


def _keyword_hit(case: EvaluationCase, results: list[RetrievalResult]) -> bool:
    if not case.expected_keywords:
        return True
    text = "\n".join(result.text for result in results)
    return any(keyword in text for keyword in case.expected_keywords)


def summarize_results(cases: list[EvaluationCase], results_by_id: dict[str, list[RetrievalResult]]) -> dict[str, Any]:
    failures = []
    source_hits = 0
    clause_hits = 0
    keyword_hits = 0

    for case in cases:
        results = results_by_id.get(case.id, [])
        source_ok = _source_hit(case, results)
        clause_ok = _clause_hit(case, results)
        keyword_ok = _keyword_hit(case, results)
        source_hits += int(source_ok)
        clause_hits += int(clause_ok)
        keyword_hits += int(keyword_ok)
        if not (source_ok and clause_ok and keyword_ok):
            failures.append(
                {
                    "id": case.id,
                    "query": case.query,
                    "source_hit": source_ok,
                    "clause_hit": clause_ok,
                    "keyword_hit": keyword_ok,
                    "top_results": [
                        {
                            "source_file": result.meta.get("source_file") or result.meta.get("source"),
                            "clause_number": result.meta.get("clause_number"),
                            "reason": result.reason,
                            "score": result.score,
                        }
                        for result in results[:3]
                    ],
                }
            )

    total = len(cases)
    return {
        "case_count": total,
        "source_hit_rate": source_hits / total if total else 0,
        "clause_hit_rate": clause_hits / total if total else 0,
        "keyword_hit_rate": keyword_hits / total if total else 0,
        "failures": failures,
    }


def run_evaluation(path: Path = DEFAULT_EVAL_PATH, top_k: int = 5) -> dict[str, Any]:
    if not retrieval_state.ready:
        return {"ok": False, "error": "知识库检索服务未就绪，请先启动并完成 ChromaDB/ZhipuAI 初始化"}

    cases = load_cases(path)
    results_by_id = {
        case.id: retrieval_state.hybrid_search(case.query, top_k)
        for case in cases
    }
    summary = summarize_results(cases, results_by_id)
    return {"ok": True, **summary}

