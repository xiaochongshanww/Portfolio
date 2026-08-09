from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .evidence_context import validate_verification_run_id

QUALITY_RUN_SCHEMA_VERSION = 1
QUALITY_RUNS_DIRECTORY = "runs"
QUALITY_RUN_MANIFEST_NAME = "manifest.json"
QUALITY_RUN_LATEST_POINTER_NAME = "quality_run_latest.json"

REPORT_ARTIFACTS: dict[str, tuple[str, str]] = {
    "regular": ("evaluation.json", "evaluation.md"),
    "structured": ("evaluation_structured.json", "evaluation_structured.md"),
    "answer": ("evaluation_answer.json", "evaluation_answer.md"),
    "gate": ("quality_gate.json", "quality_gate.md"),
    "verification": ("verification.json", "verification.md"),
}

COMPATIBILITY_ARTIFACTS: dict[str, str] = {
    "regular_json": "evaluation_latest.json",
    "regular_markdown": "evaluation_latest.md",
    "structured_json": "evaluation_structured_latest.json",
    "structured_markdown": "evaluation_structured_latest.md",
    "answer_json": "evaluation_answer_latest.json",
    "answer_markdown": "evaluation_answer_latest.md",
    "gate_json": "quality_gate_latest.json",
    "gate_markdown": "quality_gate_latest.md",
    "verification_json": "verification_latest.json",
    "verification_markdown": "verification_latest.md",
}

REQUIRED_ARTIFACT_KEYS = tuple(COMPATIBILITY_ARTIFACTS)


class QualityReportStoreError(RuntimeError):
    pass


def _validate_completed_at(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise QualityReportStoreError("质量运行完成时间无效")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualityReportStoreError("质量运行完成时间无效") from exc
    if parsed.tzinfo is None:
        raise QualityReportStoreError("质量运行完成时间必须包含时区")
    return value


def _artifact_filename(artifact_key: str) -> str:
    try:
        report_kind, format_name = artifact_key.rsplit("_", 1)
        json_name, markdown_name = REPORT_ARTIFACTS[report_kind]
    except (KeyError, ValueError) as exc:
        raise QualityReportStoreError(f"未知质量报告产物：{artifact_key}") from exc
    if format_name == "json":
        return json_name
    if format_name == "markdown":
        return markdown_name
    raise QualityReportStoreError(f"未知质量报告格式：{artifact_key}")


def quality_run_directory(reports_dir: Path, verification_run_id: str) -> Path:
    run_id = validate_verification_run_id(verification_run_id)
    return reports_dir / QUALITY_RUNS_DIRECTORY / run_id


def quality_run_artifact_path(
    reports_dir: Path,
    verification_run_id: str,
    artifact_key: str,
) -> Path:
    return quality_run_directory(reports_dir, verification_run_id) / _artifact_filename(
        artifact_key
    )


def compatibility_artifact_path(reports_dir: Path, artifact_key: str) -> Path:
    try:
        filename = COMPATIBILITY_ARTIFACTS[artifact_key]
    except KeyError as exc:
        raise QualityReportStoreError(f"未知兼容质量报告产物：{artifact_key}") from exc
    return reports_dir / filename


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path, content: str) -> None:
    atomic_write_bytes(path, content.encode("utf-8"))


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(path, serialized)


def read_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise QualityReportStoreError(f"质量报告不存在：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualityReportStoreError(f"质量报告无法读取：{path}") from exc
    if not isinstance(payload, dict):
        raise QualityReportStoreError(f"质量报告必须是 JSON 对象：{path}")
    return payload


def write_quality_report(
    reports_dir: Path,
    report_kind: str,
    payload: dict[str, Any],
    markdown: str,
    *,
    verification_run_id: str | None = None,
) -> tuple[Path, Path]:
    if report_kind not in REPORT_ARTIFACTS:
        raise QualityReportStoreError(f"未知质量报告类型：{report_kind}")
    if verification_run_id:
        run_dir = quality_run_directory(reports_dir, verification_run_id)
        if (run_dir / QUALITY_RUN_MANIFEST_NAME).exists():
            raise QualityReportStoreError("已完成的质量运行不可修改")
        json_path = quality_run_artifact_path(
            reports_dir, verification_run_id, f"{report_kind}_json"
        )
        markdown_path = quality_run_artifact_path(
            reports_dir, verification_run_id, f"{report_kind}_markdown"
        )
    else:
        json_path = compatibility_artifact_path(reports_dir, f"{report_kind}_json")
        markdown_path = compatibility_artifact_path(reports_dir, f"{report_kind}_markdown")
    atomic_write_json(json_path, payload)
    atomic_write_text(markdown_path, markdown)
    return json_path, markdown_path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative_artifact_path(verification_run_id: str, filename: str) -> str:
    return Path(QUALITY_RUNS_DIRECTORY, verification_run_id, filename).as_posix()


def _validate_relative_run_path(
    value: Any,
    *,
    verification_run_id: str,
    expected_filename: str,
) -> str:
    expected = _relative_artifact_path(verification_run_id, expected_filename)
    if not isinstance(value, str) or value != expected:
        raise QualityReportStoreError(f"质量运行相对路径无效：{expected_filename}")
    return value


def finalize_quality_run(
    reports_dir: Path,
    verification_run_id: str,
    *,
    passed: bool,
    completed_at: str | None = None,
) -> dict[str, Any]:
    run_id = validate_verification_run_id(verification_run_id)
    run_dir = quality_run_directory(reports_dir, run_id)
    artifacts: dict[str, dict[str, Any]] = {}
    for artifact_key in REQUIRED_ARTIFACT_KEYS:
        path = quality_run_artifact_path(reports_dir, run_id, artifact_key)
        if not path.is_file():
            raise QualityReportStoreError(f"完整质量运行缺少产物：{artifact_key}")
        if artifact_key.endswith("_json"):
            report = read_json_object(path)
            if report.get("verification_run_id") != run_id:
                raise QualityReportStoreError(f"质量报告运行身份不一致：{artifact_key}")
            if artifact_key == "verification_json" and report.get("passed") != bool(passed):
                raise QualityReportStoreError("验证报告结论与发布状态不一致")
        artifacts[artifact_key] = {
            "filename": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }

    manifest_path = run_dir / QUALITY_RUN_MANIFEST_NAME
    if manifest_path.exists():
        manifest = read_json_object(manifest_path)
        if (
            manifest.get("schema_version") != QUALITY_RUN_SCHEMA_VERSION
            or manifest.get("status") != "complete"
            or manifest.get("verification_run_id") != run_id
            or manifest.get("passed") != bool(passed)
            or manifest.get("artifacts") != artifacts
            or (completed_at is not None and manifest.get("completed_at") != completed_at)
        ):
            raise QualityReportStoreError("已完成质量运行与重试发布参数不一致")
        finished = _validate_completed_at(manifest.get("completed_at"))
    else:
        finished = _validate_completed_at(completed_at or datetime.now(UTC).isoformat())
        manifest = {
            "schema_version": QUALITY_RUN_SCHEMA_VERSION,
            "status": "complete",
            "verification_run_id": run_id,
            "completed_at": finished,
            "passed": bool(passed),
            "artifacts": artifacts,
        }
        atomic_write_json(manifest_path, manifest)
    manifest_hash = _sha256(manifest_path)

    for artifact_key, compatibility_name in COMPATIBILITY_ARTIFACTS.items():
        source = quality_run_artifact_path(reports_dir, run_id, artifact_key)
        atomic_write_bytes(reports_dir / compatibility_name, source.read_bytes())

    pointer = {
        "schema_version": QUALITY_RUN_SCHEMA_VERSION,
        "status": "complete",
        "verification_run_id": run_id,
        "completed_at": finished,
        "passed": bool(passed),
        "manifest": _relative_artifact_path(run_id, QUALITY_RUN_MANIFEST_NAME),
        "manifest_sha256": manifest_hash,
        "artifacts": {
            artifact_key: _relative_artifact_path(run_id, _artifact_filename(artifact_key))
            for artifact_key in REQUIRED_ARTIFACT_KEYS
        },
    }
    atomic_write_json(reports_dir / QUALITY_RUN_LATEST_POINTER_NAME, pointer)
    return pointer


def load_quality_run_pointer(reports_dir: Path) -> dict[str, Any] | None:
    pointer_path = reports_dir / QUALITY_RUN_LATEST_POINTER_NAME
    if not pointer_path.exists():
        return None
    pointer = read_json_object(pointer_path)
    if pointer.get("schema_version") != QUALITY_RUN_SCHEMA_VERSION:
        raise QualityReportStoreError("不支持的质量运行指针版本")
    if pointer.get("status") != "complete":
        raise QualityReportStoreError("质量运行指针状态无效")
    completed_at = _validate_completed_at(pointer.get("completed_at"))
    if not isinstance(pointer.get("passed"), bool):
        raise QualityReportStoreError("质量运行指针状态无效")
    run_id = validate_verification_run_id(str(pointer.get("verification_run_id") or ""))
    manifest_relative = _validate_relative_run_path(
        pointer.get("manifest"),
        verification_run_id=run_id,
        expected_filename=QUALITY_RUN_MANIFEST_NAME,
    )
    manifest_path = reports_dir / Path(manifest_relative)
    manifest = read_json_object(manifest_path)
    if _sha256(manifest_path) != pointer.get("manifest_sha256"):
        raise QualityReportStoreError("质量运行清单哈希与最新指针不一致")
    if (
        manifest.get("schema_version") != QUALITY_RUN_SCHEMA_VERSION
        or manifest.get("status") != "complete"
        or manifest.get("verification_run_id") != run_id
        or _validate_completed_at(manifest.get("completed_at")) != completed_at
        or manifest.get("passed") != pointer.get("passed")
    ):
        raise QualityReportStoreError("质量运行清单身份与最新指针不一致")

    pointer_artifacts = pointer.get("artifacts")
    manifest_artifacts = manifest.get("artifacts")
    if not isinstance(pointer_artifacts, dict) or set(pointer_artifacts) != set(
        REQUIRED_ARTIFACT_KEYS
    ):
        raise QualityReportStoreError("质量运行指针产物集合不完整")
    if not isinstance(manifest_artifacts, dict) or set(manifest_artifacts) != set(
        REQUIRED_ARTIFACT_KEYS
    ):
        raise QualityReportStoreError("质量运行清单产物集合不完整")

    for artifact_key in REQUIRED_ARTIFACT_KEYS:
        filename = _artifact_filename(artifact_key)
        relative = _validate_relative_run_path(
            pointer_artifacts.get(artifact_key),
            verification_run_id=run_id,
            expected_filename=filename,
        )
        path = reports_dir / Path(relative)
        metadata = manifest_artifacts.get(artifact_key)
        if not isinstance(metadata, dict) or metadata.get("filename") != filename:
            raise QualityReportStoreError(f"质量运行清单产物元数据无效：{artifact_key}")
        if not path.is_file():
            raise QualityReportStoreError(f"质量运行指针产物不存在：{artifact_key}")
        if path.stat().st_size != metadata.get("size_bytes") or _sha256(path) != metadata.get(
            "sha256"
        ):
            raise QualityReportStoreError(f"质量运行产物完整性校验失败：{artifact_key}")
    return pointer


def resolve_latest_quality_artifact(reports_dir: Path, artifact_key: str) -> Path:
    return resolve_latest_quality_artifacts(reports_dir, (artifact_key,))[artifact_key]


def resolve_latest_quality_artifacts(
    reports_dir: Path,
    artifact_keys: tuple[str, ...] | list[str],
) -> dict[str, Path]:
    keys = tuple(artifact_keys)
    for artifact_key in keys:
        compatibility_artifact_path(reports_dir, artifact_key)
    pointer = load_quality_run_pointer(reports_dir)
    if pointer is None:
        return {
            artifact_key: compatibility_artifact_path(reports_dir, artifact_key)
            for artifact_key in keys
        }
    return {
        artifact_key: reports_dir / Path(pointer["artifacts"][artifact_key])
        for artifact_key in keys
    }
