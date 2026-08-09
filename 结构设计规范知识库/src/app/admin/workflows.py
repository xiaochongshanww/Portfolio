import json
from pathlib import Path
from typing import Any

from src.app.core.config import settings
from src.app.retrieval.hybrid_search import retrieval_state
from src.evaluation.answer_runner import (
    render_answer_evaluation_markdown,
    run_answer_evaluation,
)
from src.evaluation.api_target import probe_api_readiness
from src.evaluation.assets import (
    ANSWER_EVALUATION_SET_IDS,
    RETRIEVAL_EVALUATION_SET_IDS,
    resolve_evaluation_asset,
)
from src.evaluation.runner import STRUCTURED_EVAL_PATH, render_evaluation_markdown, run_evaluation
from src.pipeline import builder
from src.pipeline.active_db import active_processed_dir, write_active_db
from src.pipeline.audit.manual_structuring import (
    build_manual_structuring_draft,
    list_manual_structuring_files,
    read_manual_structuring_file,
    write_manual_structuring_queue,
)
from src.pipeline.audit.structuring_ai import (
    generate_structuring_suggestion,
    read_structuring_suggestion,
)
from src.pipeline.manifest import write_manifest
from src.pipeline.paths import ACTIVE_DB_PATH, AUDIT_DIR, DB_VERSIONS_DIR, MANIFEST_PATH, RAW_DIR
from src.pipeline.version_retention import execute_cleanup_plan, retention_policy_from_settings
from src.quality import assess_candidate_activation, write_candidate_activation_artifacts

from .models import Job, utc_now
from .storage import JobStore


class CandidateActivationBlocked(RuntimeError):
    pass


class EvaluationExecutionFailed(RuntimeError):
    pass


def _snapshot_file(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


def _restore_file(path: Path, content: bytes | None) -> None:
    if content is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.rollback.tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _raise_evaluation_failure(
    job: Job,
    store: JobStore,
    result: dict[str, Any],
    *,
    default_error: str,
) -> None:
    error = str(result.get("error") or default_error)
    job.outputs = result
    store.save(job)
    store.append_log(
        job.job_id,
        "error",
        error,
        report_path=result.get("report_path", ""),
    )
    raise EvaluationExecutionFailed(error)


def _set_step(job: Job, store: JobStore, step: str, message: str, **progress: Any) -> None:
    job.step = step
    job.progress = {"message": message, **progress}
    job.progress_at = utc_now()
    store.save(job)
    store.append_log(job.job_id, "info", message, step=step, progress=job.progress)


def dry_run_workflow(job: Job, store: JobStore) -> dict[str, Any]:
    source = Path(job.params.get("source", RAW_DIR))
    parser_backend = str(job.params.get("parser_backend", builder.DEFAULT_PARSER_BACKEND))
    _set_step(job, store, "dry_run", "检查待处理 PDF")
    return builder.dry_run(source, parser_backend=parser_backend)


def rebuild_workflow(job: Job, store: JobStore) -> dict[str, Any]:
    source = Path(job.params.get("source", RAW_DIR))
    parser_backend = str(job.params.get("parser_backend", builder.DEFAULT_PARSER_BACKEND))
    apply_corrections = bool(job.params.get("apply_corrections", True))
    _set_step(
        job, store, "rebuild", "开始重建知识库", source=str(source), parser_backend=parser_backend
    )
    version_dir = DB_VERSIONS_DIR / job.job_id
    db_dir = version_dir / "db"
    processed_dir = version_dir / "processed"
    images_dir = version_dir / "images"
    mineru_dir = version_dir / "mineru"
    audit_dir = version_dir / "audit"
    quality_dir = version_dir / "quality"
    manifest_path = version_dir / "manifest.json"
    _set_step(job, store, "build_version", "构建到临时版本目录", db_dir=str(db_dir))
    manifest = builder.rebuild(
        source,
        parser_backend=parser_backend,
        apply_corrections=apply_corrections,
        db_dir=db_dir,
        manifest_path=manifest_path,
        processed_dir=processed_dir,
        images_dir=images_dir,
        mineru_output_dir=mineru_dir,
        audit_dir=audit_dir,
    )
    _set_step(
        job,
        store,
        "candidate_gate",
        "验证候选运行时并执行预激活评估",
        regular_cases=100,
        structured_cases=12,
    )
    assessment = assess_candidate_activation(
        manifest_path=manifest_path,
        db_dir=db_dir,
        processed_dir=processed_dir,
        images_dir=images_dir,
    )
    gate_artifacts = write_candidate_activation_artifacts(assessment, quality_dir)
    if not assessment.result["passed"] or assessment.retrieval_state is None:
        failed = ", ".join(assessment.result.get("failed_checks", [])) or "candidate_runtime"
        store.append_log(
            job.job_id,
            "error",
            "候选版本未通过预激活门禁，旧活动版本保持不变",
            failed_checks=assessment.result.get("failed_checks", []),
            gate_report=gate_artifacts["gate_report"],
        )
        raise CandidateActivationBlocked(f"候选版本未通过预激活门禁: {failed}")

    pointer_payload = {
        "active_db_dir": str(db_dir),
        "processed_dir": str(processed_dir),
        "images_dir": str(images_dir),
        "mineru_dir": str(mineru_dir),
        "audit_dir": str(audit_dir),
        "manifest": str(manifest_path),
        "job_id": job.job_id,
        "data_version_hash": manifest.get("data_version_hash", ""),
        "chunk_count": manifest.get("chunk_count", 0),
        "activated_at": assessment.result.get("generated_at", ""),
        "candidate_gate_report": gate_artifacts["gate_report"],
    }
    old_manifest = _snapshot_file(MANIFEST_PATH)
    old_pointer = _snapshot_file(ACTIVE_DB_PATH)
    _set_step(job, store, "activate_version", "提交候选版本并切换活动指针", db_dir=str(db_dir))
    try:
        write_manifest(MANIFEST_PATH, manifest)
        write_active_db(pointer_payload, ACTIVE_DB_PATH)
        retrieval_state.adopt(assessment.retrieval_state)
    except Exception:
        _restore_file(ACTIVE_DB_PATH, old_pointer)
        _restore_file(MANIFEST_PATH, old_manifest)
        raise

    reports_dir = AUDIT_DIR / "reports"
    latest_reports_published = True
    try:
        _write_json_atomic(reports_dir / "evaluation_latest.json", assessment.regular_evaluation)
        _write_json_atomic(
            reports_dir / "evaluation_structured_latest.json", assessment.structured_evaluation
        )
    except Exception as exc:
        latest_reports_published = False
        store.append_log(
            job.job_id,
            "warning",
            "活动版本已切换，但最新检索评估报告发布失败；完整发布门禁将保持阻断",
            error=str(exc),
        )
    try:
        write_manual_structuring_queue(processed_dir)
    except Exception as exc:
        store.append_log(
            job.job_id,
            "warning",
            "活动版本已切换，但复杂表人工队列刷新失败",
            error=str(exc),
        )
    _set_step(job, store, "active", "候选版本已通过门禁并成为活动版本", db_dir=str(db_dir))
    return {
        "manifest": str(MANIFEST_PATH),
        "version_manifest": str(manifest_path),
        "active_db": str(db_dir),
        "document_count": manifest.get("document_count", 0),
        "chunk_count": manifest.get("chunk_count", 0),
        "image_count": manifest.get("image_count", 0),
        "data_version_hash": manifest.get("data_version_hash", ""),
        "applied_correction_count": manifest.get("correction_status", {}).get("applied_count", 0),
        "candidate_gate": assessment.result,
        "candidate_gate_report": gate_artifacts["gate_report"],
        "answer_evaluation_required": True,
        "latest_reports_published": latest_reports_published,
    }


def cleanup_versions_workflow(job: Job, store: JobStore) -> dict[str, Any]:
    plan_id = str(job.params.get("plan_id") or "")
    _set_step(job, store, "validate_plan", "重新核对清理计划与受保护版本", plan_id=plan_id)
    result = execute_cleanup_plan(
        plan_id,
        policy=retention_policy_from_settings(settings),
        jobs=store.list(),
    )
    if result.get("failed_count", 0):
        store.append_log(
            job.job_id,
            "error",
            "知识版本清理部分失败，详情保留在执行报告",
            plan_id=plan_id,
            failed_count=result.get("failed_count", 0),
            report_path=result.get("report_path", ""),
        )
        raise RuntimeError(
            f"知识版本清理部分失败: {result.get('failed_count', 0)} 个版本；"
            f"报告 {result.get('report_path', '')}"
        )
    _set_step(
        job,
        store,
        "cleanup_versions",
        "知识版本清理完成",
        plan_id=plan_id,
        deleted_count=result.get("deleted_count", 0),
        skipped_count=result.get("skipped_count", 0),
        failed_count=result.get("failed_count", 0),
    )
    return result


def audit_workflow(job: Job, store: JobStore) -> dict[str, Any]:
    _set_step(job, store, "audit", "开始规则审计")
    report = builder.audit(active_processed_dir())
    return {
        "report_path": report.get("report_path", ""),
        "document_count": report.get("document_count", 0),
        "finding_count": report.get("finding_count", 0),
        "high_risk_count": report.get("high_risk_count", 0),
    }


def review_workflow(job: Job, store: JobStore) -> dict[str, Any]:
    doc = str(job.params.get("doc", ""))
    pages = str(job.params.get("pages", ""))
    _set_step(job, store, "review", "开始 AI 校对", doc=doc, pages=pages)
    return builder.review(doc, pages=pages, processed_dir=active_processed_dir())


def structuring_suggestion_workflow(job: Job, store: JobStore) -> dict[str, Any]:
    doc = str(job.params.get("doc", ""))
    item_id = str(job.params.get("item_id", ""))
    _set_step(job, store, "render", "渲染复杂表来源页面", doc=doc, item_id=item_id)
    _set_step(job, store, "generate", "调用多模态模型生成结构化建议", doc=doc, item_id=item_id)
    result = generate_structuring_suggestion(doc, item_id)
    _set_step(
        job,
        store,
        "save_suggestion",
        "结构化建议已保存，等待人工应用",
        row_count=result.get("row_count", 0),
        confidence=result.get("confidence", 0),
    )
    return result


def structuring_suggestion_batch_workflow(job: Job, store: JobStore) -> dict[str, Any]:
    force = bool(job.params.get("force", False))
    requested_docs = {str(value) for value in job.params.get("documents", []) if str(value)}
    tasks: list[tuple[str, str]] = []
    for summary in list_manual_structuring_files():
        doc = str(summary["doc"])
        if requested_docs and doc not in requested_docs:
            continue
        detail = read_manual_structuring_file(doc)
        seen: set[str] = set()
        for item in detail.get("items", []):
            owner_id = str(item.get("group_primary_item_id") or item.get("id"))
            if owner_id in seen or item.get("review_status", "pending") != "pending":
                continue
            seen.add(owner_id)
            tasks.append((doc, owner_id))

    completed = 0
    skipped = 0
    failures: list[dict[str, str]] = []
    outputs: list[dict[str, Any]] = []
    for index, (doc, item_id) in enumerate(tasks, start=1):
        _set_step(
            job,
            store,
            "batch_generate",
            f"生成结构化建议 {index}/{len(tasks)}",
            completed=completed,
            skipped=skipped,
            failed=len(failures),
            doc=doc,
            item_id=item_id,
        )
        try:
            build_manual_structuring_draft(doc, item_id)
            if not force:
                try:
                    existing = read_structuring_suggestion(doc, item_id)
                    if not existing.get("stale"):
                        skipped += 1
                        continue
                except FileNotFoundError:
                    pass
            result = generate_structuring_suggestion(doc, item_id)
            outputs.append({"doc": doc, "item_id": item_id, **result})
            completed += 1
        except Exception as exc:
            failures.append({"doc": doc, "item_id": item_id, "error": str(exc)})
            store.append_log(job.job_id, "error", str(exc), doc=doc, item_id=item_id)
    return {
        "task_count": len(tasks),
        "completed_count": completed,
        "skipped_count": skipped,
        "failed_count": len(failures),
        "failures": failures,
        "suggestions": outputs,
    }


def evaluate_workflow(job: Job, store: JobStore) -> dict[str, Any]:
    top_k = int(job.params.get("top_k", 5))
    evaluation_set_id = str(job.params.get("evaluation_set", "regular"))
    eval_file = resolve_evaluation_asset(
        evaluation_set_id,
        allowed_ids=RETRIEVAL_EVALUATION_SET_IDS,
    )
    _set_step(
        job,
        store,
        "evaluate",
        "开始检索评估",
        top_k=top_k,
        evaluation_set=evaluation_set_id,
    )
    result = {
        **run_evaluation(eval_file, top_k=top_k),
        "evaluation_set_id": evaluation_set_id,
    }
    out_dir = AUDIT_DIR / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    is_structured = eval_file.resolve() == STRUCTURED_EVAL_PATH.resolve()
    stem = "evaluation_structured_latest" if is_structured else "evaluation_latest"
    out_path = out_dir / f"{stem}.json"
    markdown_path = out_dir / f"{stem}.md"
    import json

    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(
        render_evaluation_markdown(
            result, "结构化检索专项评估" if is_structured else "检索评估报告"
        ),
        encoding="utf-8",
    )
    output = {
        **result,
        "report_path": str(out_path),
        "markdown_report_path": str(markdown_path),
    }
    if result.get("ok") is not True:
        _raise_evaluation_failure(
            job,
            store,
            output,
            default_error="检索评估执行失败",
        )
    return output


def answer_evaluate_workflow(job: Job, store: JobStore) -> dict[str, Any]:
    evaluation_set_id = str(job.params.get("evaluation_set", "answer"))
    eval_file = resolve_evaluation_asset(
        evaluation_set_id,
        allowed_ids=ANSWER_EVALUATION_SET_IDS,
    )
    api_base = settings.answer_evaluation_api_base
    api_key = settings.api_keys[0] if settings.api_keys else ""

    def update_progress(completed: int, total: int, result: dict[str, Any]) -> None:
        _set_step(
            job,
            store,
            "answer_evaluate",
            f"回答级盲测 {completed}/{total}",
            completed=completed,
            total=total,
            latest_case=result.get("id"),
            latest_passed=result.get("passed"),
        )

    _set_step(
        job,
        store,
        "answer_target_readiness",
        "检查回答盲测目标 API",
        api_base=api_base,
    )
    readiness = probe_api_readiness(api_base)
    if readiness.get("ok"):
        _set_step(
            job,
            store,
            "answer_evaluate",
            "开始回答级盲测",
            evaluation_set=evaluation_set_id,
        )
        result = run_answer_evaluation(
            api_base=api_base,
            api_key=api_key,
            path=eval_file,
            progress_callback=update_progress,
        )
        result["readiness"] = readiness
    else:
        result = {
            "ok": False,
            "api_base": api_base,
            "case_count": 0,
            "passed_count": 0,
            "failure_count": 0,
            "pass_rate": 0,
            "check_rates": {},
            "refusal_pass_rate": 0,
            "failures": [],
            "results": [],
            "readiness": readiness,
            "error": readiness.get("error") or "回答盲测目标 API 未就绪",
        }
    result["evaluation_set_id"] = evaluation_set_id
    out_dir = AUDIT_DIR / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "evaluation_answer_latest.json"
    markdown_path = out_dir / "evaluation_answer_latest.md"
    import json

    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_answer_evaluation_markdown(result), encoding="utf-8")
    output = {
        **result,
        "report_path": str(out_path),
        "markdown_report_path": str(markdown_path),
    }
    if result.get("ok") is not True:
        _raise_evaluation_failure(
            job,
            store,
            output,
            default_error="回答级盲测执行失败",
        )
    return output
