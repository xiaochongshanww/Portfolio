from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from .evidence_context import validate_verification_run_id
from .report_store import (
    QUALITY_RUN_LATEST_POINTER_NAME,
    QUALITY_RUN_MANIFEST_NAME,
    QUALITY_RUNS_DIRECTORY,
    QualityReportStoreError,
    atomic_write_json,
    load_quality_run_manifest,
    load_quality_run_pointer,
    quality_report_store_lock,
)

QUALITY_RUN_RETENTION_SCHEMA_VERSION = 1
QUALITY_RUN_RETENTION_DIRECTORY = "quality_run_retention"
PLAN_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
SNAPSHOT_RUN_PATTERN = re.compile(r"(?:^|/)data/audit/reports/runs/([0-9a-f]{32})/(?:[^/]+)$")
AUDIT_LOCK = Lock()


class QualityRunRetentionError(RuntimeError):
    pass


class UnsafeQualityRunPath(QualityRunRetentionError):
    pass


@dataclass(frozen=True)
class QualityRunRetentionPolicy:
    keep_recent_complete: int = 10
    complete_max_age_days: int = 90
    incomplete_max_age_days: int = 7
    minimum_age_hours: int = 24
    plan_ttl_minutes: int = 15

    def validate(self) -> None:
        values = asdict(self)
        invalid = [name for name, value in values.items() if value < 0]
        if invalid:
            raise QualityRunRetentionError(f"质量运行保留策略不能为负数：{', '.join(invalid)}")
        if not 1 <= self.plan_ttl_minutes <= 1440:
            raise QualityRunRetentionError("plan_ttl_minutes 必须在 1 到 1440 之间")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _parse_datetime(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise QualityRunRetentionError(f"{field} 无效")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualityRunRetentionError(f"{field} 无效") from exc
    if parsed.tzinfo is None:
        raise QualityRunRetentionError(f"{field} 必须包含时区")
    return parsed.astimezone(UTC)


def _is_reparse_point(path: Path) -> bool:
    info = path.lstat()
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return path.is_symlink() or bool(attributes & reparse_flag)


def _safe_run_path(runs_dir: Path, run_id: str, *, must_exist: bool = True) -> Path:
    try:
        validate_verification_run_id(run_id)
    except ValueError as exc:
        raise UnsafeQualityRunPath(f"非法质量运行标识：{run_id!r}") from exc
    root = runs_dir.resolve()
    candidate = root / run_id
    if must_exist and not candidate.exists():
        raise FileNotFoundError(f"质量运行不存在：{run_id}")
    if candidate.exists():
        if candidate.parent.resolve() != root or candidate.resolve() != candidate.absolute():
            raise UnsafeQualityRunPath(f"质量运行路径越界：{run_id}")
        if not candidate.is_dir() or _is_reparse_point(candidate):
            raise UnsafeQualityRunPath(f"质量运行路径不是普通目录：{run_id}")
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _scan_run(path: Path) -> dict[str, Any]:
    if _is_reparse_point(path):
        raise UnsafeQualityRunPath(f"质量运行目录包含链接或重解析点：{path.name}")
    files: list[tuple[str, int, int, str]] = []
    newest_mtime_ns = path.stat().st_mtime_ns
    pending = [path]
    while pending:
        current = pending.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                entry_path = Path(entry.path)
                info = entry.stat(follow_symlinks=False)
                attributes = int(getattr(info, "st_file_attributes", 0))
                reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
                if entry.is_symlink() or attributes & reparse_flag:
                    raise UnsafeQualityRunPath(
                        f"质量运行目录包含链接或重解析点：{entry_path.relative_to(path)}"
                    )
                newest_mtime_ns = max(newest_mtime_ns, info.st_mtime_ns)
                if entry.is_dir(follow_symlinks=False):
                    pending.append(entry_path)
                elif entry.is_file(follow_symlinks=False):
                    files.append(
                        (
                            entry_path.relative_to(path).as_posix(),
                            info.st_size,
                            info.st_mtime_ns,
                            _sha256(entry_path),
                        )
                    )
    files.sort(key=lambda item: item[0])
    digest = hashlib.sha256()
    for relative, size, modified_ns, file_hash in files:
        digest.update(
            json.dumps(
                [relative, size, modified_ns, file_hash],
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        digest.update(b"\n")
    return {
        "size_bytes": sum(item[1] for item in files),
        "file_count": len(files),
        "newest_mtime_ns": newest_mtime_ns,
        "fingerprint": digest.hexdigest(),
    }


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def load_snapshot_protection(snapshot_paths: Iterable[Path]) -> dict[str, Any]:
    run_ids: set[str] = set()
    sources: list[dict[str, str]] = []
    for path in sorted({item.resolve() for item in snapshot_paths if item.exists()}):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise QualityRunRetentionError(f"脱敏质量快照无法读取：{path.name}") from exc
        if not isinstance(payload, dict):
            raise QualityRunRetentionError(f"脱敏质量快照必须是 JSON 对象：{path.name}")
        for value in _walk_strings(payload):
            match = SNAPSHOT_RUN_PATTERN.fullmatch(value.replace("\\", "/"))
            if match:
                run_ids.add(match.group(1))
        sources.append({"name": path.name, "sha256": _sha256(path)})
    material = {"run_ids": sorted(run_ids), "sources": sources}
    fingerprint = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {**material, "fingerprint": fingerprint}


def default_snapshot_paths(project_root: Path) -> list[Path]:
    quality_dir = project_root / "docs" / "quality"
    paths = [quality_dir / "质量证据状态.json"]
    history_dir = quality_dir / "质量证据历史"
    if history_dir.is_dir():
        paths.extend(sorted(history_dir.glob("*.json")))
    return [path for path in paths if path.is_file()]


def _pointer_fingerprint(reports_dir: Path) -> tuple[dict[str, Any] | None, str]:
    pointer = load_quality_run_pointer(reports_dir)
    path = reports_dir / QUALITY_RUN_LATEST_POINTER_NAME
    return pointer, _sha256(path) if path.is_file() else ""


def list_quality_runs(
    reports_dir: Path,
    *,
    snapshot_paths: Iterable[Path] = (),
    policy: QualityRunRetentionPolicy | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    selected_policy = policy or QualityRunRetentionPolicy()
    selected_policy.validate()
    observed_at = (now or _utc_now()).astimezone(UTC)
    pointer, pointer_hash = _pointer_fingerprint(reports_dir)
    latest_run_id = str(pointer["verification_run_id"]) if pointer else ""
    snapshot = load_snapshot_protection(snapshot_paths)
    runs_dir = reports_dir / QUALITY_RUNS_DIRECTORY
    rows: list[dict[str, Any]] = []
    if runs_dir.exists() and not runs_dir.is_dir():
        raise QualityRunRetentionError("质量运行根路径不是目录")

    for path in sorted(runs_dir.iterdir(), key=lambda item: item.name) if runs_dir.is_dir() else []:
        row: dict[str, Any] = {
            "run_id": path.name,
            "classification": "invalid",
            "eligible": False,
            "protection_reasons": [],
        }
        try:
            run_path = _safe_run_path(runs_dir, path.name)
            scan = _scan_run(run_path)
            row.update(scan)
            manifest_path = run_path / QUALITY_RUN_MANIFEST_NAME
            if manifest_path.is_file():
                manifest = load_quality_run_manifest(reports_dir, path.name)
                reference_time = _parse_datetime(
                    manifest.get("completed_at"), field="质量运行完成时间"
                )
                row.update(
                    {
                        "classification": "complete",
                        "completed_at": _iso(reference_time),
                        "passed": manifest["passed"],
                    }
                )
            else:
                reference_time = datetime.fromtimestamp(
                    scan["newest_mtime_ns"] / 1_000_000_000,
                    tz=UTC,
                )
                row.update(
                    {
                        "classification": "incomplete",
                        "last_modified_at": _iso(reference_time),
                    }
                )
            row["age_hours"] = round(
                max(0.0, (observed_at - reference_time).total_seconds() / 3600), 3
            )
        except (OSError, QualityReportStoreError, QualityRunRetentionError, ValueError) as exc:
            row["error"] = str(exc)
        rows.append(row)

    complete_rows = sorted(
        (row for row in rows if row["classification"] == "complete"),
        key=lambda row: str(row["completed_at"]),
        reverse=True,
    )
    recent_ids = {row["run_id"] for row in complete_rows[: selected_policy.keep_recent_complete]}
    snapshot_ids = set(snapshot["run_ids"])
    for row in rows:
        reasons: list[str] = []
        run_id = row["run_id"]
        if row["classification"] == "invalid":
            reasons.append("invalid")
        if run_id == latest_run_id:
            reasons.append("latest")
        if run_id in snapshot_ids:
            reasons.append("snapshot_reference")
        if run_id in recent_ids:
            reasons.append("recent_complete")
        age_hours = float(row.get("age_hours", 0.0))
        if row["classification"] != "invalid" and age_hours < selected_policy.minimum_age_hours:
            reasons.append("minimum_age")
        row["protection_reasons"] = reasons
        if reasons:
            continue
        max_age_hours = (
            selected_policy.complete_max_age_days * 24
            if row["classification"] == "complete"
            else selected_policy.incomplete_max_age_days * 24
        )
        row["eligible"] = age_hours >= max_age_hours

    protection_material = {
        "latest_run_id": latest_run_id,
        "pointer_sha256": pointer_hash,
        "snapshot_fingerprint": snapshot["fingerprint"],
        "snapshot_run_ids": snapshot["run_ids"],
        "recent_complete_run_ids": sorted(recent_ids),
    }
    protection_fingerprint = hashlib.sha256(
        json.dumps(protection_material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": QUALITY_RUN_RETENTION_SCHEMA_VERSION,
        "generated_at": _iso(observed_at),
        "reports_dir": str(reports_dir.resolve()),
        "policy": asdict(selected_policy),
        "latest_run_id": latest_run_id or None,
        "snapshot_run_ids": snapshot["run_ids"],
        "protection_fingerprint": protection_fingerprint,
        "run_count": len(rows),
        "complete_count": sum(row["classification"] == "complete" for row in rows),
        "incomplete_count": sum(row["classification"] == "incomplete" for row in rows),
        "invalid_count": sum(row["classification"] == "invalid" for row in rows),
        "eligible_count": sum(bool(row["eligible"]) for row in rows),
        "total_bytes": sum(int(row.get("size_bytes", 0)) for row in rows),
        "runs": rows,
    }


def _retention_root(audit_dir: Path) -> Path:
    return audit_dir / QUALITY_RUN_RETENTION_DIRECTORY


def _append_audit(audit_dir: Path, event: dict[str, Any]) -> None:
    path = _retention_root(audit_dir) / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": _iso(_utc_now()), **event}
    with AUDIT_LOCK, path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _plan_path(audit_dir: Path, plan_id: str) -> Path:
    if not PLAN_ID_PATTERN.fullmatch(plan_id):
        raise QualityRunRetentionError("质量运行清理计划标识无效")
    return _retention_root(audit_dir) / "plans" / f"{plan_id}.json"


def create_quality_run_cleanup_plan(
    reports_dir: Path,
    audit_dir: Path,
    *,
    snapshot_paths: Iterable[Path] = (),
    policy: QualityRunRetentionPolicy | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    selected_policy = policy or QualityRunRetentionPolicy()
    created_at = (now or _utc_now()).astimezone(UTC)
    inventory = list_quality_runs(
        reports_dir,
        snapshot_paths=snapshot_paths,
        policy=selected_policy,
        now=created_at,
    )
    plan_id = uuid4().hex
    candidates = [
        {
            key: row[key]
            for key in (
                "run_id",
                "classification",
                "size_bytes",
                "file_count",
                "newest_mtime_ns",
                "fingerprint",
            )
        }
        for row in inventory["runs"]
        if row["eligible"]
    ]
    plan = {
        "schema_version": QUALITY_RUN_RETENTION_SCHEMA_VERSION,
        "status": "planned",
        "plan_id": plan_id,
        "created_at": _iso(created_at),
        "expires_at": _iso(created_at + timedelta(minutes=selected_policy.plan_ttl_minutes)),
        "policy": asdict(selected_policy),
        "protection_fingerprint": inventory["protection_fingerprint"],
        "candidate_count": len(candidates),
        "reclaimable_bytes": sum(item["size_bytes"] for item in candidates),
        "candidates": candidates,
    }
    path = _plan_path(audit_dir, plan_id)
    if path.exists():
        raise QualityRunRetentionError("质量运行清理计划标识冲突")
    atomic_write_json(path, plan)
    _append_audit(
        audit_dir,
        {
            "event": "quality_run_cleanup_planned",
            "plan_id": plan_id,
            "candidate_count": len(candidates),
            "reclaimable_bytes": plan["reclaimable_bytes"],
        },
    )
    return {**plan, "plan_path": str(path)}


def _load_plan(audit_dir: Path, plan_id: str) -> dict[str, Any]:
    path = _plan_path(audit_dir, plan_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualityRunRetentionError("质量运行清理计划无法读取") from exc
    if not isinstance(payload, dict):
        raise QualityRunRetentionError("质量运行清理计划必须是 JSON 对象")
    if (
        payload.get("schema_version") != QUALITY_RUN_RETENTION_SCHEMA_VERSION
        or payload.get("status") != "planned"
        or payload.get("plan_id") != plan_id
    ):
        raise QualityRunRetentionError("质量运行清理计划契约无效")
    return payload


def execute_quality_run_cleanup_plan(
    reports_dir: Path,
    audit_dir: Path,
    plan_id: str,
    *,
    snapshot_paths: Iterable[Path] = (),
    confirm: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not confirm:
        raise QualityRunRetentionError("执行质量运行清理必须显式确认")
    _plan_path(audit_dir, plan_id)
    execution_path = _retention_root(audit_dir) / "executions" / f"{plan_id}.json"
    if execution_path.is_file():
        try:
            existing = json.loads(execution_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise QualityRunRetentionError("质量运行清理执行报告无法读取") from exc
        if isinstance(existing, dict) and existing.get("plan_id") == plan_id:
            return {**existing, "execution_path": str(execution_path)}
        raise QualityRunRetentionError("质量运行清理执行报告契约无效")

    plan = _load_plan(audit_dir, plan_id)
    executed_at = (now or _utc_now()).astimezone(UTC)
    if executed_at > _parse_datetime(plan.get("expires_at"), field="清理计划过期时间"):
        raise QualityRunRetentionError("质量运行清理计划已过期")
    try:
        policy = QualityRunRetentionPolicy(**plan["policy"])
    except (KeyError, TypeError) as exc:
        raise QualityRunRetentionError("质量运行清理计划策略无效") from exc
    policy.validate()

    with quality_report_store_lock(reports_dir):
        inventory = list_quality_runs(
            reports_dir,
            snapshot_paths=snapshot_paths,
            policy=policy,
            now=executed_at,
        )
        if inventory["protection_fingerprint"] != plan.get("protection_fingerprint"):
            raise QualityRunRetentionError("质量运行保护集已变化，请重新生成清理计划")
        current_by_id = {row["run_id"]: row for row in inventory["runs"]}
        candidates = plan.get("candidates")
        if not isinstance(candidates, list):
            raise QualityRunRetentionError("质量运行清理计划候选集合无效")
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise QualityRunRetentionError("质量运行清理计划候选项无效")
            current = current_by_id.get(candidate.get("run_id"))
            if current is None or not current.get("eligible"):
                raise QualityRunRetentionError("质量运行候选保护状态已变化，请重新生成计划")
            for field in (
                "classification",
                "size_bytes",
                "file_count",
                "newest_mtime_ns",
                "fingerprint",
            ):
                if current.get(field) != candidate.get(field):
                    raise QualityRunRetentionError("质量运行候选内容已变化，请重新生成计划")

        results: list[dict[str, Any]] = []
        runs_dir = reports_dir / QUALITY_RUNS_DIRECTORY
        for candidate in candidates:
            run_id = str(candidate["run_id"])
            source = _safe_run_path(runs_dir, run_id)
            quarantine = runs_dir / f".deleting-{run_id}-{uuid4().hex[:8]}"
            result = {"run_id": run_id, "status": "deleted"}
            try:
                source.replace(quarantine)
                shutil.rmtree(quarantine)
            except Exception as exc:
                restore_error = ""
                if quarantine.exists() and not source.exists():
                    try:
                        quarantine.replace(source)
                    except OSError as restore_exc:
                        restore_error = f"；恢复失败：{restore_exc}"
                result = {
                    "run_id": run_id,
                    "status": "failed",
                    "error": f"{exc}{restore_error}",
                }
            results.append(result)

    failed_count = sum(result["status"] != "deleted" for result in results)
    execution = {
        "schema_version": QUALITY_RUN_RETENTION_SCHEMA_VERSION,
        "status": "succeeded" if failed_count == 0 else "partial_failed",
        "plan_id": plan_id,
        "executed_at": _iso(executed_at),
        "candidate_count": len(results),
        "deleted_count": len(results) - failed_count,
        "failed_count": failed_count,
        "reclaimed_bytes": sum(
            int(candidate["size_bytes"])
            for candidate, result in zip(candidates, results, strict=True)
            if result["status"] == "deleted"
        ),
        "results": results,
    }
    atomic_write_json(execution_path, execution)
    _append_audit(
        audit_dir,
        {
            "event": "quality_run_cleanup_executed",
            "plan_id": plan_id,
            "status": execution["status"],
            "deleted_count": execution["deleted_count"],
            "failed_count": failed_count,
            "reclaimed_bytes": execution["reclaimed_bytes"],
        },
    )
    return {**execution, "execution_path": str(execution_path)}
