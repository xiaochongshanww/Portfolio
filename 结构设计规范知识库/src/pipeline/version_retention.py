from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Iterable
from uuid import uuid4

from .active_db import active_db_dir
from .paths import ACTIVE_DB_PATH, AUDIT_DIR, DB_VERSIONS_DIR


VERSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
PIN_FILENAME = ".retention.json"
GATE_PATH = Path("quality") / "candidate_activation_gate.json"
AUDIT_LOCK = Lock()


class VersionRetentionError(RuntimeError):
    pass


class UnsafeVersionPath(VersionRetentionError):
    pass


@dataclass(frozen=True)
class VersionRetentionPolicy:
    keep_recent_passed: int = 2
    success_max_age_days: int = 30
    failed_max_age_days: int = 7
    minimum_age_hours: int = 24
    high_watermark_bytes: int = 20 * 1024**3
    low_watermark_bytes: int = 16 * 1024**3
    plan_ttl_minutes: int = 15

    def validate(self) -> None:
        values = {
            "keep_recent_passed": self.keep_recent_passed,
            "success_max_age_days": self.success_max_age_days,
            "failed_max_age_days": self.failed_max_age_days,
            "minimum_age_hours": self.minimum_age_hours,
            "low_watermark_bytes": self.low_watermark_bytes,
        }
        invalid = [name for name, value in values.items() if value < 0]
        if invalid:
            raise VersionRetentionError(f"保留策略不能为负数: {', '.join(invalid)}")
        if self.high_watermark_bytes <= 0:
            raise VersionRetentionError("high_watermark_bytes 必须大于 0")
        if self.low_watermark_bytes > self.high_watermark_bytes:
            raise VersionRetentionError("low_watermark_bytes 不能大于 high_watermark_bytes")
        if not 1 <= self.plan_ttl_minutes <= 1440:
            raise VersionRetentionError("plan_ttl_minutes 必须在 1 到 1440 之间")


def retention_policy_from_settings(config: Any) -> VersionRetentionPolicy:
    return VersionRetentionPolicy(
        keep_recent_passed=config.version_retention_keep_recent_passed,
        success_max_age_days=config.version_retention_success_days,
        failed_max_age_days=config.version_retention_failed_days,
        minimum_age_hours=config.version_retention_minimum_age_hours,
        high_watermark_bytes=config.version_retention_high_watermark_bytes,
        low_watermark_bytes=config.version_retention_low_watermark_bytes,
        plan_ttl_minutes=config.version_retention_plan_ttl_minutes,
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.{uuid4().hex[:8]}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _append_audit(audit_dir: Path, event: dict[str, Any]) -> None:
    path = audit_dir / "version_retention" / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": _iso(_utc_now()), **event}
    with AUDIT_LOCK, path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _is_reparse_point(path: Path) -> bool:
    info = path.lstat()
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return path.is_symlink() or bool(attributes & reparse_flag)


def _validate_version_id(version_id: str) -> str:
    if not VERSION_ID_PATTERN.fullmatch(version_id) or version_id.startswith(".deleting-"):
        raise UnsafeVersionPath(f"非法版本标识: {version_id!r}")
    return version_id


def _safe_version_path(versions_dir: Path, version_id: str, *, must_exist: bool = True) -> Path:
    _validate_version_id(version_id)
    root = versions_dir.resolve()
    candidate = root / version_id
    if must_exist and not candidate.exists():
        raise FileNotFoundError(f"版本不存在: {version_id}")
    if candidate.exists():
        if candidate.resolve() != candidate.absolute() or candidate.parent.resolve() != root:
            raise UnsafeVersionPath(f"版本路径越界: {version_id}")
        if not candidate.is_dir() or _is_reparse_point(candidate):
            raise UnsafeVersionPath(f"版本路径不是普通目录: {version_id}")
    return candidate


def _scan_directory(path: Path) -> dict[str, int]:
    total = 0
    file_count = 0
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
                    raise UnsafeVersionPath(f"版本目录包含链接或重解析点: {entry_path}")
                newest_mtime_ns = max(newest_mtime_ns, info.st_mtime_ns)
                if entry.is_dir(follow_symlinks=False):
                    pending.append(entry_path)
                elif entry.is_file(follow_symlinks=False):
                    total += info.st_size
                    file_count += 1
    return {
        "size_bytes": total,
        "file_count": file_count,
        "newest_mtime_ns": newest_mtime_ns,
    }


def _file_digest(path: Path) -> str:
    if not path.is_file() or _is_reparse_point(path):
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fingerprint(version_id: str, scan: dict[str, int], manifest: Path, gate: Path) -> str:
    material = {
        "version_id": version_id,
        **scan,
        "manifest_sha256": _file_digest(manifest),
        "gate_sha256": _file_digest(gate),
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _active_version_id(versions_dir: Path, pointer_path: Path) -> str:
    try:
        active = active_db_dir(pointer_path).resolve()
        relative = active.relative_to(versions_dir.resolve())
    except (FileNotFoundError, ValueError, OSError):
        return ""
    return relative.parts[0] if len(relative.parts) >= 2 else ""


def _running_version_ids(jobs: Iterable[dict[str, Any]]) -> set[str]:
    return {
        str(job.get("job_id"))
        for job in jobs
        if job.get("type") == "rebuild" and job.get("status") in {"queued", "running"}
    }


def _version_state(path: Path, active: bool, running: bool) -> tuple[str, dict[str, Any]]:
    gate_path = path / GATE_PATH
    gate = _read_json(gate_path)
    if active:
        state = "active"
    elif running:
        state = "running"
    elif gate.get("passed") is True:
        state = "passed"
    elif gate.get("passed") is False:
        state = "failed_gate"
    elif gate_path.exists():
        state = "invalid_gate"
    elif (path / "manifest.json").is_file():
        state = "legacy_complete"
    else:
        state = "incomplete"
    return state, gate


def inventory_versions(
    *,
    policy: VersionRetentionPolicy,
    versions_dir: Path = DB_VERSIONS_DIR,
    pointer_path: Path = ACTIVE_DB_PATH,
    jobs: Iterable[dict[str, Any]] = (),
    now: datetime | None = None,
) -> dict[str, Any]:
    policy.validate()
    current_time = now or _utc_now()
    versions_dir.mkdir(parents=True, exist_ok=True)
    active_id = _active_version_id(versions_dir, pointer_path)
    running_ids = _running_version_ids(jobs)
    versions: list[dict[str, Any]] = []

    for path in sorted(versions_dir.iterdir(), key=lambda item: item.name):
        if path.name.startswith(".deleting-"):
            continue
        item: dict[str, Any] = {"version_id": path.name, "path": str(path)}
        try:
            safe_path = _safe_version_path(versions_dir, path.name)
            scan = _scan_directory(safe_path)
            modified_at = datetime.fromtimestamp(scan["newest_mtime_ns"] / 1_000_000_000, timezone.utc)
            state, gate = _version_state(
                safe_path,
                path.name == active_id,
                path.name in running_ids,
            )
            pin = _read_json(safe_path / PIN_FILENAME)
            pin_marker_invalid = (safe_path / PIN_FILENAME).exists() and not pin
            item.update(
                {
                    **scan,
                    "modified_at": _iso(modified_at),
                    "age_hours": max(0.0, (current_time - modified_at).total_seconds() / 3600),
                    "state": state,
                    "gate_passed": gate.get("passed"),
                    "pinned": pin.get("pinned") is True,
                    "pin_marker_invalid": pin_marker_invalid,
                    "pin_note": str(pin.get("note") or ""),
                    "fingerprint": _fingerprint(
                        path.name,
                        scan,
                        safe_path / "manifest.json",
                        safe_path / GATE_PATH,
                    ),
                    "safe": True,
                }
            )
        except (OSError, VersionRetentionError) as exc:
            item.update(
                {
                    "size_bytes": 0,
                    "file_count": 0,
                    "modified_at": "",
                    "age_hours": 0.0,
                    "state": "unsafe",
                    "gate_passed": None,
                    "pinned": False,
                    "pin_marker_invalid": False,
                    "pin_note": "",
                    "fingerprint": "",
                    "safe": False,
                    "scan_error": str(exc),
                }
            )
        versions.append(item)

    rollback_candidates = sorted(
        [item for item in versions if item["state"] in {"passed", "legacy_complete"}],
        key=lambda item: item.get("modified_at") or "",
        reverse=True,
    )[: policy.keep_recent_passed]
    rollback_ids = {item["version_id"] for item in rollback_candidates}

    total_bytes = sum(int(item.get("size_bytes", 0)) for item in versions)
    age_candidates: list[dict[str, Any]] = []
    pressure_pool: list[dict[str, Any]] = []
    for item in versions:
        reasons: list[str] = []
        if item["state"] == "active":
            reasons.append("active")
        if item["state"] == "running":
            reasons.append("running")
        if item.get("pinned"):
            reasons.append("pinned")
        if item.get("pin_marker_invalid"):
            reasons.append("invalid_pin_marker")
        if not item.get("safe"):
            reasons.append("unsafe")
        if item.get("age_hours", 0) < policy.minimum_age_hours:
            reasons.append("minimum_age")
        if item["version_id"] in rollback_ids:
            reasons.append("recent_rollback")
        item["protected"] = bool(reasons)
        item["protection_reasons"] = reasons
        item["cleanup_eligible"] = False
        item["cleanup_reason"] = ""
        if reasons:
            continue

        age_days = float(item.get("age_hours", 0)) / 24
        if item["state"] in {"failed_gate", "invalid_gate", "incomplete"}:
            if age_days >= policy.failed_max_age_days:
                item["cleanup_eligible"] = True
                item["cleanup_reason"] = "expired_failed_or_incomplete"
                age_candidates.append(item)
            else:
                pressure_pool.append(item)
        elif item["state"] in {"passed", "legacy_complete"}:
            if age_days >= policy.success_max_age_days:
                item["cleanup_eligible"] = True
                item["cleanup_reason"] = "expired_successful"
                age_candidates.append(item)
            else:
                pressure_pool.append(item)

    projected_bytes = total_bytes - sum(int(item["size_bytes"]) for item in age_candidates)
    pressure_added: list[dict[str, Any]] = []
    if total_bytes > policy.high_watermark_bytes:
        priority = {
            "failed_gate": 0,
            "invalid_gate": 0,
            "incomplete": 0,
            "legacy_complete": 1,
            "passed": 2,
        }
        for item in sorted(
            pressure_pool,
            key=lambda value: (
                priority.get(str(value["state"]), 9),
                value.get("modified_at") or "",
            ),
        ):
            if projected_bytes <= policy.low_watermark_bytes:
                break
            item["cleanup_eligible"] = True
            item["cleanup_reason"] = "disk_pressure"
            pressure_added.append(item)
            projected_bytes -= int(item["size_bytes"])

    candidates = sorted(
        [*age_candidates, *pressure_added],
        key=lambda item: (item.get("modified_at") or "", item["version_id"]),
    )
    return {
        "schema_version": 1,
        "generated_at": _iso(current_time),
        "active_version_id": active_id,
        "policy": asdict(policy),
        "version_count": len(versions),
        "total_bytes": total_bytes,
        "cleanup_candidate_count": len(candidates),
        "cleanup_candidate_bytes": sum(int(item["size_bytes"]) for item in candidates),
        "projected_bytes": projected_bytes,
        "target_unmet_bytes": max(0, projected_bytes - policy.low_watermark_bytes)
        if total_bytes > policy.high_watermark_bytes
        else 0,
        "versions": versions,
    }


def create_cleanup_plan(
    *,
    policy: VersionRetentionPolicy,
    versions_dir: Path = DB_VERSIONS_DIR,
    pointer_path: Path = ACTIVE_DB_PATH,
    audit_dir: Path = AUDIT_DIR,
    jobs: Iterable[dict[str, Any]] = (),
    now: datetime | None = None,
) -> dict[str, Any]:
    current_time = now or _utc_now()
    inventory = inventory_versions(
        policy=policy,
        versions_dir=versions_dir,
        pointer_path=pointer_path,
        jobs=jobs,
        now=current_time,
    )
    plan_id = uuid4().hex[:16]
    candidates = [
        {
            "version_id": item["version_id"],
            "fingerprint": item["fingerprint"],
            "size_bytes": item["size_bytes"],
            "modified_at": item["modified_at"],
            "reason": item["cleanup_reason"],
        }
        for item in inventory["versions"]
        if item.get("cleanup_eligible")
    ]
    plan = {
        "schema_version": 1,
        "plan_id": plan_id,
        "status": "planned",
        "created_at": _iso(current_time),
        "expires_at": _iso(current_time + timedelta(minutes=policy.plan_ttl_minutes)),
        "policy": inventory["policy"],
        "total_bytes": inventory["total_bytes"],
        "projected_bytes": inventory["projected_bytes"],
        "target_unmet_bytes": inventory["target_unmet_bytes"],
        "candidate_count": len(candidates),
        "candidate_bytes": sum(int(item["size_bytes"]) for item in candidates),
        "candidates": candidates,
    }
    plan_path = audit_dir / "version_retention" / "plans" / f"{plan_id}.json"
    _atomic_json(plan_path, plan)
    _append_audit(
        audit_dir,
        {
            "event": "version_cleanup_planned",
            "plan_id": plan_id,
            "candidate_count": len(candidates),
            "candidate_bytes": plan["candidate_bytes"],
        },
    )
    return {**plan, "plan_path": str(plan_path)}


def _load_plan(plan_id: str, audit_dir: Path) -> tuple[dict[str, Any], Path]:
    if not re.fullmatch(r"[a-f0-9]{16}", plan_id):
        raise VersionRetentionError("非法清理计划标识")
    path = audit_dir / "version_retention" / "plans" / f"{plan_id}.json"
    plan = _read_json(path)
    if not plan or plan.get("plan_id") != plan_id:
        raise FileNotFoundError(f"清理计划不存在: {plan_id}")
    return plan, path


def execute_cleanup_plan(
    plan_id: str,
    *,
    policy: VersionRetentionPolicy,
    versions_dir: Path = DB_VERSIONS_DIR,
    pointer_path: Path = ACTIVE_DB_PATH,
    audit_dir: Path = AUDIT_DIR,
    jobs: Iterable[dict[str, Any]] = (),
    now: datetime | None = None,
) -> dict[str, Any]:
    current_time = now or _utc_now()
    plan, plan_path = _load_plan(plan_id, audit_dir)
    if plan.get("status") != "planned":
        raise VersionRetentionError(f"清理计划状态不可执行: {plan.get('status')}")
    expires_at = datetime.fromisoformat(str(plan["expires_at"]))
    if current_time > expires_at:
        plan["status"] = "expired"
        plan["finished_at"] = _iso(current_time)
        _atomic_json(plan_path, plan)
        _append_audit(audit_dir, {"event": "version_cleanup_expired", "plan_id": plan_id})
        raise VersionRetentionError("清理计划已过期，请重新生成")
    if plan.get("policy") != asdict(policy):
        plan["status"] = "invalidated"
        plan["finished_at"] = _iso(current_time)
        plan["invalidated_reason"] = "policy_changed"
        _atomic_json(plan_path, plan)
        _append_audit(
            audit_dir,
            {"event": "version_cleanup_invalidated", "plan_id": plan_id, "reason": "policy_changed"},
        )
        raise VersionRetentionError("保留策略已变化，请重新生成清理计划")

    inventory = inventory_versions(
        policy=policy,
        versions_dir=versions_dir,
        pointer_path=pointer_path,
        jobs=jobs,
        now=current_time,
    )
    current_by_id = {item["version_id"]: item for item in inventory["versions"]}
    deleted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for candidate in plan.get("candidates", []):
        version_id = str(candidate.get("version_id") or "")
        current = current_by_id.get(version_id)
        if not current:
            skipped.append({"version_id": version_id, "reason": "missing"})
            continue
        if current.get("protected"):
            skipped.append(
                {
                    "version_id": version_id,
                    "reason": "protected",
                    "protection_reasons": current.get("protection_reasons", []),
                }
            )
            continue
        if current.get("fingerprint") != candidate.get("fingerprint"):
            skipped.append({"version_id": version_id, "reason": "fingerprint_changed"})
            continue
        tombstone: Path | None = None
        try:
            source = _safe_version_path(versions_dir, version_id)
            tombstone = versions_dir.resolve() / f".deleting-{version_id}-{uuid4().hex[:8]}"
            source.replace(tombstone)
            shutil.rmtree(tombstone)
            deleted.append(
                {
                    "version_id": version_id,
                    "size_bytes": int(candidate.get("size_bytes", 0)),
                    "reason": candidate.get("reason", ""),
                }
            )
            _append_audit(
                audit_dir,
                {
                    "event": "version_deleted",
                    "plan_id": plan_id,
                    "version_id": version_id,
                    "size_bytes": int(candidate.get("size_bytes", 0)),
                },
            )
        except Exception as exc:
            restore_error = ""
            if tombstone is not None and tombstone.exists():
                try:
                    source = versions_dir.resolve() / version_id
                    if not source.exists():
                        tombstone.replace(source)
                except Exception as restore_exc:
                    restore_error = str(restore_exc)
            failed.append(
                {
                    "version_id": version_id,
                    "reason": "delete_failed",
                    "error": str(exc),
                    **({"restore_error": restore_error} if restore_error else {}),
                }
            )
            _append_audit(
                audit_dir,
                {
                    "event": "version_delete_failed",
                    "plan_id": plan_id,
                    "version_id": version_id,
                    "error": str(exc),
                },
            )

    status = "partial_failed" if failed else "completed_with_skips" if skipped else "completed"
    result = {
        "schema_version": 1,
        "plan_id": plan_id,
        "status": status,
        "finished_at": _iso(current_time),
        "deleted_count": len(deleted),
        "deleted_bytes": sum(item["size_bytes"] for item in deleted),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "deleted": deleted,
        "skipped": skipped,
        "failed": failed,
    }
    plan.update({"status": status, "finished_at": result["finished_at"], "execution": result})
    _atomic_json(plan_path, plan)
    report_path = audit_dir / "version_retention" / "executions" / f"{plan_id}.json"
    _atomic_json(report_path, result)
    _append_audit(
        audit_dir,
        {
            "event": "version_cleanup_finished",
            "plan_id": plan_id,
            "status": status,
            "deleted_count": len(deleted),
            "deleted_bytes": result["deleted_bytes"],
            "skipped_count": len(skipped),
            "failed_count": len(failed),
        },
    )
    return {**result, "report_path": str(report_path)}


def set_version_pin(
    version_id: str,
    *,
    pinned: bool,
    note: str = "",
    versions_dir: Path = DB_VERSIONS_DIR,
    audit_dir: Path = AUDIT_DIR,
) -> dict[str, Any]:
    version_path = _safe_version_path(versions_dir, version_id)
    payload = {
        "schema_version": 1,
        "pinned": bool(pinned),
        "note": note.strip()[:500],
        "updated_at": _iso(_utc_now()),
    }
    _atomic_json(version_path / PIN_FILENAME, payload)
    _append_audit(
        audit_dir,
        {
            "event": "version_retention_changed",
            "version_id": version_id,
            "pinned": bool(pinned),
            "note": payload["note"],
        },
    )
    return {"version_id": version_id, **payload}
