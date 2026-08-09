from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.app.core.config import Settings, settings
from src.app.retrieval.hybrid_search import RetrievalState
from src.evaluation.runner import DEFAULT_EVAL_PATH, STRUCTURED_EVAL_PATH, run_evaluation
from src.pipeline.manifest import read_manifest

from .gate import (
    MIN_AUTHORITY_HIT_RATE,
    MIN_REGULAR_CASES,
    MIN_STRUCTURED_CASES,
    MIN_STRUCTURED_TABLE_HIT_RATE,
    MIN_TOP1_SOURCE_HIT_RATE,
)


@dataclass(frozen=True)
class CandidateActivationAssessment:
    result: dict[str, Any]
    retrieval_state: RetrievalState | None
    regular_evaluation: dict[str, Any]
    structured_evaluation: dict[str, Any]


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def assess_candidate_activation(
    *,
    manifest_path: Path,
    db_dir: Path,
    processed_dir: Path | None = None,
    images_dir: Path | None = None,
    config: Settings = settings,
    regular_eval_path: Path = DEFAULT_EVAL_PATH,
    structured_eval_path: Path = STRUCTURED_EVAL_PATH,
    top_k: int = 5,
) -> CandidateActivationAssessment:
    manifest = read_manifest(manifest_path) or {}
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, message: str, **details: Any) -> None:
        checks.append(
            {
                "name": name,
                "status": "passed" if passed else "failed",
                "severity": "info" if passed else "blocking",
                "message": message,
                "details": details,
            }
        )

    data_version = str(manifest.get("data_version_hash") or "")
    check(
        "manifest",
        bool(manifest),
        "候选版本 manifest 可读取" if manifest else "缺少候选版本 manifest",
    )
    check(
        "data_version",
        bool(data_version),
        "候选版本具有数据版本哈希" if data_version else "候选版本缺少数据版本哈希",
    )
    document_count = int(manifest.get("document_count", 0))
    chunk_count = int(manifest.get("chunk_count", 0))
    check(
        "knowledge_base",
        document_count > 0 and chunk_count > 0,
        f"候选知识库包含 {document_count} 份文档、{chunk_count} 个 chunk",
    )
    check(
        "collection_contract",
        manifest.get("collection_name") == config.collection_name,
        "候选集合名称与运行配置一致",
        manifest_collection=manifest.get("collection_name"),
        runtime_collection=config.collection_name,
    )
    check(
        "embedding_contract",
        manifest.get("embedding_model") == config.embedding_model,
        "候选向量模型与运行配置一致",
        manifest_embedding=manifest.get("embedding_model"),
        runtime_embedding=config.embedding_model,
    )
    missing_required = int(manifest.get("artifact_status", {}).get("missing_required_count", 0))
    check("required_artifacts", missing_required == 0, f"缺失必需产物 {missing_required} 项")
    high_risk = int(manifest.get("audit_status", {}).get("high_risk_count", 0))
    check("high_risk_audit", high_risk == 0, f"高风险审计项 {high_risk} 项")
    if processed_dir is not None:
        processed_chunks = (
            list(processed_dir.glob("*_chunks.json")) if processed_dir.is_dir() else []
        )
        quality_report = processed_dir / "build_quality.json"
        check(
            "processed_assets",
            len(processed_chunks) == document_count and quality_report.is_file(),
            f"候选解析目录包含 {len(processed_chunks)} 份 chunk 文件，期望 {document_count} 份",
            processed_dir=str(processed_dir),
            build_quality_exists=quality_report.is_file(),
        )
    if images_dir is not None:
        image_files = (
            [path for path in images_dir.glob("*") if path.is_file()] if images_dir.is_dir() else []
        )
        expected_images = int(manifest.get("image_count", 0))
        check(
            "image_assets",
            len(image_files) == expected_images,
            f"候选图片目录包含 {len(image_files)} 个文件，manifest {expected_images} 个",
            images_dir=str(images_dir),
        )

    candidate_state: RetrievalState | None = None
    state_error = ""
    try:
        candidate_state = RetrievalState.load_candidate(db_dir, config)
    except Exception as exc:
        state_error = str(exc)
    state_ready = bool(candidate_state and candidate_state.ready)
    runtime_count = candidate_state.chroma_count() if candidate_state else -1
    check(
        "candidate_runtime",
        state_ready,
        "候选检索状态可独立加载"
        if state_ready
        else f"候选检索状态不可用: {state_error or 'embedding 或 collection 未就绪'}",
    )
    check(
        "runtime_collection",
        runtime_count == chunk_count and chunk_count > 0,
        f"候选集合 {runtime_count} 条，manifest {chunk_count} 条",
    )

    try:
        regular = (
            run_evaluation(
                regular_eval_path,
                top_k=top_k,
                state=candidate_state,
                manifest_path=manifest_path,
            )
            if candidate_state
            else {"ok": False, "error": state_error or "candidate retrieval state unavailable"}
        )
    except Exception as exc:
        regular = {"ok": False, "error": str(exc), "failures": []}
    regular_failures = len(regular.get("failures", []))
    regular_ok = (
        regular.get("ok") is True
        and int(regular.get("case_count", 0)) >= MIN_REGULAR_CASES
        and regular_failures == 0
        and float(regular.get("top1_source_hit_rate", 0)) >= MIN_TOP1_SOURCE_HIT_RATE
        and float(regular.get("authority_hit_rate", 0)) >= MIN_AUTHORITY_HIT_RATE
        and regular.get("data_version_hash") == data_version
        and regular.get("evaluation_set_hash") == _file_hash(regular_eval_path)
    )
    check(
        "regular_evaluation",
        regular_ok,
        f"候选常规评估 {regular.get('case_count', 0)} 项，失败 {regular_failures} 项",
        error=regular.get("error"),
        top1_source_hit_rate=regular.get("top1_source_hit_rate"),
        authority_hit_rate=regular.get("authority_hit_rate"),
    )

    try:
        structured = run_evaluation(
            structured_eval_path,
            top_k=top_k,
            state=candidate_state,
            manifest_path=manifest_path,
        )
    except Exception as exc:
        structured = {"ok": False, "error": str(exc), "failures": []}
    structured_failures = len(structured.get("failures", []))
    structured_ok = (
        structured.get("ok") is True
        and int(structured.get("case_count", 0)) >= MIN_STRUCTURED_CASES
        and structured_failures == 0
        and float(structured.get("structured_table_hit_rate", 0)) >= MIN_STRUCTURED_TABLE_HIT_RATE
        and structured.get("data_version_hash") == data_version
        and structured.get("evaluation_set_hash") == _file_hash(structured_eval_path)
    )
    check(
        "structured_evaluation",
        structured_ok,
        f"候选结构化评估 {structured.get('case_count', 0)} 项，失败 {structured_failures} 项",
        error=structured.get("error"),
        structured_table_hit_rate=structured.get("structured_table_hit_rate"),
    )

    failed_checks = [item["name"] for item in checks if item["status"] == "failed"]
    result = {
        "schema_version": 1,
        "gate": "candidate_activation",
        "generated_at": datetime.now(UTC).isoformat(),
        "passed": not failed_checks,
        "failed_checks": failed_checks,
        "checks": checks,
        "data_version_hash": data_version,
        "manifest_path": str(manifest_path),
        "db_dir": str(db_dir),
        "regular_evaluation_set": str(regular_eval_path),
        "structured_evaluation_set": str(structured_eval_path),
        "answer_evaluation_included": False,
        "answer_evaluation_note": "回答级盲测依赖隔离 API 与 LLM，继续由发布质量门禁独立执行。",
    }
    return CandidateActivationAssessment(result, candidate_state, regular, structured)


def write_candidate_activation_artifacts(
    assessment: CandidateActivationAssessment,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "gate_report": output_dir / "candidate_activation_gate.json",
        "gate_markdown": output_dir / "candidate_activation_gate.md",
        "regular_report": output_dir / "evaluation_regular.json",
        "structured_report": output_dir / "evaluation_structured.json",
    }
    payloads = {
        "gate_report": assessment.result,
        "regular_report": assessment.regular_evaluation,
        "structured_report": assessment.structured_evaluation,
    }
    for key, payload in payloads.items():
        paths[key].write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["gate_markdown"].write_text(
        render_candidate_activation_markdown(assessment.result), encoding="utf-8"
    )
    return {key: str(path) for key, path in paths.items()}


def render_candidate_activation_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 候选版本预激活门禁报告",
        "",
        f"- 结论：{'通过' if result.get('passed') else '未通过'}",
        f"- 生成时间：{result.get('generated_at', '-')}",
        f"- 数据版本：`{result.get('data_version_hash') or '-'}`",
        "- 范围：候选运行时、常规检索与结构化检索；不包含回答级盲测。",
        "",
        "## 检查项",
        "",
        "| 检查 | 状态 | 说明 |",
        "| --- | --- | --- |",
    ]
    for item in result.get("checks", []):
        lines.append(f"| `{item.get('name')}` | {item.get('status')} | {item.get('message', '')} |")
    lines.append("")
    return "\n".join(lines)
