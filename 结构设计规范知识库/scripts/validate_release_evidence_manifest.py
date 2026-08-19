from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTER_PATH = PROJECT_ROOT / "docs" / "governance" / "来源登记台账.json"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
STATUSES = {"pending", "verified", "not_applicable"}
SECRET_KEYS = {
    "api_key",
    "apikey",
    "access_token",
    "authorization",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
}
SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{20,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{16,}"),
)
REQUIRED_EVIDENCE = ("acquisition", "rights_review", "storage_disposition")


class EvidenceManifestError(ValueError):
    def __init__(self, issues: list[str] | str):
        self.issues = [issues] if isinstance(issues, str) else list(issues)
        super().__init__("；".join(self.issues))


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceManifestError(f"{label}不存在：{path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceManifestError(f"{label}无法读取或不是有效 UTF-8 JSON：{path}") from exc
    if not isinstance(value, dict):
        raise EvidenceManifestError(f"{label}根节点必须是对象")
    return value


def _required_string(value: Any, label: str, issues: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{label}必须是非空字符串")
        return ""
    return value.strip()


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _validate_no_secrets(value: Any, path: str, issues: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_name = str(key).strip().lower().replace("-", "_")
            if key_name in SECRET_KEYS:
                issues.append(f"{path}.{key}禁止保存密钥、令牌或凭据")
            _validate_no_secrets(item, f"{path}.{key}", issues)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_no_secrets(item, f"{path}[{index}]", issues)
    elif isinstance(value, str) and any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS):
        issues.append(f"{path}疑似包含访问令牌，必须删除后再保存")


def _relative_evidence_path(
    raw_path: Any,
    label: str,
    manifest_root: Path,
    issues: list[str],
) -> Path | None:
    if raw_path in (None, ""):
        return None
    if not isinstance(raw_path, str) or not raw_path.strip():
        issues.append(f"{label}.path必须是相对路径")
        return None
    candidate = Path(raw_path)
    if candidate.is_absolute():
        issues.append(f"{label}.path不能是绝对路径")
        return None
    resolved = (manifest_root / candidate).resolve()
    try:
        resolved.relative_to(manifest_root.resolve())
    except ValueError:
        issues.append(f"{label}.path不能越出 manifest 所在受限目录")
        return None
    return resolved


def _validate_file_evidence(
    value: Any,
    label: str,
    manifest_root: Path,
    issues: list[str],
    gaps: list[dict[str, Any]],
    *,
    required: bool,
) -> None:
    if not isinstance(value, dict):
        if required:
            issues.append(f"{label}必须是对象")
        return
    status = _required_string(value.get("status"), f"{label}.status", issues)
    if status and status not in STATUSES:
        issues.append(f"{label}.status不受支持：{status}")
    reference = value.get("reference")
    path = _relative_evidence_path(value.get("path"), label, manifest_root, issues)
    digest = value.get("sha256")
    if digest not in (None, "") and (
        not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest.lower())
    ):
        issues.append(f"{label}.sha256必须是 64 位小写 SHA-256")
    complete = status == "verified" and isinstance(reference, str) and bool(reference.strip())
    if path is not None:
        if not path.is_file():
            gaps.append({"id": label, "status": "missing", "detail": "引用文件不存在"})
        elif digest:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != str(digest).lower():
                issues.append(f"{label}.sha256与引用文件不匹配")
            else:
                complete = complete and True
        else:
            gaps.append({"id": label, "status": "incomplete", "detail": "引用文件缺少 SHA-256"})
    if required and not complete:
        gaps.append({"id": label, "status": status or "missing", "detail": "证据引用尚未核验完成"})


def _source_register_sources(path: Path) -> tuple[dict[str, str], str]:
    register = _load_json(path.resolve(), "来源登记台账")
    records = register.get("documents")
    if not isinstance(records, list):
        raise EvidenceManifestError("来源登记台账 documents 必须是数组")
    sources = {
        str(item.get("source_id") or ""): str(item.get("source_file") or "")
        for item in records
        if isinstance(item, dict) and item.get("release_scope") == "production"
    }
    if not sources or not all(sources) or not all(sources.values()):
        raise EvidenceManifestError("来源登记台账 production 来源缺少 source_id")
    return sources, str(register.get("updated_at") or "")


def validate_release_evidence_manifest(
    manifest_path: Path,
    *,
    source_register_path: Path = DEFAULT_REGISTER_PATH,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = _load_json(manifest_path, "发布证据包索引")
    issues: list[str] = []
    gaps: list[dict[str, Any]] = []
    _validate_no_secrets(manifest, "$", issues)
    if manifest.get("schema_version") != 1:
        issues.append("schema_version必须是 1")
    updated_at = _required_string(manifest.get("updated_at"), "updated_at", issues)
    if updated_at:
        try:
            date.fromisoformat(updated_at)
        except ValueError:
            issues.append("updated_at必须是 ISO 8601 日期")
    status = _required_string(manifest.get("status"), "status", issues)
    if status and status not in {"draft", "ready"}:
        issues.append(f"status不受支持：{status}")
    expected_sources, register_date = _source_register_sources(source_register_path)
    expected_ids = sorted(expected_sources)
    source_register_version = _required_string(
        manifest.get("source_register_version"), "source_register_version", issues
    )
    if register_date and source_register_version != f"source-register-{register_date}":
        gaps.append(
            {
                "id": "source_register_version",
                "status": "stale",
                "detail": "索引引用的来源登记版本不是当前台账版本",
            }
        )

    sources = manifest.get("sources")
    if not isinstance(sources, list):
        issues.append("sources必须是数组")
        sources = []
    actual_ids: list[str] = []
    for index, source in enumerate(sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            issues.append(f"{label}必须是对象")
            continue
        source_id = _required_string(source.get("source_id"), f"{label}.source_id", issues)
        actual_ids.append(source_id)
        source_file = _required_string(source.get("source_file"), f"{label}.source_file", issues)
        if source_id in expected_sources and source_file != expected_sources[source_id]:
            issues.append(
                f"{label}.source_file与来源登记台账不一致："
                f"台账={expected_sources[source_id]}，索引={source_file}"
            )
        evidence = source.get("evidence")
        if not isinstance(evidence, dict):
            issues.append(f"{label}.evidence必须是对象")
            evidence = {}
        for evidence_id in REQUIRED_EVIDENCE:
            _validate_file_evidence(
                evidence.get(evidence_id),
                f"{label}.evidence.{evidence_id}",
                manifest_path.parent,
                issues,
                gaps,
                required=True,
            )
        reviewed_by = source.get("reviewed_by")
        reviewed_at = source.get("reviewed_at")
        if not isinstance(reviewed_by, str) or not reviewed_by.strip():
            gaps.append(
                {"id": f"{label}.reviewed_by", "status": "missing", "detail": "缺少复核责任人"}
            )
        if not isinstance(reviewed_at, str) or not reviewed_at.strip():
            gaps.append(
                {"id": f"{label}.reviewed_at", "status": "missing", "detail": "缺少复核日期"}
            )
        elif not _is_iso_date(reviewed_at):
            issues.append(f"{label}.reviewed_at必须是 ISO 8601 日期")
    if sorted(actual_ids) != expected_ids:
        issues.append(
            "sources 必须与来源登记台账 production source_id 一一对应："
            f"期望={expected_ids}，实际={sorted(actual_ids)}"
        )

    decisions = manifest.get("decisions")
    if not isinstance(decisions, dict):
        issues.append("decisions必须是对象")
        decisions = {}
    for decision_id in ("D-001", "D-002"):
        value = decisions.get(decision_id)
        label = f"decisions.{decision_id}"
        if not isinstance(value, dict):
            issues.append(f"{label}必须是对象")
            continue
        decision_status = _required_string(value.get("status"), f"{label}.status", issues)
        if decision_status not in {"pending", "approved"}:
            issues.append(f"{label}.status必须是 pending 或 approved")
        reference = value.get("reference")
        if decision_status == "approved" and (
            not isinstance(reference, str) or not reference.strip()
        ):
            gaps.append({"id": label, "status": "incomplete", "detail": "已批准决策缺少证据引用"})
        elif decision_status != "approved":
            gaps.append(
                {"id": label, "status": decision_status or "missing", "detail": "决策尚未批准"}
            )

    trial = manifest.get("trial")
    if not isinstance(trial, dict):
        issues.append("trial必须是对象")
        trial = {}
    trial_status = _required_string(trial.get("status"), "trial.status", issues)
    if trial_status not in {"pending", "verified"}:
        issues.append("trial.status必须是 pending 或 verified")
    trial_record = trial.get("record")
    if trial_status == "verified":
        _validate_file_evidence(
            trial_record,
            "trial.record",
            manifest_path.parent,
            issues,
            gaps,
            required=True,
        )
        if isinstance(trial_record, dict) and isinstance(trial_record.get("path"), str):
            record_path = _relative_evidence_path(
                trial_record.get("path"), "trial.record", manifest_path.parent, issues
            )
            if record_path is not None and record_path.is_file():
                from scripts.validate_trial_record import validate_trial_record

                result = validate_trial_record(record_path)
                if not result.get("ok") or result.get("status") != "completed":
                    gaps.append(
                        {
                            "id": "trial.record",
                            "status": "invalid",
                            "detail": "试用记录未通过校验或状态不是 completed",
                        }
                    )
    else:
        gaps.append(
            {"id": "trial", "status": trial_status or "missing", "detail": "真实试用证据尚未收口"}
        )

    rerank = manifest.get("rerank")
    if not isinstance(rerank, dict):
        issues.append("rerank必须是对象")
        rerank = {}
    rerank_status = _required_string(rerank.get("status"), "rerank.status", issues)
    if rerank_status not in {"disabled", "verified"}:
        issues.append("rerank.status必须是 disabled 或 verified")
    if rerank_status == "verified":
        for field in ("comparison_report", "answer_report"):
            _validate_file_evidence(
                rerank.get(field),
                f"rerank.{field}",
                manifest_path.parent,
                issues,
                gaps,
                required=True,
            )

    if issues:
        raise EvidenceManifestError(issues)
    blocking_gaps = [item for item in gaps if not str(item.get("id") or "").startswith("rerank.")]
    return {
        "ok": True,
        "ready": not blocking_gaps,
        "manifest_path": str(manifest_path),
        "status": status,
        "source_count": len(expected_ids),
        "gap_count": len(gaps),
        "gaps": gaps,
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="校验受控发布证据包索引")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-register", type=Path, default=DEFAULT_REGISTER_PATH)
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="额外要求来源、试用和决策证据全部收口",
    )
    args = parser.parse_args()
    try:
        result = validate_release_evidence_manifest(
            args.manifest, source_register_path=args.source_register
        )
    except EvidenceManifestError as exc:
        result = {
            "ok": False,
            "ready": False,
            "error": "evidence_manifest_invalid",
            "issues": exc.issues,
        }
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if not result.get("ok"):
        return 1
    if args.require_ready and not result.get("ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
