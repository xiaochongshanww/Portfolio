from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from src.pipeline.active_db import resolve_pointer_path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTER_PATH = PROJECT_ROOT / "docs" / "governance" / "来源登记台账.json"
DEFAULT_METADATA_PATH = PROJECT_ROOT / "data" / "metadata" / "specs.json"
DEFAULT_SOURCE_ROOT = PROJECT_ROOT / "data" / "raw"
DEFAULT_ACTIVE_DB_PATH = PROJECT_ROOT / "data" / "active_db.json"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RIGHTS_STATUSES = {"A", "B", "C", "test_fixture"}
RELEASE_SCOPES = {"production", "test_only"}
TAKEDOWN_STATUSES = {"active", "suspended", "removed"}
REQUIRED_RECORD_FIELDS = {
    "source_id",
    "source_file",
    "standard_code",
    "title",
    "version",
    "source_kind",
    "release_scope",
    "original_sha256",
    "acquisition",
    "rights",
    "permissions",
    "processing",
    "review",
    "takedown",
    "repository_storage",
    "derived_asset_policy",
}
REQUIRED_PERMISSION_FIELDS = {
    "page_screenshot",
    "original_excerpt",
    "table_export",
    "external_retrieval",
    "paid_service",
}


class SourceRegisterError(ValueError):
    def __init__(self, issues: list[str] | str):
        self.issues = [issues] if isinstance(issues, str) else list(issues)
        super().__init__("；".join(self.issues))


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SourceRegisterError(f"{label}不存在：{path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceRegisterError(f"{label}无法读取或不是有效 UTF-8 JSON：{path}") from exc
    if not isinstance(value, dict):
        raise SourceRegisterError(f"{label}根节点必须是对象：{path}")
    return value


def _object(value: Any, label: str, issues: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        issues.append(f"{label}必须是对象")
        return {}
    return value


def _string(value: Any, label: str, issues: list[str], *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        issues.append(f"{label}必须是非空字符串")
        return ""
    return value.strip()


def _validate_record_shape(record: dict[str, Any], index: int, issues: list[str]) -> None:
    prefix = f"documents[{index}]"
    missing = sorted(REQUIRED_RECORD_FIELDS - set(record))
    if missing:
        issues.append(f"{prefix}缺少字段：{', '.join(missing)}")

    source_file = _string(record.get("source_file"), f"{prefix}.source_file", issues)
    _string(record.get("source_id"), f"{prefix}.source_id", issues)
    _string(record.get("standard_code"), f"{prefix}.standard_code", issues)
    _string(record.get("title"), f"{prefix}.title", issues)
    _string(record.get("version"), f"{prefix}.version", issues)
    _string(record.get("source_kind"), f"{prefix}.source_kind", issues)
    release_scope = _string(record.get("release_scope"), f"{prefix}.release_scope", issues)
    if release_scope and release_scope not in RELEASE_SCOPES:
        issues.append(f"{prefix}.release_scope不受支持：{release_scope}")
    digest = _string(record.get("original_sha256"), f"{prefix}.original_sha256", issues)
    if digest and not SHA256_PATTERN.fullmatch(digest.lower()):
        issues.append(f"{prefix}.original_sha256必须是 64 位小写 SHA-256")

    acquisition = _object(record.get("acquisition"), f"{prefix}.acquisition", issues)
    if "date" not in acquisition:
        issues.append(f"{prefix}.acquisition缺少 date")
    if "reference_index" not in acquisition:
        issues.append(f"{prefix}.acquisition缺少 reference_index")
    _string(acquisition.get("method"), f"{prefix}.acquisition.method", issues)

    rights = _object(record.get("rights"), f"{prefix}.rights", issues)
    rights_status = _string(rights.get("status"), f"{prefix}.rights.status", issues)
    if rights_status and rights_status not in RIGHTS_STATUSES:
        issues.append(f"{prefix}.rights.status不受支持：{rights_status}")
    allowed_uses = rights.get("allowed_uses")
    if (
        not isinstance(allowed_uses, list)
        or not allowed_uses
        or not all(isinstance(item, str) and item.strip() for item in allowed_uses)
    ):
        issues.append(f"{prefix}.rights.allowed_uses必须是非空字符串数组")

    permissions = _object(record.get("permissions"), f"{prefix}.permissions", issues)
    missing_permissions = sorted(REQUIRED_PERMISSION_FIELDS - set(permissions))
    if missing_permissions:
        issues.append(f"{prefix}.permissions缺少字段：{', '.join(missing_permissions)}")
    for field in REQUIRED_PERMISSION_FIELDS:
        if field in permissions and not isinstance(permissions[field], bool):
            issues.append(f"{prefix}.permissions.{field}必须是布尔值")
    if rights_status in {"B", "C", "test_fixture"} and any(
        permissions.get(field) is True for field in REQUIRED_PERMISSION_FIELDS
    ):
        issues.append(f"{prefix}的 {rights_status} 级来源不得声明对外展示或付费权限")

    processing = _object(record.get("processing"), f"{prefix}.processing", issues)
    _string(processing.get("parser"), f"{prefix}.processing.parser", issues)
    _string(processing.get("parser_version"), f"{prefix}.processing.parser_version", issues)
    if not isinstance(processing.get("package_schema_version"), int):
        issues.append(f"{prefix}.processing.package_schema_version必须是整数")
    _string(processing.get("owner"), f"{prefix}.processing.owner", issues)

    review = _object(record.get("review"), f"{prefix}.review", issues)
    _string(review.get("status"), f"{prefix}.review.status", issues)
    _string(review.get("owner"), f"{prefix}.review.owner", issues)
    if "date" not in review or "complaint_index" not in review:
        issues.append(f"{prefix}.review必须包含 date 和 complaint_index")

    takedown = _object(record.get("takedown"), f"{prefix}.takedown", issues)
    takedown_status = _string(takedown.get("status"), f"{prefix}.takedown.status", issues)
    if takedown_status and takedown_status not in TAKEDOWN_STATUSES:
        issues.append(f"{prefix}.takedown.status不受支持：{takedown_status}")
    if "reason_index" not in takedown:
        issues.append(f"{prefix}.takedown缺少 reason_index")

    if source_file and Path(source_file).name != source_file:
        issues.append(f"{prefix}.source_file只能包含文件名，不能包含目录")

    if release_scope == "test_only":
        if record.get("source_kind") != "repository_test_fixture":
            issues.append(f"{prefix}.test_only来源必须是 repository_test_fixture")
        if rights_status != "test_fixture":
            issues.append(f"{prefix}.test_only来源的 rights.status 必须是 test_fixture")
        if review.get("status") != "not_applicable":
            issues.append(f"{prefix}.test_only来源的 review.status 必须是 not_applicable")
        if record.get("repository_storage") != "tracked_test_fixture":
            issues.append(f"{prefix}.test_only来源必须使用 tracked_test_fixture 存储标识")
    elif release_scope == "production" and record.get("source_kind") == "repository_test_fixture":
        issues.append(f"{prefix}.repository_test_fixture不能声明为 production 来源")


def validate_source_register(
    register_path: Path = DEFAULT_REGISTER_PATH,
    metadata_path: Path = DEFAULT_METADATA_PATH,
    source_root: Path = DEFAULT_SOURCE_ROOT,
    active_db_path: Path = DEFAULT_ACTIVE_DB_PATH,
) -> dict[str, Any]:
    register = _load_json(register_path.resolve(), "来源登记台账")
    metadata = _load_json(metadata_path.resolve(), "运行来源元数据")
    issues: list[str] = []
    warnings: list[str] = []

    if register.get("schema_version") != 1:
        issues.append("来源登记台账 schema_version 必须是 1")
    records = register.get("documents")
    if not isinstance(records, list):
        raise SourceRegisterError("来源登记台账 documents 必须是数组")
    metadata_records = metadata.get("documents")
    if not isinstance(metadata_records, list):
        raise SourceRegisterError("运行来源元数据 documents 必须是数组")

    metadata_files = {
        str(item.get("source_file") or "").strip()
        for item in metadata_records
        if isinstance(item, dict)
    }
    metadata_files.discard("")
    record_files: set[str] = set()
    record_ids: set[str] = set()
    release_blockers: list[str] = []
    record_scopes: dict[str, str] = {}

    for index, raw_record in enumerate(records):
        if not isinstance(raw_record, dict):
            issues.append(f"documents[{index}]必须是对象")
            continue
        _validate_record_shape(raw_record, index, issues)
        source_file = str(raw_record.get("source_file") or "").strip()
        source_id = str(raw_record.get("source_id") or "").strip()
        release_scope = str(raw_record.get("release_scope") or "").strip()
        if source_file and release_scope:
            record_scopes[source_file] = release_scope
        if source_file in record_files:
            issues.append(f"来源登记包含重复 source_file：{source_file}")
        if source_id in record_ids:
            issues.append(f"来源登记包含重复 source_id：{source_id}")
        record_files.add(source_file)
        record_ids.add(source_id)

        source_path = source_root.resolve() / source_file if source_file else None
        digest = str(raw_record.get("original_sha256") or "").lower()
        if source_path is not None and source_path.is_file() and digest:
            actual = hashlib.sha256(source_path.read_bytes()).hexdigest()
            if actual != digest:
                issues.append(f"{source_file} 的 SHA-256 不匹配：台账={digest}，实际={actual}")
        elif source_path is not None:
            warnings.append(f"{source_file} 原始文件当前不在 {source_root}，仅校验台账字段")

        rights = raw_record.get("rights") if isinstance(raw_record.get("rights"), dict) else {}
        rights_status = str(rights.get("status") or "")
        acquisition = (
            raw_record.get("acquisition") if isinstance(raw_record.get("acquisition"), dict) else {}
        )
        review = raw_record.get("review") if isinstance(raw_record.get("review"), dict) else {}
        if release_scope == "test_only":
            continue
        if rights_status != "A":
            release_blockers.append(f"{source_file}: 权利等级为 {rights_status or '未填'}")
        if not acquisition.get("date") or not acquisition.get("reference_index"):
            release_blockers.append(f"{source_file}: 取得日期或凭证索引缺失")
        if review.get("status") != "verified":
            release_blockers.append(f"{source_file}: 权利复核状态不是 verified")
        if raw_record.get("repository_storage") == "tracked_raw_source":
            release_blockers.append(f"{source_file}: 原始扫描件仍位于仓库跟踪路径")
        if rights_status == "C":
            release_blockers.append(f"{source_file}: 来源已标记为禁止使用")

    missing = sorted(metadata_files - record_files)
    extra = sorted(record_files - metadata_files)
    if missing:
        issues.append("来源元数据缺少登记：" + ", ".join(missing))
    if extra:
        issues.append("来源台账包含未进入运行元数据的文件：" + ", ".join(extra))

    metadata_scopes = {
        str(item.get("source_file") or "").strip(): (
            "test_only" if item.get("status") == "test" else "production"
        )
        for item in metadata_records
        if isinstance(item, dict) and str(item.get("source_file") or "").strip()
    }
    for source_file, metadata_scope in metadata_scopes.items():
        registered_scope = record_scopes.get(source_file)
        if registered_scope and registered_scope != metadata_scope:
            issues.append(
                f"{source_file} 的来源范围不一致：台账={registered_scope}，运行元数据={metadata_scope}"
            )

    runtime_test_only_sources: list[str] = []
    if not active_db_path.is_file():
        warnings.append(f"活动数据库指针不存在，未能校验运行来源范围：{active_db_path}")
        release_blockers.append("活动数据库指针不存在，不能确认生产运行来源范围")
    else:
        active_db = _load_json(active_db_path.resolve(), "活动数据库指针")
        manifest_reference = str(active_db.get("manifest") or "").strip()
        if manifest_reference:
            manifest_path = resolve_pointer_path(
                manifest_reference,
                active_db_path.resolve(),
                active_db_path.resolve().parent / "manifest.json",
            )
            if manifest_path.is_file():
                runtime_manifest = _load_json(manifest_path.resolve(), "活动运行 manifest")
                runtime_sources = {
                    str(item.get("source_file") or "").strip(): item
                    for item in runtime_manifest.get("documents", [])
                    if isinstance(item, dict) and str(item.get("source_file") or "").strip()
                }
                runtime_test_only_sources = sorted(
                    source_file
                    for source_file, item in runtime_sources.items()
                    if item.get("status") == "test"
                )
                for source_file in runtime_test_only_sources:
                    release_blockers.append(
                        f"{source_file}: test_only 来源仍位于活动运行 manifest，不能作为生产运行包发布"
                    )
            else:
                warnings.append(f"活动运行 manifest 不存在，未能校验测试来源范围：{manifest_path}")
                release_blockers.append("活动运行 manifest 不存在，不能确认生产运行来源范围")
        else:
            warnings.append("活动数据库指针缺少 manifest，未能校验运行来源范围")
            release_blockers.append("活动数据库指针缺少 manifest，不能确认生产运行来源范围")

    if issues:
        raise SourceRegisterError(issues)
    return {
        "ok": True,
        "registry_path": str(register_path.resolve()),
        "metadata_path": str(metadata_path.resolve()),
        "source_count": len(records),
        "production_source_count": sum(scope == "production" for scope in record_scopes.values()),
        "test_only_sources": sorted(
            source_file for source_file, scope in record_scopes.items() if scope == "test_only"
        ),
        "runtime_test_only_sources": runtime_test_only_sources,
        "release_eligible": not release_blockers,
        "release_blockers": release_blockers,
        "warnings": warnings,
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="校验来源登记台账与运行来源元数据")
    parser.add_argument("--register", type=Path, default=DEFAULT_REGISTER_PATH)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--active-db", type=Path, default=DEFAULT_ACTIVE_DB_PATH)
    parser.add_argument(
        "--require-release-eligible",
        action="store_true",
        help="额外要求所有来源具备可对外发布资格；当前内部台账通常应失败",
    )
    args = parser.parse_args()
    try:
        result = validate_source_register(
            args.register, args.metadata, args.source_root, args.active_db
        )
        if args.require_release_eligible and not result["release_eligible"]:
            result = {
                **result,
                "ok": False,
                "error": "source_release_not_eligible",
            }
            print(json.dumps(result, ensure_ascii=True, indent=2))
            return 1
    except SourceRegisterError as exc:
        for issue in exc.issues:
            safe_issue = issue.encode("ascii", errors="backslashreplace").decode("ascii")
            print(f"::error title=Source register::{safe_issue}")
        result = {"ok": False, "error": "source_register_invalid", "issues": exc.issues}
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
