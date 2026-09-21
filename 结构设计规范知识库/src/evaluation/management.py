from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from copy import deepcopy
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from src.evaluation.answer_runner import (
    ANSWER_EVAL_PATH,
    AnswerEvaluationCase,
    validate_answer_cases,
)
from src.evaluation.runner import (
    DEFAULT_EVAL_PATH,
    STRUCTURED_EVAL_PATH,
    EvaluationCase,
    validate_cases,
)
from src.pipeline.paths import DATA_DIR

EVALUATION_SETS_DIR = DATA_DIR / "evaluation_sets"
AUDIT_LOG_NAME = "audit.jsonl"
REFRESH_QUEUE_NAME = "quality_refresh_queue.jsonl"
MANAGEMENT_SCHEMA_VERSION = "1"
_AUDIT_LOCK = RLock()
_LIFECYCLE_LOCK = RLock()

EVALUATION_SET_DEFINITIONS: dict[str, dict[str, Any]] = {
    "regular": {
        "name": "常规检索评估",
        "builtin_path": DEFAULT_EVAL_PATH,
        "minimum_count": 100,
        "kind": "retrieval",
    },
    "structured": {
        "name": "结构化专项评估",
        "builtin_path": STRUCTURED_EVAL_PATH,
        "minimum_count": 12,
        "kind": "retrieval",
    },
    "answer": {
        "name": "回答级盲测",
        "builtin_path": ANSWER_EVAL_PATH,
        "minimum_count": 24,
        "kind": "answer",
    },
}


class EvaluationSetError(ValueError):
    """Base error for controlled evaluation-set lifecycle operations."""


class EvaluationSetNotFound(EvaluationSetError):
    pass


class EvaluationSetConflict(EvaluationSetError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _audit_path() -> Path:
    return EVALUATION_SETS_DIR / AUDIT_LOG_NAME


def _refresh_queue_path() -> Path:
    return EVALUATION_SETS_DIR / REFRESH_QUEUE_NAME


def _audit_error(exc: Exception) -> str:
    message = str(exc).replace(str(EVALUATION_SETS_DIR), "<evaluation-sets>")
    return f"{type(exc).__name__}: {message[:500]}"


def _snapshot_optional_file(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def _restore_optional_file(path: Path, content: bytes | None) -> None:
    if content is None:
        path.unlink(missing_ok=True)
    else:
        _atomic_write(path, content)


def _record_audit(
    evaluation_set_id: str,
    operation: str,
    status: str,
    *,
    actor: str = "local-maintainer",
    details: dict[str, Any] | None = None,
    error: str = "",
) -> None:
    payload: dict[str, Any] = {
        "event_id": f"ev-{uuid4().hex}",
        "timestamp": _now(),
        "evaluation_set_id": evaluation_set_id,
        "operation": operation,
        "status": status,
        "actor": actor,
    }
    if details:
        payload["details"] = details
    if error:
        payload["error"] = error
    path = _audit_path()
    with _AUDIT_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def list_audit_events(
    evaluation_set_id: str | None = None, *, limit: int = 200
) -> list[dict[str, Any]]:
    if limit <= 0:
        raise ValueError("audit limit 必须大于 0")
    path = _audit_path()
    if not path.is_file():
        return []
    with _AUDIT_LOCK:
        lines = path.read_text(encoding="utf-8").splitlines()
    events: list[dict[str, Any]] = []
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            logging.warning("evaluation_audit_record_invalid")
            continue
        if not isinstance(payload, dict):
            continue
        if evaluation_set_id and payload.get("evaluation_set_id") != evaluation_set_id:
            continue
        events.append(payload)
        if len(events) >= limit:
            break
    return events


def _enqueue_quality_refresh(
    evaluation_set_id: str,
    revision: dict[str, Any],
    *,
    previous_revision_id: str | None,
    actor: str,
) -> dict[str, Any]:
    """Persist a compact durable todo for evaluations affected by a revision."""
    event = {
        "event_id": f"refresh-{uuid4().hex}",
        "created_at": _now(),
        "evaluation_set_id": evaluation_set_id,
        "revision_id": str(revision["revision_id"]),
        "content_hash": str(revision["content_hash"]),
        "previous_revision_id": previous_revision_id,
        "affected_report_types": [evaluation_set_id],
        "actor": actor,
        "status": "pending",
    }
    path = _refresh_queue_path()
    with _AUDIT_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    return event


def list_quality_refresh_events(*, limit: int = 200) -> list[dict[str, Any]]:
    if limit <= 0:
        raise ValueError("refresh queue limit 必须大于 0")
    path = _refresh_queue_path()
    if not path.is_file():
        return []
    with _AUDIT_LOCK:
        lines = path.read_text(encoding="utf-8").splitlines()
    events: list[dict[str, Any]] = []
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            logging.warning("evaluation_refresh_queue_record_invalid")
            continue
        if isinstance(payload, dict):
            events.append(payload)
        if len(events) >= limit:
            break
    return events


def _lifecycle_locked(function):
    @wraps(function)
    def locked(*args, **kwargs):
        with _LIFECYCLE_LOCK:
            return function(*args, **kwargs)

    return locked


def _definition(evaluation_set_id: str) -> dict[str, Any]:
    try:
        return EVALUATION_SET_DEFINITIONS[evaluation_set_id]
    except KeyError as exc:
        raise EvaluationSetNotFound(f"未知评估集：{evaluation_set_id}") from exc


def _set_dir(evaluation_set_id: str) -> Path:
    _definition(evaluation_set_id)
    return EVALUATION_SETS_DIR / evaluation_set_id


def _manifest_path(evaluation_set_id: str) -> Path:
    return _set_dir(evaluation_set_id) / "manifest.json"


def _draft_path(evaluation_set_id: str) -> Path:
    return _set_dir(evaluation_set_id) / "draft.jsonl"


def _revisions_dir(evaluation_set_id: str) -> Path:
    return _set_dir(evaluation_set_id) / "revisions"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvaluationSetNotFound(f"评估集清单不存在：{path.name}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvaluationSetError(f"评估集清单无法读取：{path.name}") from exc
    if not isinstance(payload, dict):
        raise EvaluationSetError(f"评估集清单必须是对象：{path.name}")
    return payload


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _write_manifest(evaluation_set_id: str, manifest: dict[str, Any]) -> None:
    _atomic_write(_manifest_path(evaluation_set_id), _manifest_bytes(manifest))


def _read_rows(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise EvaluationSetError(f"评估集文件无法读取：{path.name}") from exc
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvaluationSetError(f"评估集 JSONL 第 {line_number} 行无法解析") from exc
        if not isinstance(value, dict):
            raise EvaluationSetError(f"评估集 JSONL 第 {line_number} 行必须是对象")
        rows.append(value)
    return rows


def _normalise_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: str(row.get("id", "")))


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in _normalise_rows(rows)
    ).encode("utf-8")


def _content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _type_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        case_type = str(row.get("type") or "unknown")
        counts[case_type] = counts.get(case_type, 0) + 1
    return dict(sorted(counts.items()))


def _builtin_revision(evaluation_set_id: str) -> dict[str, Any]:
    definition = _definition(evaluation_set_id)
    path = Path(definition["builtin_path"])
    if not path.is_file():
        raise EvaluationSetError(f"内置评估集不存在：{evaluation_set_id}")
    rows = _read_rows(path)
    content_hash = _hash_file(path)
    return {
        "revision_id": f"builtin-{content_hash[:12]}",
        "evaluation_set_id": evaluation_set_id,
        "name": definition["name"],
        "status": "published",
        "case_count": len(rows),
        "type_counts": _type_counts(rows),
        "content_hash": content_hash,
        "schema_version": MANAGEMENT_SCHEMA_VERSION,
        "created_at": None,
        "published_at": None,
        "created_by": "builtin",
        "parent_revision_id": None,
        "source": "builtin",
    }


def _default_manifest(evaluation_set_id: str) -> dict[str, Any]:
    revision = _builtin_revision(evaluation_set_id)
    return {
        "schema_version": MANAGEMENT_SCHEMA_VERSION,
        "evaluation_set_id": evaluation_set_id,
        "name": revision["name"],
        "published_revision_id": revision["revision_id"],
        "draft_revision_id": None,
        "draft_content_hash": None,
        "draft_status": None,
        "updated_at": None,
        "updated_by": "builtin",
        "revision_count": 0,
        "revisions": [],
    }


def _manifest(evaluation_set_id: str) -> dict[str, Any]:
    path = _manifest_path(evaluation_set_id)
    return _read_json(path) if path.exists() else _default_manifest(evaluation_set_id)


def _revision_file(evaluation_set_id: str, revision_id: str) -> Path:
    if not revision_id or Path(revision_id).name != revision_id:
        raise EvaluationSetError("非法评估集修订标识")
    return _revisions_dir(evaluation_set_id) / f"{revision_id}.jsonl"


def _revision_from_manifest(
    evaluation_set_id: str, revision_id: str, manifest: dict[str, Any]
) -> dict[str, Any] | None:
    for revision in manifest.get("revisions", []):
        if isinstance(revision, dict) and revision.get("revision_id") == revision_id:
            return dict(revision)
    return None


def _published_revision(
    evaluation_set_id: str, manifest: dict[str, Any] | None = None
) -> dict[str, Any]:
    manifest = manifest or _manifest(evaluation_set_id)
    revision_id = str(manifest.get("published_revision_id") or "")
    builtin = _builtin_revision(evaluation_set_id)
    if revision_id == builtin["revision_id"] and not _manifest_path(evaluation_set_id).exists():
        return builtin
    revision = _revision_from_manifest(evaluation_set_id, revision_id, manifest)
    if not revision:
        if revision_id == builtin["revision_id"]:
            return builtin
        raise EvaluationSetError(f"已发布修订元数据不存在：{revision_id}")
    revision["status"] = "published"
    return revision


def _published_path(evaluation_set_id: str, manifest: dict[str, Any] | None = None) -> Path:
    manifest = manifest or _manifest(evaluation_set_id)
    revision = _published_revision(evaluation_set_id, manifest)
    if revision.get("source") == "builtin":
        return Path(_definition(evaluation_set_id)["builtin_path"])
    path = _revision_file(evaluation_set_id, str(revision["revision_id"]))
    if not path.is_file():
        raise EvaluationSetError(f"已发布评估集文件不存在：{path.name}")
    return path


def resolve_published_asset(evaluation_set_id: str) -> Path:
    """Resolve the immutable server-side asset used by evaluation jobs."""
    return _published_path(evaluation_set_id)


def published_revision_id(evaluation_set_id: str) -> str:
    return str(_published_revision(evaluation_set_id).get("revision_id") or "")


def _draft_rows(evaluation_set_id: str) -> list[dict[str, Any]]:
    path = _draft_path(evaluation_set_id)
    if not path.is_file():
        raise EvaluationSetNotFound(f"评估集没有草稿：{evaluation_set_id}")
    return _read_rows(path)


def _draft_summary(evaluation_set_id: str, manifest: dict[str, Any]) -> dict[str, Any] | None:
    path = _draft_path(evaluation_set_id)
    if not path.is_file():
        return None
    rows = _read_rows(path)
    content = _jsonl_bytes(rows)
    validation = manifest.get("validation_summary")
    if not isinstance(validation, dict) or validation.get("content_hash") != _content_hash(content):
        validation = None
    return {
        "revision_id": "draft",
        "evaluation_set_id": evaluation_set_id,
        "name": str(manifest.get("name") or _definition(evaluation_set_id)["name"]),
        "status": str(manifest.get("draft_status") or "draft"),
        "case_count": len(rows),
        "type_counts": _type_counts(rows),
        "content_hash": _content_hash(content),
        "schema_version": MANAGEMENT_SCHEMA_VERSION,
        "created_at": manifest.get("draft_created_at"),
        "published_at": None,
        "created_by": manifest.get("draft_created_by") or "local-maintainer",
        "parent_revision_id": manifest.get("draft_parent_revision_id"),
        "source": "draft",
        "validation_summary": validation,
    }


def _summary(evaluation_set_id: str, revision: dict[str, Any]) -> dict[str, Any]:
    result = dict(revision)
    result.setdefault("name", _definition(evaluation_set_id)["name"])
    result.setdefault("type_counts", {})
    result.setdefault("source", "managed")
    return result


def list_sets() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for evaluation_set_id in EVALUATION_SET_DEFINITIONS:
        manifest = _manifest(evaluation_set_id)
        published = _summary(evaluation_set_id, _published_revision(evaluation_set_id, manifest))
        draft = _draft_summary(evaluation_set_id, manifest)
        result.append(
            {
                "evaluation_set_id": evaluation_set_id,
                "name": str(manifest.get("name") or published["name"]),
                "kind": _definition(evaluation_set_id)["kind"],
                "published_revision": published,
                "draft": draft,
                "case_count": int(published.get("case_count", 0)),
                "updated_at": manifest.get("updated_at") or published.get("published_at"),
            }
        )
    return result


def _migrated_revision(
    evaluation_set_id: str,
    rows: list[dict[str, Any]],
    content: bytes,
    *,
    actor: str,
) -> dict[str, Any]:
    content_hash = _content_hash(content)
    now = _now()
    return {
        "revision_id": f"r-migrated-{content_hash[:12]}",
        "evaluation_set_id": evaluation_set_id,
        "name": _definition(evaluation_set_id)["name"],
        "status": "published",
        "case_count": len(rows),
        "type_counts": _type_counts(rows),
        "content_hash": content_hash,
        "schema_version": MANAGEMENT_SCHEMA_VERSION,
        "created_at": now,
        "published_at": now,
        "created_by": actor,
        "parent_revision_id": None,
        "source": "builtin_migrated",
    }


@_lifecycle_locked
def migrate_builtin_asset(
    evaluation_set_id: str,
    *,
    actor: str = "local-maintainer",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Materialize one builtin asset as the first managed published revision.

    The operation is intentionally explicit: normal reads may continue using the
    builtin fallback, while this command creates a durable DATA_DIR-owned source.
    """
    definition = _definition(evaluation_set_id)
    manifest_path = _manifest_path(evaluation_set_id)
    draft_path = _draft_path(evaluation_set_id)
    manifest = _manifest(evaluation_set_id)
    previous_manifest = deepcopy(manifest)
    manifest_existed = manifest_path.is_file()
    refresh_queue_path = _refresh_queue_path()
    previous_refresh_queue = _snapshot_optional_file(refresh_queue_path)
    current_id = str(manifest.get("published_revision_id") or "")
    current = _revision_from_manifest(evaluation_set_id, current_id, manifest)
    if current is not None and current.get("source") != "builtin":
        result = {
            "evaluation_set_id": evaluation_set_id,
            "status": "unchanged",
            "revision": _summary(evaluation_set_id, current),
            "reason": "已有受控发布修订",
        }
        _record_audit(
            evaluation_set_id,
            "builtin_migration",
            "unchanged",
            actor=actor,
            details={"revision_id": current.get("revision_id")},
        )
        return result
    if draft_path.exists():
        error = "评估集已有草稿，迁移不会覆盖草稿；请先处理草稿"
        _record_audit(evaluation_set_id, "builtin_migration", "failed", actor=actor, error=error)
        raise EvaluationSetConflict(error)

    builtin_path = Path(definition["builtin_path"])
    if not builtin_path.is_file():
        raise EvaluationSetError(f"内置评估集不存在：{evaluation_set_id}")
    rows = _read_rows(builtin_path)
    content = _jsonl_bytes(rows)
    revision = _migrated_revision(evaluation_set_id, rows, content, actor=actor)
    revision_path = _revision_file(evaluation_set_id, str(revision["revision_id"]))
    existing_revision = _revision_from_manifest(
        evaluation_set_id, str(revision["revision_id"]), manifest
    )
    if existing_revision is not None:
        if not revision_path.is_file() or _hash_file(revision_path) != revision["content_hash"]:
            raise EvaluationSetError("迁移修订元数据与文件内容不一致")
        revision = existing_revision
        created_file = False
    else:
        if revision_path.exists() and _hash_file(revision_path) != revision["content_hash"]:
            raise EvaluationSetConflict("迁移目标修订文件已存在但内容不一致")
        created_file = not revision_path.exists()

    if dry_run:
        return {
            "evaluation_set_id": evaluation_set_id,
            "status": "planned",
            "revision": _summary(evaluation_set_id, revision),
            "content_hash": revision["content_hash"],
        }

    if created_file:
        _atomic_write(revision_path, content)
    revisions = [
        item
        for item in manifest.get("revisions", [])
        if isinstance(item, dict) and item.get("revision_id") != revision["revision_id"]
    ]
    revisions.append(revision)
    manifest.update(
        {
            "published_revision_id": revision["revision_id"],
            "draft_revision_id": None,
            "draft_content_hash": None,
            "draft_status": None,
            "validation_summary": None,
            "updated_at": revision["published_at"],
            "updated_by": actor,
            "revision_count": len(revisions),
            "revisions": revisions,
        }
    )
    try:
        _write_manifest(evaluation_set_id, manifest)
    except Exception as exc:
        if created_file:
            revision_path.unlink(missing_ok=True)
        _record_audit(
            evaluation_set_id,
            "builtin_migration",
            "failed",
            actor=actor,
            details={"revision_id": revision["revision_id"]},
            error=_audit_error(exc),
        )
        raise
    try:
        _enqueue_quality_refresh(
            evaluation_set_id,
            revision,
            previous_revision_id=current_id or None,
            actor=actor,
        )
    except Exception as exc:
        try:
            if manifest_existed:
                _atomic_write(manifest_path, _manifest_bytes(previous_manifest))
            else:
                manifest_path.unlink(missing_ok=True)
            if created_file:
                revision_path.unlink(missing_ok=True)
            _restore_optional_file(refresh_queue_path, previous_refresh_queue)
        except Exception:
            logging.exception("evaluation_set_migration_rollback_failed")
        _record_audit(
            evaluation_set_id,
            "builtin_migration",
            "failed",
            actor=actor,
            details={"revision_id": revision["revision_id"]},
            error=_audit_error(exc),
        )
        raise
    result = {
        "evaluation_set_id": evaluation_set_id,
        "status": "migrated",
        "revision": _summary(evaluation_set_id, revision),
        "content_hash": revision["content_hash"],
        "manifest": str(manifest_path),
    }
    _record_audit(
        evaluation_set_id,
        "builtin_migration",
        "completed",
        actor=actor,
        details={
            "revision_id": revision["revision_id"],
            "content_hash": revision["content_hash"],
            "case_count": len(rows),
        },
    )
    return result


@_lifecycle_locked
def migrate_builtin_assets(
    evaluation_set_id: str | None = None,
    *,
    actor: str = "local-maintainer",
    dry_run: bool = False,
) -> dict[str, Any]:
    ids = [evaluation_set_id] if evaluation_set_id else list(EVALUATION_SET_DEFINITIONS)
    results = [migrate_builtin_asset(item, actor=actor, dry_run=dry_run) for item in ids]
    return {
        "dry_run": dry_run,
        "results": results,
        "migrated_count": sum(item["status"] == "migrated" for item in results),
        "unchanged_count": sum(item["status"] == "unchanged" for item in results),
        "planned_count": sum(item["status"] == "planned" for item in results),
    }


def list_revisions(evaluation_set_id: str) -> list[dict[str, Any]]:
    manifest = _manifest(evaluation_set_id)
    revisions = [_builtin_revision(evaluation_set_id)]
    revisions.extend(
        _summary(evaluation_set_id, revision)
        for revision in manifest.get("revisions", [])
        if isinstance(revision, dict)
    )
    unique: dict[str, dict[str, Any]] = {str(item["revision_id"]): item for item in revisions}
    return sorted(
        unique.values(),
        key=lambda item: str(item.get("published_at") or item.get("created_at") or ""),
        reverse=True,
    )


def read_revision(
    evaluation_set_id: str, revision_id: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = _manifest(evaluation_set_id)
    builtin = _builtin_revision(evaluation_set_id)
    if revision_id == builtin["revision_id"]:
        revision = builtin
        path = Path(_definition(evaluation_set_id)["builtin_path"])
    else:
        revision = _revision_from_manifest(evaluation_set_id, revision_id, manifest)
        if revision is None:
            raise EvaluationSetNotFound(f"评估集修订不存在：{revision_id}")
        path = _revision_file(evaluation_set_id, revision_id)
    if not path.is_file():
        raise EvaluationSetNotFound(f"评估集修订文件不存在：{revision_id}")
    rows = _read_rows(path)
    return _summary(evaluation_set_id, revision), rows


def read_set(evaluation_set_id: str) -> dict[str, Any]:
    manifest = _manifest(evaluation_set_id)
    published = _published_revision(evaluation_set_id, manifest)
    revision, cases = read_revision(evaluation_set_id, str(published["revision_id"]))
    draft_cases = _draft_rows(evaluation_set_id) if _draft_path(evaluation_set_id).is_file() else []
    return {
        "evaluation_set_id": evaluation_set_id,
        "name": str(manifest.get("name") or published["name"]),
        "kind": _definition(evaluation_set_id)["kind"],
        "published_revision": revision,
        "draft": _draft_summary(evaluation_set_id, manifest),
        "case_count": len(cases),
        "type_counts": _type_counts(cases),
        "cases": cases,
        "draft_cases": draft_cases,
    }


def _update_draft_manifest(
    evaluation_set_id: str,
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    validation_summary: dict[str, Any] | None = None,
    audit_operation: str = "draft_update",
    audit_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    content = _jsonl_bytes(rows)
    manifest_path = _manifest_path(evaluation_set_id)
    draft_path = _draft_path(evaluation_set_id)
    previous_manifest = deepcopy(manifest)
    manifest_existed = manifest_path.is_file()
    previous_draft = _snapshot_optional_file(draft_path)
    try:
        _atomic_write(draft_path, content)
        manifest["draft_revision_id"] = "draft"
        manifest["draft_content_hash"] = _content_hash(content)
        manifest["draft_status"] = (
            "validated" if validation_summary and validation_summary.get("ok") else "draft"
        )
        manifest["validation_summary"] = validation_summary
        manifest["updated_at"] = _now()
        manifest["updated_by"] = "local-maintainer"
        _write_manifest(evaluation_set_id, manifest)
    except Exception as exc:
        try:
            if manifest_existed:
                _atomic_write(manifest_path, _manifest_bytes(previous_manifest))
            else:
                manifest_path.unlink(missing_ok=True)
            _restore_optional_file(draft_path, previous_draft)
        except Exception:
            logging.exception("evaluation_set_draft_rollback_failed")
        _record_audit(
            evaluation_set_id,
            audit_operation,
            "failed",
            details=audit_details,
            error=_audit_error(exc),
        )
        raise
    result = {
        "evaluation_set_id": evaluation_set_id,
        "draft_status": manifest["draft_status"],
        "draft": _draft_summary(evaluation_set_id, manifest),
        "case_count": len(rows),
        "type_counts": _type_counts(rows),
        "cases": rows,
    }
    _record_audit(
        evaluation_set_id,
        audit_operation,
        "completed",
        details={"draft_content_hash": manifest["draft_content_hash"], **(audit_details or {})},
    )
    return result


@_lifecycle_locked
def create_draft(evaluation_set_id: str, *, reset: bool = False) -> dict[str, Any]:
    manifest = _manifest(evaluation_set_id)
    if _draft_path(evaluation_set_id).exists() and not reset:
        error = "评估集已有草稿；如需覆盖请显式请求 reset"
        _record_audit(evaluation_set_id, "draft_create", "failed", error=error)
        raise EvaluationSetConflict(error)
    rows = _read_rows(_published_path(evaluation_set_id, manifest))
    manifest["draft_created_at"] = _now()
    manifest["draft_created_by"] = "local-maintainer"
    manifest["draft_parent_revision_id"] = manifest.get("published_revision_id")
    return _update_draft_manifest(
        evaluation_set_id,
        manifest,
        rows,
        audit_operation="draft_reset" if reset else "draft_create",
        audit_details={"parent_revision_id": manifest.get("draft_parent_revision_id")},
    )


def _case_index(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        str(row.get("id")): index for index, row in enumerate(rows) if row.get("id") is not None
    }


@_lifecycle_locked
def update_case(evaluation_set_id: str, case_id: str, case: dict[str, Any]) -> dict[str, Any]:
    if str(case.get("id") or "") != case_id:
        error = "请求路径中的用例 ID 必须与 case.id 一致"
        _record_audit(
            evaluation_set_id, "case_update", "failed", details={"case_id": case_id}, error=error
        )
        raise EvaluationSetError(error)
    manifest = _manifest(evaluation_set_id)
    rows = _draft_rows(evaluation_set_id)
    index = _case_index(rows).get(case_id)
    if index is None:
        error = f"草稿用例不存在：{case_id}"
        _record_audit(
            evaluation_set_id, "case_update", "failed", details={"case_id": case_id}, error=error
        )
        raise EvaluationSetNotFound(error)
    rows[index] = dict(case)
    return _update_draft_manifest(
        evaluation_set_id,
        manifest,
        rows,
        audit_operation="case_update",
        audit_details={"case_id": case_id},
    )


@_lifecycle_locked
def add_case(evaluation_set_id: str, case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case.get("id") or "")
    if not case_id:
        error = "新增用例必须提供 id"
        _record_audit(evaluation_set_id, "case_add", "failed", error=error)
        raise EvaluationSetError(error)
    manifest = _manifest(evaluation_set_id)
    rows = _draft_rows(evaluation_set_id)
    if case_id in _case_index(rows):
        error = f"草稿用例 ID 已存在：{case_id}"
        _record_audit(
            evaluation_set_id, "case_add", "failed", details={"case_id": case_id}, error=error
        )
        raise EvaluationSetConflict(error)
    rows.append(dict(case))
    return _update_draft_manifest(
        evaluation_set_id,
        manifest,
        rows,
        audit_operation="case_add",
        audit_details={"case_id": case_id},
    )


@_lifecycle_locked
def delete_case(evaluation_set_id: str, case_id: str) -> dict[str, Any]:
    manifest = _manifest(evaluation_set_id)
    rows = _draft_rows(evaluation_set_id)
    if case_id not in _case_index(rows):
        error = f"草稿用例不存在：{case_id}"
        _record_audit(
            evaluation_set_id, "case_delete", "failed", details={"case_id": case_id}, error=error
        )
        raise EvaluationSetNotFound(error)
    rows = [row for row in rows if str(row.get("id")) != case_id]
    result = _update_draft_manifest(
        evaluation_set_id,
        manifest,
        rows,
        audit_operation="case_delete",
        audit_details={"case_id": case_id},
    )
    result["deleted_case_id"] = case_id
    return result


def _build_validation_cases(
    evaluation_set_id: str, rows: list[dict[str, Any]]
) -> tuple[list[str], dict[str, int]]:
    definition = _definition(evaluation_set_id)
    errors: list[str] = []
    if evaluation_set_id == "answer":
        cases: list[AnswerEvaluationCase] = []
        for index, row in enumerate(rows, start=1):
            try:
                cases.append(
                    AnswerEvaluationCase(
                        id=str(row.get("id") or ""),
                        query=str(row.get("query") or ""),
                        type=str(row.get("type") or ""),
                        expected_all=[str(value) for value in row.get("expected_all", [])],
                        expected_any_groups=[
                            [str(value) for value in group]
                            for group in row.get("expected_any_groups", [])
                        ],
                        forbidden_terms=[str(value) for value in row.get("forbidden_terms", [])],
                        expected_citations=[
                            str(value) for value in row.get("expected_citations", [])
                        ],
                        expected_unit_groups=[
                            [str(value) for value in group]
                            for group in row.get("expected_unit_groups", [])
                        ],
                        requires_refusal=bool(row.get("requires_refusal", False)),
                        requires_image=bool(row.get("requires_image", True)),
                    )
                )
            except (TypeError, ValueError) as exc:
                errors.append(f"line-{index}: 字段类型错误：{exc}")
        if not errors:
            errors.extend(
                validate_answer_cases(cases, minimum_count=int(definition["minimum_count"]))
            )
    else:
        cases = []
        for index, row in enumerate(rows, start=1):
            try:
                cases.append(
                    EvaluationCase(
                        id=str(row.get("id") or ""),
                        query=str(row.get("query") or ""),
                        expected_sources=[str(value) for value in row.get("expected_sources", [])],
                        expected_clause=str(row.get("expected_clause") or ""),
                        expected_keywords=[
                            str(value) for value in row.get("expected_keywords", [])
                        ],
                        type=str(row.get("type") or "general"),
                        expected_authority_type=str(row.get("expected_authority_type") or ""),
                        top1_source_required=bool(row.get("top1_source_required", True)),
                        keyword_required=bool(row.get("keyword_required", True)),
                        expected_table_id=str(row.get("expected_table_id") or ""),
                    )
                )
            except (TypeError, ValueError) as exc:
                errors.append(f"line-{index}: 字段类型错误：{exc}")
        if not errors:
            errors.extend(validate_cases(cases, minimum_count=int(definition["minimum_count"])))
    ids = [str(row.get("id") or "") for row in rows]
    duplicates = sorted({case_id for case_id in ids if ids.count(case_id) > 1 and case_id})
    errors.extend(f"id 重复：{case_id}" for case_id in duplicates)
    query_counts: dict[str, int] = {}
    for row in rows:
        query = str(row.get("query") or "").strip()
        if query:
            query_counts[query] = query_counts.get(query, 0) + 1
    return errors, _type_counts(rows)


@_lifecycle_locked
def validate_draft(evaluation_set_id: str) -> dict[str, Any]:
    manifest = _manifest(evaluation_set_id)
    rows = _draft_rows(evaluation_set_id)
    content = _jsonl_bytes(rows)
    content_hash = _content_hash(content)
    errors, type_counts = _build_validation_cases(evaluation_set_id, rows)
    queries = [str(row.get("query") or "").strip() for row in rows]
    query_counts: dict[str, int] = {}
    for query in queries:
        if query:
            query_counts[query] = query_counts.get(query, 0) + 1
    duplicate_queries = sum(max(0, count - 1) for count in query_counts.values())
    warnings = [f"存在 {duplicate_queries} 个重复问题"] if duplicate_queries else []
    summary = {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "case_count": len(rows),
        "type_counts": type_counts,
        "content_hash": content_hash,
        "validated_at": _now(),
    }
    manifest["validation_summary"] = summary
    manifest["draft_status"] = "validated" if not errors else "invalid"
    manifest["draft_content_hash"] = content_hash
    manifest["updated_at"] = _now()
    manifest["updated_by"] = "local-maintainer"
    _write_manifest(evaluation_set_id, manifest)
    result = {
        "evaluation_set_id": evaluation_set_id,
        "draft_status": manifest["draft_status"],
        "validation": summary,
    }
    _record_audit(
        evaluation_set_id,
        "draft_validate",
        "completed",
        details={
            "draft_content_hash": content_hash,
            "ok": summary["ok"],
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
    )
    return result


def diff_draft(evaluation_set_id: str) -> dict[str, Any]:
    manifest = _manifest(evaluation_set_id)
    draft = _draft_rows(evaluation_set_id)
    published_revision = _published_revision(evaluation_set_id, manifest)
    _, published = read_revision(evaluation_set_id, str(published_revision["revision_id"]))
    before = {str(row.get("id")): row for row in published}
    after = {str(row.get("id")): row for row in draft}
    added = [after[case_id] for case_id in sorted(after.keys() - before.keys())]
    removed = [before[case_id] for case_id in sorted(before.keys() - after.keys())]
    modified = [
        {"id": case_id, "before": before[case_id], "after": after[case_id]}
        for case_id in sorted(before.keys() & after.keys())
        if before[case_id] != after[case_id]
    ]
    return {
        "evaluation_set_id": evaluation_set_id,
        "base_revision_id": published_revision["revision_id"],
        "draft_content_hash": _content_hash(_jsonl_bytes(draft)),
        "added": added,
        "removed": removed,
        "modified": modified,
        "changed_count": len(added) + len(removed) + len(modified),
    }


def _publish_rows(
    evaluation_set_id: str,
    rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    parent_revision_id: str,
    audit_operation: str = "draft_publish",
    actor: str = "local-maintainer",
) -> dict[str, Any]:
    previous_manifest = deepcopy(manifest)
    draft_path = _draft_path(evaluation_set_id)
    previous_draft = draft_path.read_bytes() if draft_path.is_file() else None
    refresh_queue_path = _refresh_queue_path()
    previous_refresh_queue = _snapshot_optional_file(refresh_queue_path)
    content = _jsonl_bytes(rows)
    content_hash = _content_hash(content)
    revision_id = f"r-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}-{content_hash[:12]}"
    path = _revision_file(evaluation_set_id, revision_id)
    revision = {
        "revision_id": revision_id,
        "evaluation_set_id": evaluation_set_id,
        "name": str(manifest.get("name") or _definition(evaluation_set_id)["name"]),
        "status": "published",
        "case_count": len(rows),
        "type_counts": _type_counts(rows),
        "content_hash": content_hash,
        "schema_version": MANAGEMENT_SCHEMA_VERSION,
        "created_at": _now(),
        "published_at": _now(),
        "created_by": actor,
        "parent_revision_id": parent_revision_id,
        "source": "managed",
    }
    revisions = [item for item in manifest.get("revisions", []) if isinstance(item, dict)]
    revisions = [item for item in revisions if item.get("revision_id") != revision_id]
    revisions.append(revision)
    manifest.update(
        {
            "published_revision_id": revision_id,
            "draft_revision_id": None,
            "draft_content_hash": None,
            "draft_status": None,
            "validation_summary": None,
            "updated_at": revision["published_at"],
            "updated_by": actor,
            "revision_count": len(revisions),
            "revisions": revisions,
        }
    )
    revision_created = False
    try:
        if path.exists():
            raise EvaluationSetConflict(f"评估集修订标识已存在：{revision_id}")
        _atomic_write(path, content)
        revision_created = True
        _write_manifest(evaluation_set_id, manifest)
        draft_path.unlink(missing_ok=True)
        _enqueue_quality_refresh(
            evaluation_set_id,
            revision,
            previous_revision_id=parent_revision_id,
            actor=actor,
        )
    except Exception as exc:
        try:
            _write_manifest(evaluation_set_id, previous_manifest)
            if previous_draft is None:
                draft_path.unlink(missing_ok=True)
            else:
                _atomic_write(draft_path, previous_draft)
            if revision_created:
                path.unlink(missing_ok=True)
            _restore_optional_file(refresh_queue_path, previous_refresh_queue)
        except Exception:
            logging.exception("evaluation_set_publish_rollback_failed")
        _record_audit(
            evaluation_set_id,
            audit_operation,
            "failed",
            actor=actor,
            details={"parent_revision_id": parent_revision_id},
            error=_audit_error(exc),
        )
        raise
    result = {
        "evaluation_set_id": evaluation_set_id,
        "previous_revision_id": parent_revision_id,
        "revision": revision,
        "affected_report_types": [evaluation_set_id],
    }
    _record_audit(
        evaluation_set_id,
        audit_operation,
        "completed",
        actor=actor,
        details={
            "previous_revision_id": parent_revision_id,
            "revision_id": revision_id,
            "content_hash": content_hash,
            "case_count": len(rows),
        },
    )
    return result


@_lifecycle_locked
def publish_draft(evaluation_set_id: str) -> dict[str, Any]:
    manifest = _manifest(evaluation_set_id)
    rows = _draft_rows(evaluation_set_id)
    current_hash = _content_hash(_jsonl_bytes(rows))
    validation = manifest.get("validation_summary")
    if not isinstance(validation, dict) or validation.get("content_hash") != current_hash:
        error = "草稿尚未按当前内容完成校验"
        _record_audit(evaluation_set_id, "draft_publish", "failed", error=error)
        raise EvaluationSetConflict(error)
    if validation.get("ok") is not True:
        error = "草稿校验未通过，不能发布"
        _record_audit(evaluation_set_id, "draft_publish", "failed", error=error)
        raise EvaluationSetConflict(error)
    parent = str(manifest.get("published_revision_id") or "")
    return _publish_rows(evaluation_set_id, rows, manifest, parent_revision_id=parent)


@_lifecycle_locked
def rollback(evaluation_set_id: str, revision_id: str) -> dict[str, Any]:
    manifest = _manifest(evaluation_set_id)
    _, rows = read_revision(evaluation_set_id, revision_id)
    return _publish_rows(
        evaluation_set_id,
        rows,
        manifest,
        parent_revision_id=revision_id,
        audit_operation="revision_rollback",
    )
