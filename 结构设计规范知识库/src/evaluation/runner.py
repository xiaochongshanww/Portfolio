import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.app.retrieval.models import RetrievalResult
from src.app.retrieval.hybrid_search import (
    RetrievalState,
    infer_is_table,
    infer_section_type,
    retrieval_state,
    text_contains_clause_heading,
    text_mentions_clause,
)
from src.app.rag.structured_tables import (
    STRUCTURED_TABLE_DIR,
    StructuredTableMatch,
    find_structured_table_matches,
)
from src.pipeline.active_db import read_active_manifest
from src.pipeline.manifest import read_manifest


DEFAULT_EVAL_PATH = Path(__file__).resolve().parents[2] / "data" / "evaluation" / "queries.jsonl"
STRUCTURED_EVAL_PATH = Path(__file__).resolve().parents[2] / "data" / "evaluation" / "complex_structured_tables.jsonl"
SUPPORTED_CASE_TYPES = {
    "alias",
    "classification",
    "clause",
    "code",
    "definition",
    "formula",
    "general",
    "multi_spec",
    "structured_table",
    "table",
}


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    query: str
    expected_sources: list[str]
    expected_clause: str = ""
    expected_keywords: list[str] | None = None
    type: str = "general"
    expected_authority_type: str = ""
    top1_source_required: bool = True
    keyword_required: bool = True
    expected_table_id: str = ""


def validate_cases(cases: list[EvaluationCase], *, minimum_count: int = 0) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for index, case in enumerate(cases, start=1):
        label = case.id or f"line-{index}"
        if not case.id.strip():
            errors.append(f"{label}: id 不能为空")
        elif case.id in seen_ids:
            errors.append(f"{label}: id 重复")
        seen_ids.add(case.id)
        if not case.query.strip():
            errors.append(f"{label}: query 不能为空")
        if case.type not in SUPPORTED_CASE_TYPES:
            errors.append(f"{label}: 未知 type={case.type}")
        if not any(
            (
                case.expected_sources,
                case.expected_clause,
                case.expected_keywords,
                case.expected_authority_type,
                case.expected_table_id,
            )
        ):
            errors.append(f"{label}: 至少需要一种期望命中条件")
        if case.type == "structured_table" and not case.expected_table_id:
            errors.append(f"{label}: structured_table 用例必须提供 expected_table_id")
    if len(cases) < minimum_count:
        errors.append(f"评估集用例数不足：实际 {len(cases)}，最低 {minimum_count}")
    return errors


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
                expected_authority_type=data.get("expected_authority_type", ""),
                top1_source_required=data.get("top1_source_required", True),
                keyword_required=data.get("keyword_required", True),
                expected_table_id=data.get("expected_table_id", ""),
            )
        )
    minimum_count = 0
    if path.resolve() == DEFAULT_EVAL_PATH.resolve():
        minimum_count = 100
    elif path.resolve() == STRUCTURED_EVAL_PATH.resolve():
        minimum_count = 12
    errors = validate_cases(cases, minimum_count=minimum_count)
    if errors:
        raise ValueError("评估集契约校验失败：\n- " + "\n- ".join(errors))
    return cases


def structured_data_version_hash(directory: Path = STRUCTURED_TABLE_DIR) -> str:
    paths = sorted(directory.glob("*.json")) if directory.exists() else []
    if not paths:
        return ""
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _source_hit(case: EvaluationCase, results: list[RetrievalResult]) -> bool:
    if not case.expected_sources:
        return True
    haystack = "\n".join(
        " ".join(str(result.meta.get(key, "")) for key in ("source_file", "code", "name"))
        for result in results
    )
    return any(source in haystack for source in case.expected_sources)


def _top1_source_hit(case: EvaluationCase, results: list[RetrievalResult]) -> bool:
    if not case.top1_source_required:
        return True
    if not case.expected_sources or not results:
        return True
    top = results[0]
    haystack = " ".join(str(top.meta.get(key, "")) for key in ("source_file", "code", "name"))
    return any(source in haystack for source in case.expected_sources)


def _clause_hit(case: EvaluationCase, results: list[RetrievalResult]) -> bool:
    if not case.expected_clause:
        return True
    return any(
        case.expected_clause == str(result.meta.get("clause_number", ""))
        or case.expected_clause == str(result.meta.get("matched_clause_number", ""))
        or text_contains_clause_heading(str(result.meta.get("title", "")), case.expected_clause)
        or text_contains_clause_heading(result.text, case.expected_clause)
        or text_mentions_clause(result.text, case.expected_clause)
        for result in results
    )


def _keyword_hit(case: EvaluationCase, results: list[RetrievalResult]) -> bool:
    if not case.keyword_required:
        return True
    if not case.expected_keywords:
        return True
    text = "\n".join(
        "\n".join(
            [
                result.text,
                str(result.meta.get("title", "")),
                str(result.meta.get("table_name", "")),
                str(result.meta.get("name", "")),
                str(result.meta.get("code", "")),
            ]
        )
        for result in results
    )
    return any(keyword in text for keyword in case.expected_keywords)


def _table_hit(case: EvaluationCase, results: list[RetrievalResult]) -> bool:
    if case.type == "structured_table":
        return True
    if case.type != "table":
        return True
    return any(infer_is_table(result.meta, result.text) for result in results)


def _authority_hit(case: EvaluationCase, results: list[RetrievalResult]) -> bool:
    if case.type == "structured_table":
        return True
    if not results:
        return False
    top_section = infer_section_type(results[0].meta, results[0].text)
    if case.expected_authority_type:
        if case.expected_authority_type == "body_table":
            return top_section == "body_table" or infer_is_table(results[0].meta, results[0].text)
        if case.expected_authority_type == "body":
            return top_section == "body"
        if case.expected_authority_type == "body_or_table":
            return top_section in {"body", "body_table"} or infer_is_table(results[0].meta, results[0].text)
        if case.expected_authority_type == "explanation":
            return top_section == "explanation"
        if case.expected_authority_type == "non_explanation":
            return top_section != "explanation"
        if case.expected_authority_type == "any":
            return True
    if case.type == "table":
        return top_section == "body_table" or infer_is_table(results[0].meta, results[0].text)
    if case.type == "clause":
        return top_section in {"body", "body_table"}
    return top_section != "explanation"


def summarize_results(
    cases: list[EvaluationCase],
    results_by_id: dict[str, list[RetrievalResult]],
    structured_by_id: dict[str, list[StructuredTableMatch]] | None = None,
) -> dict[str, Any]:
    structured_by_id = structured_by_id or {}
    failures = []
    source_hits = 0
    top1_source_hits = 0
    clause_hits = 0
    keyword_hits = 0
    table_hits = 0
    authority_hits = 0
    structured_hits = 0
    structured_case_count = 0
    cases_by_type: dict[str, int] = {}
    failures_by_type: dict[str, int] = {}
    failures_by_check = {
        "source": 0,
        "top1_source": 0,
        "clause": 0,
        "keyword": 0,
        "table": 0,
        "authority": 0,
        "structured_table": 0,
    }

    for case in cases:
        cases_by_type[case.type] = cases_by_type.get(case.type, 0) + 1
        results = results_by_id.get(case.id, [])
        source_ok = _source_hit(case, results)
        top1_source_ok = _top1_source_hit(case, results)
        clause_ok = _clause_hit(case, results)
        keyword_ok = _keyword_hit(case, results)
        table_ok = _table_hit(case, results)
        authority_ok = _authority_hit(case, results)
        structured_matches = structured_by_id.get(case.id, [])
        structured_ok = (
            not case.expected_table_id
            or any(
                str(match.table.get("source", {}).get("table_id") or "") == case.expected_table_id
                for match in structured_matches
            )
        )
        if case.expected_table_id:
            structured_case_count += 1
            structured_hits += int(structured_ok)
        failed_checks = [
            name
            for name, ok in (
                ("source", source_ok),
                ("top1_source", top1_source_ok),
                ("clause", clause_ok),
                ("keyword", keyword_ok),
                ("table", table_ok),
                ("authority", authority_ok),
                ("structured_table", structured_ok),
            )
            if not ok
        ]
        source_hits += int(source_ok)
        top1_source_hits += int(top1_source_ok)
        clause_hits += int(clause_ok)
        keyword_hits += int(keyword_ok)
        table_hits += int(table_ok)
        authority_hits += int(authority_ok)
        if failed_checks:
            failures_by_type[case.type] = failures_by_type.get(case.type, 0) + 1
            for failed_check in failed_checks:
                failures_by_check[failed_check] += 1
            failures.append(
                {
                    "id": case.id,
                    "type": case.type,
                    "query": case.query,
                    "expected_authority_type": case.expected_authority_type,
                    "top1_source_required": case.top1_source_required,
                    "keyword_required": case.keyword_required,
                    "source_hit": source_ok,
                    "top1_source_hit": top1_source_ok,
                    "clause_hit": clause_ok,
                    "keyword_hit": keyword_ok,
                    "table_hit": table_ok,
                    "authority_hit": authority_ok,
                    "structured_table_hit": structured_ok,
                    "failed_checks": failed_checks,
                    "top_results": [
                        {
                            "source_file": result.meta.get("source_file") or result.meta.get("source"),
                            "clause_number": result.meta.get("clause_number"),
                            "matched_clause_number": result.meta.get("matched_clause_number"),
                            "section_type": result.meta.get("section_type"),
                            "table_id": result.meta.get("table_id"),
                            "reason": result.reason,
                            "score": result.score,
                        }
                        for result in results[:3]
                    ],
                    "top_structured_results": [
                        {
                            "table_id": match.table.get("source", {}).get("table_id"),
                            "table_name": match.table.get("source", {}).get("table_name"),
                            "reason": match.reason,
                            "score": match.score,
                        }
                        for match in structured_matches[:3]
                    ],
                }
            )

    total = len(cases)
    return {
        "case_count": total,
        "source_hit_rate": source_hits / total if total else 0,
        "top1_source_hit_rate": top1_source_hits / total if total else 0,
        "clause_hit_rate": clause_hits / total if total else 0,
        "keyword_hit_rate": keyword_hits / total if total else 0,
        "table_hit_rate": table_hits / total if total else 0,
        "authority_hit_rate": authority_hits / total if total else 0,
        "structured_case_count": structured_case_count,
        "structured_table_hit_rate": structured_hits / structured_case_count if structured_case_count else 1,
        "cases_by_type": cases_by_type,
        "failures_by_type": failures_by_type,
        "failures_by_check": failures_by_check,
        "failures": failures,
    }


def run_evaluation(
    path: Path = DEFAULT_EVAL_PATH,
    top_k: int = 5,
    *,
    state: RetrievalState | None = None,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    cases = load_cases(path)
    evaluation_state = state or retrieval_state
    requires_hybrid = any(case.type != "structured_table" for case in cases)
    if state is None and requires_hybrid and not evaluation_state.ready:
        evaluation_state.initialize()

    if requires_hybrid and not evaluation_state.ready:
        return {"ok": False, "error": "知识库检索服务未就绪，请先启动并完成 ChromaDB/ZhipuAI 初始化"}

    results_by_id = {
        case.id: evaluation_state.hybrid_search(case.query, top_k) if case.type != "structured_table" else []
        for case in cases
    }
    structured_by_id = {
        case.id: find_structured_table_matches(case.query, limit=top_k)
        for case in cases
        if case.expected_table_id
    }
    summary = summarize_results(cases, results_by_id, structured_by_id)
    manifest = (read_manifest(manifest_path) or {}) if manifest_path else read_active_manifest()
    data_version_hash = str(manifest.get("data_version_hash") or "")
    if not data_version_hash and cases and all(case.type == "structured_table" for case in cases):
        data_version_hash = structured_data_version_hash()
    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_set": str(path.resolve()),
        "evaluation_set_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
        "data_version_hash": data_version_hash,
        **summary,
    }


def render_evaluation_markdown(result: dict[str, Any], title: str = "检索评估报告") -> str:
    lines = [
        f"# {title}",
        "",
        f"- 用例数：{result.get('case_count', 0)}",
        f"- 来源命中率：{result.get('source_hit_rate', 0):.1%}",
        f"- 条文命中率：{result.get('clause_hit_rate', 0):.1%}",
        f"- 关键词命中率：{result.get('keyword_hit_rate', 0):.1%}",
        f"- 权威性命中率：{result.get('authority_hit_rate', 0):.1%}",
        f"- 结构化表命中率：{result.get('structured_table_hit_rate', 1):.1%}",
        f"- 失败数：{len(result.get('failures', []))}",
        "",
        "## 类型分布",
        "",
    ]
    for key, value in sorted(result.get("cases_by_type", {}).items()):
        lines.append(f"- `{key}`：{value}")
    lines.extend(["", "## 失败用例", ""])
    failures = result.get("failures", [])
    if not failures:
        lines.append("无失败用例。")
    for failure in failures:
        lines.extend(
            [
                f"### {failure.get('id', '')}",
                "",
                f"- 问题：{failure.get('query', '')}",
                f"- 失败检查：{', '.join(failure.get('failed_checks', []))}",
                "",
            ]
        )
    return "\n".join(lines) + "\n"

