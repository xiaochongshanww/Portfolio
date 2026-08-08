from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from getpass import getuser
from pathlib import Path, PurePosixPath
from typing import Any

from .paths import DATA_DIR, PROJECT_ROOT


BACKUP_FORMAT = "structural-spec-runtime-backup"
BACKUP_SCHEMA_VERSION = 1
BACKUP_MANIFEST_NAME = "runtime-backup.json"
PAYLOAD_PREFIX = "data"
DEFAULT_MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024 * 1024
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
ACTIVE_JOB_STATUSES = {"queued", "running"}
BACKUP_ID_RE = re.compile(r"^rb-[0-9a-f]{24}$")


class RuntimeBackupError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _actor(explicit_actor: str) -> str:
    actor = explicit_actor.strip()
    if actor:
        return actor
    try:
        return getuser().strip() or "unknown"
    except (ImportError, KeyError, OSError):
        return "unknown"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise RuntimeBackupError(f"无法读取运行数据文件 {path}: {exc}") from exc
    return digest.hexdigest()


def _zip_member_sha256(archive: zipfile.ZipFile, name: str) -> str:
    digest = hashlib.sha256()
    with archive.open(name) as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_member(name: str) -> PurePosixPath:
    if not name or len(name) > 4096 or "\\" in name or ":" in name:
        raise RuntimeBackupError(f"运行数据快照包含不安全路径: {name!r}")
    raw_parts = name.split("/")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in raw_parts):
        raise RuntimeBackupError(f"运行数据快照包含不安全路径: {name!r}")
    return path


def _payload_path(relative_path: str) -> str:
    return f"{PAYLOAD_PREFIX}/{relative_path}"


def _file_identity(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": entry["path"],
        "size_bytes": entry["size_bytes"],
        "sha256": entry["sha256"],
    }


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _payload_hash(files: list[dict[str, Any]]) -> str:
    return _canonical_hash([_file_identity(entry) for entry in files])


def _inventory_hash(
    root: dict[str, int],
    directories: list[dict[str, Any]],
    files: list[dict[str, Any]],
) -> str:
    return _canonical_hash(
        {
            "root": root,
            "directories": directories,
            "files": files,
        }
    )


def _entry_metadata(path: Path) -> dict[str, int]:
    try:
        info = path.stat()
    except OSError as exc:
        raise RuntimeBackupError(f"无法读取运行数据元数据 {path}: {exc}") from exc
    return {
        "mtime_ns": info.st_mtime_ns,
        "mode": stat.S_IMODE(info.st_mode),
    }


def _resolve_data_dir(data_dir: Path) -> Path:
    candidate = data_dir.expanduser().absolute()
    if candidate.is_symlink():
        raise RuntimeBackupError(f"DATA_DIR 不能是符号链接: {candidate}")
    resolved = candidate.resolve()
    if resolved == resolved.parent or resolved == PROJECT_ROOT.resolve():
        raise RuntimeBackupError(f"DATA_DIR 目标过于宽泛，拒绝操作: {resolved}")
    return resolved


def _scan_inventory(data_dir: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    if not data_dir.is_dir():
        raise RuntimeBackupError(f"DATA_DIR 不存在或不是目录: {data_dir}")
    if data_dir.is_symlink():
        raise RuntimeBackupError(f"DATA_DIR 不能是符号链接: {data_dir}")

    directories: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    sources: dict[str, Path] = {}
    try:
        paths = sorted(data_dir.rglob("*"), key=lambda item: item.relative_to(data_dir).as_posix())
    except OSError as exc:
        raise RuntimeBackupError(f"无法扫描 DATA_DIR {data_dir}: {exc}") from exc

    for path in paths:
        relative = path.relative_to(data_dir).as_posix()
        archive_path = _payload_path(relative)
        _safe_member(archive_path)
        if path.is_symlink():
            raise RuntimeBackupError(f"运行数据快照不允许符号链接: {path}")
        metadata = _entry_metadata(path)
        if path.is_dir():
            directories.append({"path": archive_path, **metadata})
            continue
        if not path.is_file():
            raise RuntimeBackupError(f"运行数据快照不允许特殊文件: {path}")
        entry = {
            "path": archive_path,
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
            **metadata,
        }
        files.append(entry)
        sources[archive_path] = path

    root = _entry_metadata(data_dir)
    payload_hash = _payload_hash(files)
    inventory_hash = _inventory_hash(root, directories, files)
    inventory = {
        "root": root,
        "directories": directories,
        "files": files,
        "file_count": len(files),
        "directory_count": len(directories),
        "uncompressed_size_bytes": sum(entry["size_bytes"] for entry in files),
        "payload_hash": payload_hash,
        "inventory_hash": inventory_hash,
        "backup_id": f"rb-{inventory_hash[:24]}",
    }
    return inventory, sources


def _assert_no_active_jobs(data_dir: Path) -> None:
    jobs_dir = data_dir / "jobs"
    if not jobs_dir.exists():
        return
    if not jobs_dir.is_dir() or jobs_dir.is_symlink():
        raise RuntimeBackupError(f"任务目录无效: {jobs_dir}")
    for path in sorted(jobs_dir.glob("*.json")):
        if path.is_symlink() or not path.is_file():
            raise RuntimeBackupError(f"任务记录不是普通文件: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeBackupError(f"无法解析任务记录 {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise RuntimeBackupError(f"任务记录不是 JSON 对象: {path}")
        status_value = payload.get("status")
        if not isinstance(status_value, str):
            raise RuntimeBackupError(f"任务记录缺少有效 status: {path}")
        status_value = status_value.strip().lower()
        if status_value in ACTIVE_JOB_STATUSES:
            raise RuntimeBackupError(
                f"存在活动任务 {path.stem}（{status_value}），请停止 API 并完成任务收口后重试"
            )


def _manifest_from_inventory(inventory: dict[str, Any], actor: str) -> dict[str, Any]:
    return {
        "format": BACKUP_FORMAT,
        "schema_version": BACKUP_SCHEMA_VERSION,
        "backup_id": inventory["backup_id"],
        "created_at": _utc_now(),
        "actor": actor,
        "source_scope": "DATA_DIR",
        **inventory,
    }


def _zip_is_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK(info.external_attr >> 16)


def _read_manifest(archive: zipfile.ZipFile) -> dict[str, Any]:
    try:
        info = archive.getinfo(BACKUP_MANIFEST_NAME)
    except KeyError as exc:
        raise RuntimeBackupError(f"运行数据快照缺少 {BACKUP_MANIFEST_NAME}") from exc
    if info.file_size > MAX_MANIFEST_BYTES:
        raise RuntimeBackupError(f"运行数据快照清单超过 {MAX_MANIFEST_BYTES} bytes")
    try:
        payload = json.loads(archive.read(BACKUP_MANIFEST_NAME).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeBackupError("运行数据快照清单不是有效的 UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeBackupError("运行数据快照清单必须是 JSON 对象")
    return payload


def _validate_metadata(value: Any, *, label: str) -> dict[str, int]:
    if not isinstance(value, dict):
        raise RuntimeBackupError(f"{label} 元数据必须是对象")
    mtime_ns = value.get("mtime_ns")
    mode = value.get("mode")
    if not isinstance(mtime_ns, int) or isinstance(mtime_ns, bool) or mtime_ns < 0:
        raise RuntimeBackupError(f"{label} mtime_ns 无效")
    if not isinstance(mode, int) or isinstance(mode, bool) or not 0 <= mode <= 0o7777:
        raise RuntimeBackupError(f"{label} mode 无效")
    return {"mtime_ns": mtime_ns, "mode": mode}


def _validate_manifest_entries(
    manifest: dict[str, Any],
) -> tuple[dict[str, int], list[dict[str, Any]], list[dict[str, Any]]]:
    root = _validate_metadata(manifest.get("root"), label="根目录")
    raw_directories = manifest.get("directories")
    raw_files = manifest.get("files")
    if not isinstance(raw_directories, list) or not isinstance(raw_files, list):
        raise RuntimeBackupError("运行数据快照 directories/files 必须是数组")

    directories: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_directories:
        if not isinstance(raw, dict):
            raise RuntimeBackupError("目录声明必须是对象")
        path = str(raw.get("path") or "")
        safe = _safe_member(path)
        if safe.parts[0] != PAYLOAD_PREFIX or len(safe.parts) < 2 or path in seen:
            raise RuntimeBackupError(f"目录声明重复或不在 data/ 下: {path!r}")
        seen.add(path)
        directories.append({"path": path, **_validate_metadata(raw, label=f"目录 {path}")})

    for raw in raw_files:
        if not isinstance(raw, dict):
            raise RuntimeBackupError("文件声明必须是对象")
        path = str(raw.get("path") or "")
        safe = _safe_member(path)
        if safe.parts[0] != PAYLOAD_PREFIX or len(safe.parts) < 2 or path in seen:
            raise RuntimeBackupError(f"文件声明重复或不在 data/ 下: {path!r}")
        seen.add(path)
        size = raw.get("size_bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise RuntimeBackupError(f"文件大小声明无效: {path}")
        digest = str(raw.get("sha256") or "").lower()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise RuntimeBackupError(f"文件 SHA-256 声明无效: {path}")
        files.append(
            {
                "path": path,
                "size_bytes": size,
                "sha256": digest,
                **_validate_metadata(raw, label=f"文件 {path}"),
            }
        )
    if directories != sorted(directories, key=lambda entry: entry["path"]):
        raise RuntimeBackupError("运行数据快照目录声明必须按路径排序")
    if files != sorted(files, key=lambda entry: entry["path"]):
        raise RuntimeBackupError("运行数据快照文件声明必须按路径排序")

    directory_paths = {entry["path"] for entry in directories}
    for entry in [*directories, *files]:
        path = PurePosixPath(entry["path"])
        parent = path.parent
        if str(parent) != PAYLOAD_PREFIX and str(parent) not in directory_paths:
            raise RuntimeBackupError(f"运行数据快照缺少父目录声明: {parent}")
    return root, directories, files


def validate_runtime_backup(
    backup_path: Path,
    *,
    max_uncompressed_bytes: int = DEFAULT_MAX_UNCOMPRESSED_BYTES,
) -> dict[str, Any]:
    backup_path = backup_path.expanduser().resolve()
    if not backup_path.is_file():
        raise RuntimeBackupError(f"运行数据快照不存在: {backup_path}")
    if max_uncompressed_bytes <= 0:
        raise RuntimeBackupError("解压大小限制必须大于 0")
    try:
        archive = zipfile.ZipFile(backup_path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise RuntimeBackupError("文件不是有效的 ZIP 运行数据快照") from exc

    with archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise RuntimeBackupError("运行数据快照包含重复 ZIP 成员")
        for info in infos:
            _safe_member(info.filename)
            if info.is_dir():
                raise RuntimeBackupError(f"运行数据快照不应包含显式目录成员: {info.filename}")
            if _zip_is_symlink(info):
                raise RuntimeBackupError(f"运行数据快照不允许 ZIP 符号链接: {info.filename}")
        archive_size = sum(info.file_size for info in infos)
        if archive_size > max_uncompressed_bytes:
            raise RuntimeBackupError(f"运行数据快照解压后超过限制: {archive_size} bytes")

        manifest = _read_manifest(archive)
        if manifest.get("format") != BACKUP_FORMAT:
            raise RuntimeBackupError("运行数据快照 format 不受支持")
        if manifest.get("schema_version") != BACKUP_SCHEMA_VERSION:
            raise RuntimeBackupError(
                f"运行数据快照 schema_version 不受支持: {manifest.get('schema_version')}"
            )
        backup_id = str(manifest.get("backup_id") or "")
        if not BACKUP_ID_RE.fullmatch(backup_id):
            raise RuntimeBackupError(f"运行数据快照 backup_id 无效: {backup_id!r}")
        if manifest.get("source_scope") != "DATA_DIR":
            raise RuntimeBackupError("运行数据快照 source_scope 无效")
        actor = str(manifest.get("actor") or "").strip()
        if not actor:
            raise RuntimeBackupError("运行数据快照缺少责任人")
        created_at = str(manifest.get("created_at") or "")
        try:
            parsed_created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise RuntimeBackupError("运行数据快照 created_at 无效") from exc
        if parsed_created_at.tzinfo is None:
            raise RuntimeBackupError("运行数据快照 created_at 必须包含时区")

        root, directories, files = _validate_manifest_entries(manifest)
        actual_payloads = set(names) - {BACKUP_MANIFEST_NAME}
        declared_payloads = {entry["path"] for entry in files}
        if actual_payloads != declared_payloads:
            missing = sorted(declared_payloads - actual_payloads)
            undeclared = sorted(actual_payloads - declared_payloads)
            raise RuntimeBackupError(
                f"运行数据快照文件声明不一致: missing={missing}, undeclared={undeclared}"
            )

        for entry in files:
            info = archive.getinfo(entry["path"])
            if info.file_size != entry["size_bytes"]:
                raise RuntimeBackupError(f"文件大小不匹配: {entry['path']}")
            if _zip_member_sha256(archive, entry["path"]) != entry["sha256"]:
                raise RuntimeBackupError(f"文件 SHA-256 不匹配: {entry['path']}")

        file_count = manifest.get("file_count")
        directory_count = manifest.get("directory_count")
        payload_size = manifest.get("uncompressed_size_bytes")
        if file_count != len(files) or directory_count != len(directories):
            raise RuntimeBackupError("运行数据快照文件或目录计数不一致")
        expected_payload_size = sum(entry["size_bytes"] for entry in files)
        if payload_size != expected_payload_size:
            raise RuntimeBackupError("运行数据快照负载大小不一致")
        expected_payload_hash = _payload_hash(files)
        if manifest.get("payload_hash") != expected_payload_hash:
            raise RuntimeBackupError("运行数据快照 payload_hash 不一致")
        expected_inventory_hash = _inventory_hash(root, directories, files)
        if manifest.get("inventory_hash") != expected_inventory_hash:
            raise RuntimeBackupError("运行数据快照 inventory_hash 不一致")
        if backup_id != f"rb-{expected_inventory_hash[:24]}":
            raise RuntimeBackupError("运行数据快照 backup_id 与清单不一致")

    return {
        "ok": True,
        "valid": True,
        "backup": str(backup_path),
        "backup_id": backup_id,
        "schema_version": BACKUP_SCHEMA_VERSION,
        "created_at": created_at,
        "actor": actor,
        "file_count": len(files),
        "directory_count": len(directories),
        "uncompressed_size_bytes": expected_payload_size,
        "payload_hash": expected_payload_hash,
        "inventory_hash": expected_inventory_hash,
    }


def create_runtime_backup(
    output_path: Path,
    *,
    data_dir: Path = DATA_DIR,
    overwrite: bool = False,
    actor: str = "",
    maintenance_window: bool = False,
) -> dict[str, Any]:
    if not maintenance_window:
        raise RuntimeBackupError("创建完整快照必须显式确认维护窗口")
    source = _resolve_data_dir(data_dir)
    output = output_path.expanduser().resolve()
    if output == source or output.is_relative_to(source):
        raise RuntimeBackupError("快照输出不能位于 DATA_DIR 内")
    if output.exists() and not overwrite:
        raise RuntimeBackupError(f"快照已存在，使用 --overwrite 才可覆盖: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")

    _assert_no_active_jobs(source)
    inventory, sources = _scan_inventory(source)
    manifest = _manifest_from_inventory(inventory, _actor(actor))
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
            allowZip64=True,
        ) as archive:
            for entry in manifest["files"]:
                archive.write(sources[entry["path"]], entry["path"])
            archive.writestr(
                BACKUP_MANIFEST_NAME,
                json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            )

        _assert_no_active_jobs(source)
        second_inventory, _ = _scan_inventory(source)
        if second_inventory != inventory:
            raise RuntimeBackupError("创建期间 DATA_DIR 发生变化，已拒绝生成不一致快照")
        validation = validate_runtime_backup(temporary)
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return {
        **validation,
        "backup": str(output),
        "size_bytes": output.stat().st_size,
        "maintenance_window_confirmed": True,
    }


def _apply_metadata(path: Path, metadata: dict[str, Any]) -> None:
    try:
        path.chmod(int(metadata["mode"]))
        os.utime(path, ns=(int(metadata["mtime_ns"]), int(metadata["mtime_ns"])))
    except OSError as exc:
        raise RuntimeBackupError(f"无法恢复文件元数据 {path}: {exc}") from exc


def _extract_backup(backup_path: Path, destination: Path) -> dict[str, Any]:
    with zipfile.ZipFile(backup_path) as archive:
        manifest = _read_manifest(archive)
        root, directories, files = _validate_manifest_entries(manifest)
        destination.mkdir(parents=True, exist_ok=False)
        for entry in sorted(directories, key=lambda item: len(PurePosixPath(item["path"]).parts)):
            relative = PurePosixPath(entry["path"]).relative_to(PAYLOAD_PREFIX)
            destination.joinpath(*relative.parts).mkdir(parents=True, exist_ok=False)
        for entry in files:
            relative = PurePosixPath(entry["path"]).relative_to(PAYLOAD_PREFIX)
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry["path"]) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            if target.stat().st_size != entry["size_bytes"] or _sha256(target) != entry["sha256"]:
                raise RuntimeBackupError(f"解压后文件完整性校验失败: {entry['path']}")
            _apply_metadata(target, entry)
        for entry in sorted(
            directories,
            key=lambda item: len(PurePosixPath(item["path"]).parts),
            reverse=True,
        ):
            relative = PurePosixPath(entry["path"]).relative_to(PAYLOAD_PREFIX)
            _apply_metadata(destination.joinpath(*relative.parts), entry)
        _apply_metadata(destination, root)
    return manifest


def _replace_path(source: Path, target: Path) -> None:
    source.replace(target)


def restore_runtime_backup(
    backup_path: Path,
    *,
    data_dir: Path = DATA_DIR,
    replace: bool = False,
    actor: str = "",
    maintenance_window: bool = False,
) -> dict[str, Any]:
    if not maintenance_window:
        raise RuntimeBackupError("恢复完整快照必须显式确认维护窗口")
    target = _resolve_data_dir(data_dir)
    backup = backup_path.expanduser().resolve()
    if backup == target or backup.is_relative_to(target):
        raise RuntimeBackupError("恢复使用的快照不能位于目标 DATA_DIR 内")
    validation = validate_runtime_backup(backup)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        if not target.is_dir() or target.is_symlink():
            raise RuntimeBackupError(f"目标 DATA_DIR 不是普通目录: {target}")
        _assert_no_active_jobs(target)
        if any(target.iterdir()) and not replace:
            raise RuntimeBackupError(f"目标 DATA_DIR 非空，使用 --replace 才可恢复: {target}")

    temporary_root = Path(tempfile.mkdtemp(prefix=".runtime-backup-", dir=target.parent))
    staging = temporary_root / "staging-data"
    previous = temporary_root / "previous-data"
    previous_moved = False
    target_installed = False
    cleanup_temporary = True
    try:
        manifest = _extract_backup(backup, staging)
        if manifest.get("backup_id") != validation["backup_id"]:
            raise RuntimeBackupError("运行数据快照在校验与解压之间发生变化")
        _assert_no_active_jobs(staging)
        staged_inventory, _ = _scan_inventory(staging)
        expected_inventory = {
            key: manifest[key]
            for key in (
                "root",
                "directories",
                "files",
                "file_count",
                "directory_count",
                "uncompressed_size_bytes",
                "payload_hash",
                "inventory_hash",
                "backup_id",
            )
        }
        if staged_inventory != expected_inventory:
            raise RuntimeBackupError("解压后的 DATA_DIR 清单与快照不一致")

        if target.exists():
            _replace_path(target, previous)
            previous_moved = True
        _replace_path(staging, target)
        target_installed = True
        restored_inventory, _ = _scan_inventory(target)
        if restored_inventory != expected_inventory:
            raise RuntimeBackupError("恢复后的 DATA_DIR 清单与快照不一致")
    except Exception as exc:
        rollback_errors: list[str] = []
        if target_installed and target.exists():
            try:
                shutil.rmtree(target)
            except OSError as rollback_exc:
                rollback_errors.append(f"无法移除失败目标: {rollback_exc}")
        if previous_moved and previous.exists():
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                _replace_path(previous, target)
            except OSError as rollback_exc:
                rollback_errors.append(f"无法恢复原 DATA_DIR: {rollback_exc}")
        if rollback_errors:
            cleanup_temporary = False
            detail = "；".join(rollback_errors)
            raise RuntimeBackupError(
                f"恢复失败且自动回退不完整，旧数据保留在 {temporary_root}: {detail}"
            ) from exc
        raise
    finally:
        if cleanup_temporary:
            shutil.rmtree(temporary_root, ignore_errors=True)

    return {
        **validation,
        "data_dir": str(target),
        "restored_by": _actor(actor),
        "replaced_existing": previous_moved,
        "maintenance_window_confirmed": True,
        "restart_required": True,
        "post_restore_checks": [
            "python -m src.app.core.config",
            "GET /health",
            "GET /ready",
            "GET /admin/active-db",
            "GET /admin/quality/status",
        ],
    }
