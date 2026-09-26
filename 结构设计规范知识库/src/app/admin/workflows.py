import hashlib
import logging
import re
import shutil
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.app.core.config import settings
from src.app.core.job_cancellation import (
    job_cancellation_safe_section,
    raise_if_job_cancelled,
)
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
from src.evaluation.management import published_revision_id
from src.evaluation.runner import render_evaluation_markdown, run_evaluation
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
from src.pipeline.manifest import read_manifest, write_manifest
from src.pipeline.paths import ACTIVE_DB_PATH, AUDIT_DIR, DB_VERSIONS_DIR, MANIFEST_PATH, RAW_DIR
from src.pipeline.version_retention import execute_cleanup_plan, retention_policy_from_settings
from src.quality import (
    assess_candidate_activation,
    atomic_write_json,
    current_evidence_context,
    validate_verification_run_id,
    write_candidate_activation_artifacts,
    write_quality_report,
)

from .models import Job, utc_now
from .source_management import source_catalog_store
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
    job.progress = {"stage": step, "message": message, **progress}
    job.progress_at = utc_now()
    store.save(job)
    store.append_log(job.job_id, "info", message, step=step, progress=job.progress)


class _JobProgressReporter:
    """Persist structured pipeline progress without writing one record per parser line."""

    def __init__(self, job: Job, store: JobStore, *, min_interval_seconds: float = 1.0):
        self.job = job
        self.store = store
        self.min_interval_seconds = min_interval_seconds
        self._last_emit_at = 0.0
        self._last_step = ""

    def __call__(self, step: str, message: str, details: dict[str, Any]) -> None:
        raise_if_job_cancelled()
        now = time.monotonic()
        if step == self._last_step and now - self._last_emit_at < self.min_interval_seconds:
            return
        self._last_emit_at = now
        self._last_step = step
        _set_step(self.job, self.store, step, message, **details)


def dry_run_workflow(job: Job, store: JobStore) -> dict[str, Any]:
    source = Path(job.params.get("source", RAW_DIR))
    metadata_path = Path(job.params.get("metadata_path", settings.source_metadata_path))
    parser_backend = str(job.params.get("parser_backend", builder.DEFAULT_PARSER_BACKEND))
    _set_step(job, store, "dry_run", "检查待处理 PDF")
    return builder.dry_run(source, parser_backend=parser_backend, metadata_path=metadata_path)


def _activate_candidate_version(
    job: Job,
    store: JobStore,
    *,
    version_dir: Path,
    manifest: dict[str, Any],
    source_catalog_revision: str,
    rebuild_mode: str,
    version_job_id: str,
) -> dict[str, Any]:
    """Gate and atomically activate an already assembled candidate version."""
    db_dir = version_dir / "db"
    processed_dir = version_dir / "processed"
    images_dir = version_dir / "images"
    mineru_dir = version_dir / "mineru"
    audit_dir = version_dir / "audit"
    quality_dir = version_dir / "quality"
    manifest_path = version_dir / "manifest.json"

    _set_step(
        job,
        store,
        "candidate_gate",
        "验证候选运行时并执行预激活评估",
        regular_cases=100,
        structured_cases=12,
        candidate_job_id=version_job_id,
    )
    assessment = assess_candidate_activation(
        manifest_path=manifest_path,
        db_dir=db_dir,
        processed_dir=processed_dir,
        images_dir=images_dir,
    )
    gate_artifacts = write_candidate_activation_artifacts(assessment, quality_dir)
    raise_if_job_cancelled()
    if not assessment.result["passed"] or assessment.retrieval_state is None:
        failed = ", ".join(assessment.result.get("failed_checks", [])) or "candidate_runtime"
        store.append_log(
            job.job_id,
            "error",
            "候选版本未通过预激活门禁，旧活动版本保持不变",
            failed_checks=assessment.result.get("failed_checks", []),
            gate_report=gate_artifacts["gate_report"],
        )
        error = f"候选版本未通过预激活门禁: {failed}"
        if source_catalog_revision:
            source_catalog_store.fail_revision(source_catalog_revision, error)
        raise CandidateActivationBlocked(error)

    pointer_payload = {
        "active_db_dir": str(db_dir),
        "processed_dir": str(processed_dir),
        "images_dir": str(images_dir),
        "mineru_dir": str(mineru_dir),
        "audit_dir": str(audit_dir),
        "manifest": str(manifest_path),
        "job_id": version_job_id,
        "activation_job_id": job.job_id,
        "data_version_hash": manifest.get("data_version_hash", ""),
        "chunk_count": manifest.get("chunk_count", 0),
        "activated_at": assessment.result.get("generated_at", ""),
        "candidate_gate_report": gate_artifacts["gate_report"],
        "source_catalog_revision": source_catalog_revision,
    }
    with job_cancellation_safe_section():
        old_manifest = _snapshot_file(MANIFEST_PATH)
        old_pointer = _snapshot_file(ACTIVE_DB_PATH)
        old_retrieval_state = retrieval_state.snapshot()
        _set_step(
            job,
            store,
            "activate_version",
            "提交候选版本并切换活动指针",
            db_dir=str(db_dir),
            candidate_job_id=version_job_id,
        )
        try:
            write_manifest(MANIFEST_PATH, manifest)
            write_active_db(pointer_payload, ACTIVE_DB_PATH)
            retrieval_state.adopt(assessment.retrieval_state)
            if source_catalog_revision:
                source_catalog_store.activate_revision(
                    source_catalog_revision, str(manifest.get("data_version_hash", ""))
                )
        except Exception:
            _restore_file(ACTIVE_DB_PATH, old_pointer)
            _restore_file(MANIFEST_PATH, old_manifest)
            retrieval_state.restore(old_retrieval_state)
            if source_catalog_revision:
                try:
                    source_catalog_store.fail_revision(
                        source_catalog_revision, "候选版本激活失败，已恢复旧在线版本"
                    )
                except Exception:
                    logging.exception("source_revision_failure_status_update_failed")
            raise

    cache_index = ""
    try:
        from src.pipeline.incremental import publish_cache_index

        cache_index = str(publish_cache_index(manifest, manifest.get("incremental_plan", {})))
    except Exception as exc:
        store.append_log(
            job.job_id,
            "warning",
            "活动版本已切换，但增量缓存索引发布失败；下次将安全回退或重新处理",
            error=str(exc),
        )

    reports_dir = AUDIT_DIR / "reports"
    latest_reports_published = True
    try:
        atomic_write_json(reports_dir / "evaluation_latest.json", assessment.regular_evaluation)
        atomic_write_json(
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
    _set_step(
        job,
        store,
        "active",
        "候选版本已通过门禁并成为活动版本",
        db_dir=str(db_dir),
        candidate_job_id=version_job_id,
    )
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
        "rebuild_mode": manifest.get("build_params", {}).get("mode", rebuild_mode),
        "incremental_plan": manifest.get("incremental_plan", {}),
        "cache_index": cache_index,
        "source_catalog_revision": source_catalog_revision,
        "candidate_job_id": version_job_id,
        "activation_job_id": job.job_id,
        "parsing_reused": True,
    }


def rebuild_workflow(job: Job, store: JobStore) -> dict[str, Any]:
    source = Path(job.params.get("source", RAW_DIR))
    parser_backend = str(job.params.get("parser_backend", builder.DEFAULT_PARSER_BACKEND))
    apply_corrections = bool(job.params.get("apply_corrections", True))
    rebuild_mode = str(job.params.get("mode", "full"))
    metadata_path = Path(job.params.get("metadata_path", settings.source_metadata_path))
    source_catalog_revision = str(job.params.get("source_catalog_revision", ""))
    progress = _JobProgressReporter(job, store)
    _set_step(
        job,
        store,
        "rebuild",
        "开始重建知识库",
        source=str(source),
        parser_backend=parser_backend,
        mode=rebuild_mode,
    )
    version_dir = DB_VERSIONS_DIR / job.job_id
    db_dir = version_dir / "db"
    processed_dir = version_dir / "processed"
    images_dir = version_dir / "images"
    mineru_dir = version_dir / "mineru"
    audit_dir = version_dir / "audit"
    manifest_path = version_dir / "manifest.json"
    _set_step(job, store, "build_version", "构建到临时版本目录", db_dir=str(db_dir))
    build_kwargs = {
        "parser_backend": parser_backend,
        "apply_corrections": apply_corrections,
        "db_dir": db_dir,
        "manifest_path": manifest_path,
        "processed_dir": processed_dir,
        "images_dir": images_dir,
        "mineru_output_dir": mineru_dir,
        "audit_dir": audit_dir,
        "metadata_path": metadata_path,
        "source_catalog_revision": source_catalog_revision,
    }
    try:
        if rebuild_mode == "incremental":
            manifest = builder.incremental_rebuild(
                source,
                requested_mode=rebuild_mode,
                progress_callback=progress,
                **build_kwargs,
            )
        else:
            manifest = builder.rebuild(
                source,
                build_mode="full",
                progress_callback=progress,
                **build_kwargs,
            )
    except Exception as exc:
        if source_catalog_revision:
            source_catalog_store.fail_revision(source_catalog_revision, str(exc))
        raise
    return _activate_candidate_version(
        job,
        store,
        version_dir=version_dir,
        manifest=manifest,
        source_catalog_revision=source_catalog_revision,
        rebuild_mode=rebuild_mode,
        version_job_id=job.job_id,
    )


def republish_candidate_workflow(job: Job, store: JobStore) -> dict[str, Any]:
    """Re-validate and publish an existing candidate without invoking the parser."""
    candidate_job_id = str(job.params.get("candidate_job_id") or "")
    source_catalog_revision = str(job.params.get("source_catalog_revision") or "")
    if not candidate_job_id or not source_catalog_revision:
        raise RuntimeError("候选重试发布缺少 candidate_job_id 或 source_catalog_revision")

    source_catalog_store.validate_republish_revision(source_catalog_revision)
    version_dir = DB_VERSIONS_DIR / candidate_job_id
    manifest_path = version_dir / "manifest.json"
    manifest = read_manifest(manifest_path)
    if not manifest:
        raise RuntimeError(f"候选版本 manifest 不存在: {manifest_path}")
    recorded_revision = str(manifest.get("build_params", {}).get("source_catalog_revision") or "")
    if recorded_revision != source_catalog_revision:
        raise RuntimeError("候选版本与来源 revision 不一致，拒绝发布")

    _set_step(
        job,
        store,
        "candidate_revalidate",
        "重新验证已有候选版本（不重新解析）",
        candidate_job_id=candidate_job_id,
        source_catalog_revision=source_catalog_revision,
    )
    return _activate_candidate_version(
        job,
        store,
        version_dir=version_dir,
        manifest=manifest,
        source_catalog_revision=source_catalog_revision,
        rebuild_mode="candidate_republish",
        version_job_id=candidate_job_id,
    )


def revalidate_candidate_workflow(job: Job, store: JobStore) -> dict[str, Any]:
    """Assess a failed candidate without changing its status or the active version."""
    candidate_job_id = str(job.params.get("candidate_job_id") or "")
    source_catalog_revision = str(job.params.get("source_catalog_revision") or "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", candidate_job_id):
        raise RuntimeError("候选复核缺少有效的 candidate_job_id")
    if not source_catalog_revision:
        raise RuntimeError("候选复核缺少 source_catalog_revision")

    original = store.read(candidate_job_id)
    if (
        not original
        or original.get("type") != "source_rebuild"
        or original.get("status") != "failed"
    ):
        raise RuntimeError("仅支持复核仍处于失败状态的来源候选任务")
    original_params = original.get("params") if isinstance(original.get("params"), dict) else {}
    if str(original_params.get("source_catalog_revision") or "") != source_catalog_revision:
        raise RuntimeError("候选任务与来源 revision 不一致")

    source_snapshot = source_catalog_store.validate_republish_revision(source_catalog_revision)
    versions_root = DB_VERSIONS_DIR.resolve()
    candidate_root = (versions_root / candidate_job_id).resolve(strict=True)
    if not candidate_root.is_relative_to(versions_root):
        raise RuntimeError("候选版本目录越界")
    manifest_path = (candidate_root / "manifest.json").resolve(strict=True)
    if not manifest_path.is_relative_to(candidate_root):
        raise RuntimeError("候选 manifest 路径越界")
    manifest_bytes = manifest_path.read_bytes()
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    manifest = read_manifest(manifest_path)
    if not manifest:
        raise RuntimeError("候选版本 manifest 不存在")
    build_params = manifest.get("build_params")
    recorded_revision = (
        str(build_params.get("source_catalog_revision") or "")
        if isinstance(build_params, dict)
        else ""
    )
    if recorded_revision != source_catalog_revision:
        raise RuntimeError("候选版本与来源 revision 不一致")

    def evaluation_snapshot(set_id: str) -> tuple[Path, str, str]:
        path = resolve_evaluation_asset(set_id, allowed_ids=frozenset({set_id})).resolve(
            strict=True
        )
        return path, hashlib.sha256(path.read_bytes()).hexdigest(), published_revision_id(set_id)

    before_evaluations = {
        set_id: evaluation_snapshot(set_id) for set_id in ("regular", "structured")
    }
    _set_step(
        job,
        store,
        "candidate_revalidate",
        "仅复核已有候选（不重新解析、不发布）",
        candidate_job_id=candidate_job_id,
        source_catalog_revision=source_catalog_revision,
        regular_cases=100,
        structured_cases=12,
    )
    assessment = assess_candidate_activation(
        manifest_path=manifest_path,
        db_dir=candidate_root / "db",
        processed_dir=candidate_root / "processed",
        images_dir=candidate_root / "images",
    )
    if assessment.result.get("data_version_hash") != manifest.get("data_version_hash"):
        raise RuntimeError("复核门禁结果与候选数据版本不一致，报告未保存")
    assessment.result["report_source"] = "revalidation"
    assessment.result["revalidation_job_id"] = job.job_id
    assessment.result["candidate_job_id"] = candidate_job_id

    revalidations_root = candidate_root / "quality" / "revalidations"
    revalidations_root.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=".pending-", dir=revalidations_root))
    try:
        artifacts = write_candidate_activation_artifacts(assessment, staging_dir)

        current_manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        if current_manifest_hash != manifest_hash:
            raise RuntimeError("候选 manifest 在复核期间发生变化，报告未保存")
        current_source_snapshot = source_catalog_store.validate_republish_revision(
            source_catalog_revision
        )
        if current_source_snapshot != source_snapshot:
            raise RuntimeError("来源 revision 在复核期间发生变化，报告未保存")
        latest_original = store.read(candidate_job_id)
        latest_original_params = (
            latest_original.get("params") if isinstance(latest_original, dict) else None
        )
        if (
            not isinstance(latest_original, dict)
            or latest_original.get("type") != "source_rebuild"
            or latest_original.get("status") != "failed"
            or not isinstance(latest_original_params, dict)
            or str(latest_original_params.get("source_catalog_revision") or "")
            != source_catalog_revision
        ):
            raise RuntimeError("原候选任务状态在复核期间发生变化，报告未保存")
        after_evaluations = {
            set_id: evaluation_snapshot(set_id) for set_id in ("regular", "structured")
        }
        if after_evaluations != before_evaluations:
            raise RuntimeError("评估集在复核期间发生变化，报告未保存")

        report_payloads = {
            "regular": assessment.regular_evaluation,
            "structured": assessment.structured_evaluation,
        }
        for set_id, payload in report_payloads.items():
            _, expected_hash, expected_revision = before_evaluations[set_id]
            if payload.get("evaluation_set_hash") != expected_hash:
                raise RuntimeError(f"{set_id} 评估报告与本次评估集不一致，报告未保存")
            recorded_report_revision = assessment.result.get(f"{set_id}_evaluation_set_revision_id")
            if recorded_report_revision and recorded_report_revision != expected_revision:
                raise RuntimeError(f"{set_id} 评估修订不一致，报告未保存")
            if payload.get("data_version_hash") != manifest.get("data_version_hash"):
                raise RuntimeError(f"{set_id} 评估报告与候选数据版本不一致，报告未保存")

        run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        final_dir = revalidations_root / run_id
        if final_dir.exists():
            raise RuntimeError("候选复核报告目录发生时间戳冲突，请重新提交")
        staging_dir.replace(final_dir)
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise

    published_artifacts = {key: str(final_dir / Path(path).name) for key, path in artifacts.items()}
    _set_step(
        job,
        store,
        "candidate_revalidate_report",
        "候选复核报告已保存；候选未发布或激活",
        candidate_job_id=candidate_job_id,
        report_path=published_artifacts["gate_report"],
        passed=bool(assessment.result.get("passed")),
    )
    return {
        "candidate_job_id": candidate_job_id,
        "source_catalog_revision": source_catalog_revision,
        "data_version_hash": manifest.get("data_version_hash", ""),
        "passed": bool(assessment.result.get("passed")),
        "candidate_gate": assessment.result,
        **published_artifacts,
        "revalidation_only": True,
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
        **current_evidence_context(),
        "evaluation_set_id": evaluation_set_id,
        "evaluation_set_revision_id": published_revision_id(evaluation_set_id),
    }
    run_id = str(job.params.get("verification_run_id") or "")
    if run_id:
        result["verification_run_id"] = validate_verification_run_id(run_id)
    out_dir = AUDIT_DIR / "reports"
    is_structured = evaluation_set_id == "structured"
    out_path, markdown_path = write_quality_report(
        out_dir,
        "structured" if is_structured else "regular",
        result,
        render_evaluation_markdown(
            result, "结构化检索专项评估" if is_structured else "检索评估报告"
        ),
        verification_run_id=run_id or None,
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
    result.update(current_evidence_context())
    result["evaluation_set_id"] = evaluation_set_id
    result["evaluation_set_revision_id"] = published_revision_id(evaluation_set_id)
    run_id = str(job.params.get("verification_run_id") or "")
    if run_id:
        result["verification_run_id"] = validate_verification_run_id(run_id)
    out_dir = AUDIT_DIR / "reports"
    out_path, markdown_path = write_quality_report(
        out_dir,
        "answer",
        result,
        render_answer_evaluation_markdown(result),
        verification_run_id=run_id or None,
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
            default_error="回答级盲测执行失败",
        )
    return output
