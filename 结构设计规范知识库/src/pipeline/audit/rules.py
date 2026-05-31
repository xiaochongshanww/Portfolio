import json
import re
from pathlib import Path
from typing import Any

from src.pipeline.paths import AUDIT_DIR, PROCESSED_DIR


CLAUSE_RE = re.compile(r"\b\d+\.\d+(?:\.\d+)?(?:-\d+)?\b")
MOJIBAKE_RE = re.compile(r"[�□]{2,}")


def _finding(code: str, severity: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message, **extra}


def audit_elements(source_file: str, elements: list[dict[str, Any]], artifacts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    artifacts = artifacts or []
    findings: list[dict[str, Any]] = []
    total = len(elements)
    empty_count = sum(1 for element in elements if not str(element.get("text", "")).strip())
    page_values = sorted({int(element.get("page") or 0) for element in elements if int(element.get("page") or 0) > 0})
    missing_artifacts = [item for item in artifacts if item.get("status") != "ok"]

    if not total:
        findings.append(_finding("no_elements", "high", "未提取到任何元素"))
    if total and empty_count / total > 0.15:
        findings.append(_finding("high_empty_text_ratio", "medium", "空文本比例偏高", ratio=round(empty_count / total, 4)))
    if missing_artifacts:
        findings.append(
            _finding(
                "missing_artifacts",
                "high" if any(item.get("required") for item in missing_artifacts) else "medium",
                "MinerU 产物存在缺失",
                missing=[{"kind": item.get("kind"), "required": item.get("required")} for item in missing_artifacts],
            )
        )

    for index, element in enumerate(elements):
        text = str(element.get("text") or "")
        if len(text) > 6000:
            findings.append(_finding("oversized_element", "medium", "单个元素文本过长", element_index=index, length=len(text)))
        if MOJIBAKE_RE.search(text):
            findings.append(_finding("mojibake", "medium", "疑似乱码", element_index=index))
        if element.get("chunk_type") in {"table", "formula", "figure"} and not element.get("img") and not text.strip():
            findings.append(_finding("media_without_text_or_image", "high", "媒体元素缺少文本和图片引用", element_index=index))

    clauses = [CLAUSE_RE.search(str(element.get("text") or "")) for element in elements]
    clause_count = sum(1 for match in clauses if match)
    if total > 20 and clause_count == 0:
        findings.append(_finding("no_clause_numbers", "medium", "未识别到条文编号"))

    return {
        "source_file": source_file,
        "element_count": total,
        "page_count": len(page_values),
        "pages": page_values,
        "empty_text_ratio": round(empty_count / total, 4) if total else 0,
        "clause_count": clause_count,
        "finding_count": len(findings),
        "high_risk_count": sum(1 for item in findings if item["severity"] == "high"),
        "findings": findings,
    }


def audit_processed_documents(processed_dir: Path = PROCESSED_DIR) -> dict[str, Any]:
    documents = []
    for path in sorted(processed_dir.glob("*.json")):
        if path.name.endswith("_chunks.json") or path.name == "build_quality.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        documents.append(
            audit_elements(
                payload.get("source_file", path.name),
                payload.get("elements", payload if isinstance(payload, list) else []),
                payload.get("artifacts", []),
            )
        )
    return {
        "document_count": len(documents),
        "finding_count": sum(doc["finding_count"] for doc in documents),
        "high_risk_count": sum(doc["high_risk_count"] for doc in documents),
        "documents": documents,
    }


def write_audit_report(report: dict[str, Any], out_dir: Path = AUDIT_DIR) -> Path:
    report_dir = out_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "quality_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
