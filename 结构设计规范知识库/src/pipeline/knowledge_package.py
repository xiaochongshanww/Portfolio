from __future__ import annotations

import hashlib
import json
import platform
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from getpass import getuser
from importlib import metadata as importlib_metadata
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from src.app.core.config import settings
from src.quality import DEFAULT_REPORT_MAX_AGE, evaluate_quality_gate

from .active_db import read_active_db, write_active_db
from .manifest import read_manifest
from .paths import (
    ACTIVE_DB_PATH,
    AUDIT_DIR,
    DATA_DIR,
    DB_DIR,
    IMAGES_DIR,
    MANIFEST_PATH,
    RAW_DIR,
    STRUCTURED_TABLES_DIR,
)


PACKAGE_FORMAT = "structural-spec-knowledge-package"
PACKAGE_SCHEMA_VERSION = 2
SUPPORTED_PACKAGE_SCHEMA_VERSIONS = {1, PACKAGE_SCHEMA_VERSION}
PACKAGE_MANIFEST_NAME = "knowledge-package.json"
DEFAULT_MAX_UNCOMPRESSED_BYTES = 20 * 1024 * 1024 * 1024
PACKAGE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MIN_WAIVER_REASON_LENGTH = 8


class KnowledgePackageError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _zip_member_sha256(archive: zipfile.ZipFile, name: str) -> str:
    digest = hashlib.sha256()
    with archive.open(name) as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _dependency_version(distribution: str) -> str:
    try:
        return importlib_metadata.version(distribution)
    except importlib_metadata.PackageNotFoundError:
        return "not-installed"


def _resolve_pointer_path(value: str | None, pointer_path: Path, default: Path) -> Path:
    candidate = Path(value) if value else default
    if candidate.is_absolute():
        return candidate.resolve()
    project_root = pointer_path.resolve().parents[1]
    return (project_root / candidate).resolve()


def _payload_files(directory: Path, archive_prefix: str, role: str) -> Iterable[tuple[str, Path, str]]:
    if not directory.exists():
        return
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise KnowledgePackageError(f"知识包不允许包含符号链接: {path}")
        if path.is_file():
            relative = path.relative_to(directory).as_posix()
            yield f"{archive_prefix}/{relative}", path, role


def _file_entry(archive_path: str, source: Path, role: str) -> dict[str, Any]:
    return {
        "path": archive_path,
        "role": role,
        "size_bytes": source.stat().st_size,
        "sha256": _sha256(source),
    }


def _payload_hash(entries: Iterable[dict[str, Any]]) -> str:
    canonical = [
        {
            "path": str(entry.get("path") or ""),
            "role": str(entry.get("role") or ""),
            "size_bytes": int(entry.get("size_bytes", -1)),
            "sha256": str(entry.get("sha256") or "").lower(),
        }
        for entry in entries
    ]
    encoded = json.dumps(
        sorted(canonical, key=lambda entry: entry["path"]),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _object_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _assert_safe_member(name: str) -> PurePosixPath:
    if not name or "\\" in name or ":" in name:
        raise KnowledgePackageError(f"知识包包含不安全路径: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise KnowledgePackageError(f"知识包包含不安全路径: {name!r}")
    return path


def _read_package_manifest(archive: zipfile.ZipFile) -> dict[str, Any]:
    try:
        info = archive.getinfo(PACKAGE_MANIFEST_NAME)
    except KeyError as exc:
        raise KnowledgePackageError(f"缺少 {PACKAGE_MANIFEST_NAME}") from exc
    if info.file_size > 2 * 1024 * 1024:
        raise KnowledgePackageError("知识包清单超过 2 MiB")
    try:
        payload = json.loads(archive.read(PACKAGE_MANIFEST_NAME).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise KnowledgePackageError("知识包清单不是有效的 UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise KnowledgePackageError("知识包清单必须是 JSON 对象")
    return payload


def _export_actor(explicit_actor: str) -> str:
    actor = explicit_actor.strip()
    if actor:
        return actor
    try:
        return getuser().strip() or "unknown"
    except (ImportError, KeyError, OSError):
        return "unknown"


def _quality_evidence(
    gate_result: dict[str, Any],
    *,
    data_version_hash: str,
    max_report_age: timedelta,
    waiver_actor: str,
    waiver_reason: str,
    audit_event_id: str,
) -> dict[str, Any]:
    failed_checks = [str(item) for item in gate_result.get("failed_checks", [])]
    gate_version = str(gate_result.get("data_version_hash") or "")
    if gate_version != data_version_hash and "quality_gate_data_version" not in failed_checks:
        failed_checks.append("quality_gate_data_version")
    gate_passed = gate_result.get("passed") is True and not failed_checks
    waiver_used = not gate_passed and bool(waiver_actor and waiver_reason)
    return {
        "gate_passed": gate_passed,
        "gate_generated_at": gate_result.get("generated_at"),
        "data_version_hash": gate_version,
        "max_report_age_seconds": int(max_report_age.total_seconds()),
        "failed_checks": failed_checks,
        "waiver": {
            "used": waiver_used,
            "actor": waiver_actor if waiver_used else "",
            "reason": waiver_reason if waiver_used else "",
        },
        "audit_event_id": audit_event_id,
    }


def _write_export_audit(audit_dir: Path, event: dict[str, Any]) -> Path:
    path = audit_dir / f"{event['event_id']}.json"
    _atomic_write_json(path, event)
    return path


def export_runtime_package(
    output_path: Path,
    *,
    active_db_path: Path = ACTIVE_DB_PATH,
    fallback_manifest_path: Path = MANIFEST_PATH,
    structured_tables_dir: Path = STRUCTURED_TABLES_DIR,
    images_dir: Path = IMAGES_DIR,
    raw_dir: Path = RAW_DIR,
    include_source_pdfs: bool = False,
    overwrite: bool = False,
    quality_max_age: timedelta = DEFAULT_REPORT_MAX_AGE,
    quality_waiver_actor: str = "",
    quality_waiver_reason: str = "",
    export_actor: str = "",
    export_audit_dir: Path = AUDIT_DIR / "package_exports",
) -> dict[str, Any]:
    if quality_max_age <= timedelta(0):
        raise KnowledgePackageError("质量报告最大有效期必须大于 0")
    output_path = output_path.resolve()
    if output_path.exists() and not overwrite:
        raise KnowledgePackageError(f"输出文件已存在: {output_path}")

    active = read_active_db(active_db_path)
    db_dir = _resolve_pointer_path(str(active.get("active_db_dir") or ""), active_db_path, DB_DIR)
    manifest_path = _resolve_pointer_path(
        str(active.get("manifest") or ""),
        active_db_path,
        fallback_manifest_path,
    )
    manifest = read_manifest(manifest_path)
    if not manifest:
        raise KnowledgePackageError(f"活动 manifest 不存在或为空: {manifest_path}")
    if not db_dir.is_dir():
        raise KnowledgePackageError(f"活动数据库目录不存在: {db_dir}")

    source_roots = [db_dir.resolve(), structured_tables_dir.resolve(), images_dir.resolve()]
    if include_source_pdfs:
        source_roots.append(raw_dir.resolve())
    for source_root in source_roots:
        if output_path == source_root or output_path.is_relative_to(source_root):
            raise KnowledgePackageError(f"知识包输出不能位于待打包目录内: {output_path}")

    data_version_hash = str(manifest.get("data_version_hash") or "")
    if not data_version_hash:
        raise KnowledgePackageError("活动 manifest 缺少 data_version_hash")
    gate_result = evaluate_quality_gate(
        manifest_path=manifest_path,
        active_db_path=active_db_path,
        max_report_age=quality_max_age,
    )
    waiver_actor = quality_waiver_actor.strip()
    waiver_reason = quality_waiver_reason.strip()
    if bool(waiver_actor) != bool(waiver_reason):
        raise KnowledgePackageError("质量豁免必须同时提供责任人和原因")
    if waiver_reason and len(waiver_reason) < MIN_WAIVER_REASON_LENGTH:
        raise KnowledgePackageError(f"质量豁免原因至少需要 {MIN_WAIVER_REASON_LENGTH} 个字符")

    created_at = _utc_now()
    event_id = f"package-export-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{data_version_hash[:8]}"
    quality = _quality_evidence(
        gate_result,
        data_version_hash=data_version_hash,
        max_report_age=quality_max_age,
        waiver_actor=waiver_actor,
        waiver_reason=waiver_reason,
        audit_event_id=event_id,
    )
    if quality["gate_passed"] and waiver_actor:
        raise KnowledgePackageError("质量门禁已通过，不需要提供豁免参数")
    if not quality["gate_passed"] and not waiver_actor:
        audit_event = {
            "schema_version": 1,
            "event_id": event_id,
            "event_type": "knowledge_package_export",
            "created_at": created_at,
            "outcome": "blocked",
            "actor": _export_actor(export_actor),
            "output": str(output_path),
            "data_version_hash": data_version_hash,
            "include_source_pdfs": include_source_pdfs,
            "quality_gate": gate_result,
            "waiver": quality["waiver"],
        }
        audit_path = _write_export_audit(export_audit_dir, audit_event)
        failed = ", ".join(quality["failed_checks"]) or "unknown"
        raise KnowledgePackageError(
            f"质量门禁未通过，已阻断知识包导出（{failed}）；审计记录: {audit_path}。"
            "如需紧急豁免，必须同时提供责任人和原因"
        )

    payloads: list[tuple[str, Path, str]] = [("runtime/manifest.json", manifest_path, "manifest")]
    database_files = list(_payload_files(db_dir, "runtime/db", "vector_index"))
    if not database_files:
        raise KnowledgePackageError(f"活动数据库目录没有可导出的文件: {db_dir}")
    payloads.extend(database_files)
    payloads.extend(_payload_files(structured_tables_dir, "runtime/structured_tables", "structured_table"))
    payloads.extend(_payload_files(images_dir, "runtime/images", "image"))
    if include_source_pdfs:
        for archive_path, source, role in _payload_files(raw_dir, "runtime/raw", "source_pdf"):
            if source.suffix.lower() == ".pdf":
                payloads.append((archive_path, source, role))

    archive_paths = [archive_path for archive_path, _, _ in payloads]
    if len(archive_paths) != len(set(archive_paths)):
        raise KnowledgePackageError("导出内容存在重复路径")

    entries = [_file_entry(archive_path, source, role) for archive_path, source, role in payloads]
    roles = {entry["role"] for entry in entries}
    payload_hash = _payload_hash(entries)
    quality_hash = _object_hash(quality)
    package_id = f"kp-{data_version_hash[:12]}-{payload_hash[:12]}-{quality_hash[:12]}"
    package_manifest = {
        "format": PACKAGE_FORMAT,
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "package_id": package_id,
        "profile": "runtime",
        "created_at": created_at,
        "data_version_hash": data_version_hash,
        "payload_hash": payload_hash,
        "document_count": int(manifest.get("document_count", 0)),
        "chunk_count": int(manifest.get("chunk_count", 0)),
        "compatibility": {
            "app_version": settings.app_version,
            "python_version": platform.python_version(),
            "platform": platform.system().lower(),
            "machine": platform.machine().lower(),
            "chromadb_version": _dependency_version("chromadb"),
            "embedding_model": str(manifest.get("embedding_model") or settings.embedding_model),
            "collection_name": str(manifest.get("collection_name") or settings.collection_name),
        },
        "capabilities": {
            "prebuilt_vector_index": True,
            "structured_tables": "structured_table" in roles,
            "extracted_images": "image" in roles,
            "source_pdfs": "source_pdf" in roles,
            "page_images": "source_pdf" in roles,
        },
        "quality": quality,
        "files": entries,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(f".{output_path.name}.tmp")
    temporary_path.unlink(missing_ok=True)
    audit_event = {
        "schema_version": 1,
        "event_id": event_id,
        "event_type": "knowledge_package_export",
        "created_at": created_at,
        "outcome": "authorized",
        "actor": _export_actor(export_actor),
        "output": str(output_path),
        "package_id": package_id,
        "data_version_hash": data_version_hash,
        "include_source_pdfs": include_source_pdfs,
        "quality_gate": gate_result,
        "waiver": quality["waiver"],
    }
    try:
        with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for archive_path, source, _ in payloads:
                archive.write(source, archive_path)
            archive.writestr(
                PACKAGE_MANIFEST_NAME,
                json.dumps(package_manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            )
        audit_path = _write_export_audit(export_audit_dir, audit_event)
        temporary_path.replace(output_path)
        audit_event["outcome"] = "exported"
        audit_event["size_bytes"] = output_path.stat().st_size
        _write_export_audit(export_audit_dir, audit_event)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return {
        "ok": True,
        "package": str(output_path),
        "package_id": package_id,
        "data_version_hash": data_version_hash,
        "file_count": len(entries),
        "size_bytes": output_path.stat().st_size,
        "capabilities": package_manifest["capabilities"],
        "quality": quality,
        "audit_record": str(audit_path),
    }


def validate_runtime_package(
    package_path: Path,
    *,
    max_uncompressed_bytes: int = DEFAULT_MAX_UNCOMPRESSED_BYTES,
) -> dict[str, Any]:
    package_path = package_path.resolve()
    if not package_path.is_file():
        raise KnowledgePackageError(f"知识包不存在: {package_path}")

    try:
        archive = zipfile.ZipFile(package_path)
    except zipfile.BadZipFile as exc:
        raise KnowledgePackageError("文件不是有效的 ZIP 知识包") from exc

    with archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise KnowledgePackageError("知识包包含重复 ZIP 成员")
        for info in infos:
            _assert_safe_member(info.filename)
            if info.is_dir():
                raise KnowledgePackageError(f"知识包不应包含显式目录成员: {info.filename}")
        total_size = sum(info.file_size for info in infos)
        if total_size > max_uncompressed_bytes:
            raise KnowledgePackageError(f"知识包解压后超过限制: {total_size} bytes")

        package_manifest = _read_package_manifest(archive)
        if package_manifest.get("format") != PACKAGE_FORMAT:
            raise KnowledgePackageError("知识包 format 不受支持")
        schema_version = package_manifest.get("schema_version")
        if (
            not isinstance(schema_version, int)
            or isinstance(schema_version, bool)
            or schema_version not in SUPPORTED_PACKAGE_SCHEMA_VERSIONS
        ):
            raise KnowledgePackageError(f"知识包 schema_version 不受支持: {package_manifest.get('schema_version')}")
        if package_manifest.get("profile") != "runtime":
            raise KnowledgePackageError("当前仅支持 runtime 知识包")
        package_id = str(package_manifest.get("package_id") or "")
        if not PACKAGE_ID_RE.fullmatch(package_id):
            raise KnowledgePackageError(f"package_id 不安全: {package_id!r}")

        declared = package_manifest.get("files")
        if not isinstance(declared, list) or not declared:
            raise KnowledgePackageError("知识包 files 必须是非空数组")
        declared_by_path: dict[str, dict[str, Any]] = {}
        for entry in declared:
            if not isinstance(entry, dict):
                raise KnowledgePackageError("files 成员必须是对象")
            path = str(entry.get("path") or "")
            _assert_safe_member(path)
            if path == PACKAGE_MANIFEST_NAME or path in declared_by_path:
                raise KnowledgePackageError(f"知识包文件声明重复或非法: {path}")
            role = entry.get("role")
            if not isinstance(role, str) or not role:
                raise KnowledgePackageError(f"文件角色声明无效: {path}")
            size = entry.get("size_bytes")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise KnowledgePackageError(f"文件大小声明无效: {path}")
            expected_hash = str(entry.get("sha256") or "").lower()
            if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                raise KnowledgePackageError(f"文件 SHA-256 声明无效: {path}")
            declared_by_path[path] = entry

        declared_payload_hash = str(package_manifest.get("payload_hash") or "").lower()
        calculated_payload_hash = _payload_hash(declared_by_path.values())
        if declared_payload_hash != calculated_payload_hash:
            raise KnowledgePackageError("知识包 payload_hash 与文件声明不一致")
        data_version_hash = str(package_manifest.get("data_version_hash") or "").lower()
        if not re.fullmatch(r"[0-9a-f]{64}", data_version_hash):
            raise KnowledgePackageError("知识包 data_version_hash 无效")
        quality = package_manifest.get("quality")
        if schema_version == 1:
            expected_package_id = f"kp-{data_version_hash[:12]}-{calculated_payload_hash[:12]}"
        elif isinstance(quality, dict):
            expected_package_id = (
                f"kp-{data_version_hash[:12]}-{calculated_payload_hash[:12]}-{_object_hash(quality)[:12]}"
            )
        else:
            raise KnowledgePackageError("v2 知识包缺少 quality 质量证据")
        if package_id != expected_package_id:
            raise KnowledgePackageError("知识包 package_id 与数据、payload 和质量证据不一致")

        actual_payloads = set(names) - {PACKAGE_MANIFEST_NAME}
        if actual_payloads != set(declared_by_path):
            missing = sorted(set(declared_by_path) - actual_payloads)
            undeclared = sorted(actual_payloads - set(declared_by_path))
            raise KnowledgePackageError(f"知识包文件声明不一致: missing={missing}, undeclared={undeclared}")

        for path, entry in declared_by_path.items():
            info = archive.getinfo(path)
            expected_size = entry.get("size_bytes")
            if info.file_size != expected_size:
                raise KnowledgePackageError(f"文件大小不匹配: {path}")
            expected_hash = str(entry.get("sha256") or "").lower()
            if _zip_member_sha256(archive, path) != expected_hash:
                raise KnowledgePackageError(f"文件 SHA-256 不匹配: {path}")

        if "runtime/manifest.json" not in declared_by_path:
            raise KnowledgePackageError("知识包缺少 runtime/manifest.json")
        if not any(path.startswith("runtime/db/") for path in declared_by_path):
            raise KnowledgePackageError("知识包缺少预构建向量数据库")
        try:
            runtime_manifest = json.loads(archive.read("runtime/manifest.json").decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise KnowledgePackageError("runtime/manifest.json 无效") from exc
        if runtime_manifest.get("data_version_hash") != package_manifest.get("data_version_hash"):
            raise KnowledgePackageError("包清单与运行 manifest 的数据版本不一致")
        if int(runtime_manifest.get("chunk_count", -1)) != int(package_manifest.get("chunk_count", -2)):
            raise KnowledgePackageError("包清单与运行 manifest 的 chunk 数不一致")

        capabilities = package_manifest.get("capabilities")
        if not isinstance(capabilities, dict):
            raise KnowledgePackageError("知识包 capabilities 必须是对象")
        has_raw = any(path.startswith("runtime/raw/") for path in declared_by_path)
        has_images = any(path.startswith("runtime/images/") for path in declared_by_path)
        has_tables = any(path.startswith("runtime/structured_tables/") for path in declared_by_path)
        expected_capabilities = {
            "prebuilt_vector_index": True,
            "structured_tables": has_tables,
            "extracted_images": has_images,
            "source_pdfs": has_raw,
            "page_images": has_raw,
        }
        for key, expected in expected_capabilities.items():
            if capabilities.get(key) is not expected:
                raise KnowledgePackageError(f"能力声明与文件内容不一致: {key}")

        if schema_version >= 2:
            if not isinstance(quality, dict):
                raise KnowledgePackageError("v2 知识包缺少 quality 质量证据")
            if quality.get("data_version_hash") != data_version_hash:
                raise KnowledgePackageError("质量证据与知识包数据版本不一致")
            gate_passed = quality.get("gate_passed")
            if not isinstance(gate_passed, bool):
                raise KnowledgePackageError("质量证据 gate_passed 必须是布尔值")
            gate_generated_at = str(quality.get("gate_generated_at") or "")
            try:
                parsed_gate_time = datetime.fromisoformat(gate_generated_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise KnowledgePackageError("质量证据 gate_generated_at 无效") from exc
            if parsed_gate_time.tzinfo is None:
                raise KnowledgePackageError("质量证据 gate_generated_at 必须包含时区")
            max_age_seconds = quality.get("max_report_age_seconds")
            if not isinstance(max_age_seconds, int) or isinstance(max_age_seconds, bool) or max_age_seconds <= 0:
                raise KnowledgePackageError("质量证据 max_report_age_seconds 无效")
            failed_checks = quality.get("failed_checks")
            if not isinstance(failed_checks, list) or not all(isinstance(item, str) for item in failed_checks):
                raise KnowledgePackageError("质量证据 failed_checks 必须是字符串数组")
            waiver = quality.get("waiver")
            if not isinstance(waiver, dict) or not isinstance(waiver.get("used"), bool):
                raise KnowledgePackageError("质量证据 waiver 声明无效")
            if gate_passed and (failed_checks or waiver.get("used") is True):
                raise KnowledgePackageError("质量证据同时声明通过和失败/豁免，状态矛盾")
            if not gate_passed:
                if waiver.get("used") is not True:
                    raise KnowledgePackageError("质量门禁未通过的知识包必须包含显式豁免")
                if not str(waiver.get("actor") or "").strip() or not str(waiver.get("reason") or "").strip():
                    raise KnowledgePackageError("质量豁免缺少责任人或原因")

        warnings: list[str] = []
        compatibility = package_manifest.get("compatibility", {})
        if not isinstance(compatibility, dict):
            raise KnowledgePackageError("知识包 compatibility 必须是对象")
        source_chroma = str(compatibility.get("chromadb_version") or "")
        local_chroma = _dependency_version("chromadb")
        if source_chroma not in {"", "not-installed"} and local_chroma not in {"", "not-installed"}:
            if source_chroma.split(".", 1)[0] != local_chroma.split(".", 1)[0]:
                warnings.append(f"Chroma 主版本不同: package={source_chroma}, local={local_chroma}")
        if compatibility.get("collection_name") != settings.collection_name:
            warnings.append(
                f"集合名称不同: package={compatibility.get('collection_name')}, local={settings.collection_name}"
            )
        if compatibility.get("embedding_model") != settings.embedding_model:
            warnings.append(
                f"Embedding 模型不同: package={compatibility.get('embedding_model')}, local={settings.embedding_model}"
            )
        local_platform = platform.system().lower()
        local_machine = platform.machine().lower()
        if compatibility.get("platform") not in {None, "", local_platform}:
            warnings.append(f"操作系统不同: package={compatibility.get('platform')}, local={local_platform}")
        if compatibility.get("machine") not in {None, "", local_machine}:
            warnings.append(f"处理器架构不同: package={compatibility.get('machine')}, local={local_machine}")

    return {
        "ok": True,
        "valid": True,
        "package": str(package_path),
        "package_id": package_manifest["package_id"],
        "data_version_hash": package_manifest["data_version_hash"],
        "document_count": package_manifest.get("document_count", 0),
        "chunk_count": package_manifest.get("chunk_count", 0),
        "file_count": len(package_manifest["files"]),
        "uncompressed_size_bytes": total_size,
        "capabilities": package_manifest["capabilities"],
        "compatibility": package_manifest.get("compatibility", {}),
        "quality": package_manifest.get("quality"),
        "warnings": warnings,
    }


def _extract_payloads(package_path: Path, destination: Path) -> dict[str, Any]:
    with zipfile.ZipFile(package_path) as archive:
        package_manifest = _read_package_manifest(archive)
        for entry in package_manifest["files"]:
            relative = _assert_safe_member(str(entry["path"]))
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(str(entry["path"])) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            if target.stat().st_size != entry["size_bytes"] or _sha256(target) != entry["sha256"]:
                raise KnowledgePackageError(f"解压后文件完整性校验失败: {entry['path']}")
    return package_manifest


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _asset_mappings(staging_runtime: Path, data_dir: Path) -> list[tuple[Path, Path]]:
    mappings: list[tuple[Path, Path]] = []
    for source_name, target_name in (
        ("structured_tables", "structured_tables"),
        ("images", "images"),
        ("raw", "raw"),
    ):
        source_root = staging_runtime / source_name
        if not source_root.exists():
            continue
        for source in sorted(source_root.rglob("*")):
            if source.is_file():
                mappings.append((source, data_dir / target_name / source.relative_to(source_root)))
    return mappings


def import_runtime_package(
    package_path: Path,
    *,
    data_dir: Path = DATA_DIR,
    replace: bool = False,
    activate: bool = True,
) -> dict[str, Any]:
    validation = validate_runtime_package(package_path)
    data_dir = data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    package_id = str(validation["package_id"])
    version_root = data_dir / "db_versions" / f"import-{package_id}"
    active_db_path = data_dir / "active_db.json"
    root_manifest_path = data_dir / "manifest.json"

    with tempfile.TemporaryDirectory(prefix="knowledge-package-", dir=data_dir.parent) as temporary_name:
        temporary_root = Path(temporary_name)
        staging = temporary_root / "staging"
        staging.mkdir()
        package_manifest = _extract_payloads(package_path.resolve(), staging)
        runtime = staging / "runtime"
        staged_db = runtime / "db"
        staged_manifest = runtime / "manifest.json"
        asset_mappings = _asset_mappings(runtime, data_dir)

        conflicts = [target for source, target in asset_mappings if target.exists() and _sha256(source) != _sha256(target)]
        if version_root.exists() and not replace:
            raise KnowledgePackageError(f"知识包版本已经安装: {version_root}")
        if conflicts and not replace:
            preview = ", ".join(str(path) for path in conflicts[:3])
            raise KnowledgePackageError(f"目标资产存在不同内容，使用 --replace 才可覆盖: {preview}")

        backup = temporary_root / "backup"
        backup.mkdir()
        moved_backups: list[tuple[Path, Path]] = []
        created_targets: list[Path] = []

        def backup_target(target: Path, key: str) -> None:
            if not target.exists():
                return
            backup_target_path = backup / key
            backup_target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(backup_target_path))
            moved_backups.append((backup_target_path, target))

        try:
            if version_root.exists():
                backup_target(version_root, "version")
            version_root.parent.mkdir(parents=True, exist_ok=True)
            version_root.mkdir()
            created_targets.append(version_root)
            shutil.copytree(staged_db, version_root / "db")
            shutil.copy2(staged_manifest, version_root / "manifest.json")

            copied_assets = 0
            reused_assets = 0
            for index, (source, target) in enumerate(asset_mappings):
                if target.exists() and _sha256(source) == _sha256(target):
                    reused_assets += 1
                    continue
                if target.exists():
                    backup_target(target, f"asset-{index}")
                target.parent.mkdir(parents=True, exist_ok=True)
                created_targets.append(target)
                shutil.copy2(source, target)
                copied_assets += 1

            if activate:
                backup_target(root_manifest_path, "root-manifest.json")
                backup_target(active_db_path, "active-db.json")
                created_targets.append(root_manifest_path)
                shutil.copy2(staged_manifest, root_manifest_path)
                created_targets.append(active_db_path)
                write_active_db(
                    {
                        "active_db_dir": str((version_root / "db").resolve()),
                        "manifest": str((version_root / "manifest.json").resolve()),
                        "package_id": package_id,
                        "data_version_hash": package_manifest["data_version_hash"],
                        "chunk_count": package_manifest.get("chunk_count", 0),
                        "activated_at": _utc_now(),
                        "activation_source": "knowledge_package_import",
                    },
                    active_db_path,
                )
        except Exception:
            for target in reversed(created_targets):
                if target.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                else:
                    target.unlink(missing_ok=True)
            for backup_path, target in reversed(moved_backups):
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(backup_path), str(target))
            raise

    return {
        "ok": True,
        "package": str(package_path.resolve()),
        "package_id": package_id,
        "data_version_hash": validation["data_version_hash"],
        "version_dir": str(version_root),
        "active_db_dir": str(version_root / "db") if activate else "",
        "activated": activate,
        "copied_asset_count": copied_assets,
        "reused_asset_count": reused_assets,
        "capabilities": validation["capabilities"],
        "warnings": validation["warnings"],
        "restart_required": activate,
    }
