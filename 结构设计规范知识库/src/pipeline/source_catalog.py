import hashlib
import json
import os
import re
import shutil
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from .metadata import load_metadata_overrides, parse_spec_filename

SCHEMA_VERSION = 1
SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{5,63}$")
ACCESS_SCOPES = {"public", "authenticated", "disabled"}
RIGHTS_STATUSES = {"A", "B", "C", "unknown"}


class SourceCatalogError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _safe_pdf_name(filename: str) -> str:
    raw = filename.strip()
    if "/" in raw or "\\" in raw:
        raise SourceCatalogError("文件名不能包含目录路径")
    normalized = Path(raw).name.strip()
    if not normalized or normalized in {".", ".."} or not normalized.lower().endswith(".pdf"):
        raise SourceCatalogError("文件名必须是有效的 PDF 文件名")
    return normalized


def _source_id(code: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", code.casefold()).strip("-")[:40] or "spec"
    return f"{slug}-{uuid4().hex[:8]}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_pdf(path: Path) -> int:
    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise SourceCatalogError("文件内容不是 PDF")
    try:
        import fitz

        with fitz.open(path) as document:
            if document.needs_pass:
                raise SourceCatalogError("不支持受密码保护的 PDF")
            if document.page_count <= 0:
                raise SourceCatalogError("PDF 不包含可读取页面")
            return document.page_count
    except SourceCatalogError:
        raise
    except Exception as exc:
        raise SourceCatalogError(f"PDF 结构校验失败：{exc}") from exc


class SourceCatalogStore:
    """Persistent source registry with immutable, content-addressed PDF assets."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.assets_dir = self.data_dir / "source_assets"
        self.objects_dir = self.assets_dir / "objects"
        self.staging_dir = self.assets_dir / "staging"
        self.catalog_dir = self.data_dir / "source_catalog"
        self.catalog_path = self.catalog_dir / "catalog.json"
        self.revisions_dir = self.catalog_dir / "revisions"
        self._lock = RLock()

    @staticmethod
    def empty_catalog() -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "revision": 0,
            "updated_at": "",
            "active_revision_id": "",
            "sources": [],
            "revisions": [],
        }

    def read(self) -> dict[str, Any]:
        with self._lock:
            if not self.catalog_path.exists():
                return self.empty_catalog()
            payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
            if payload.get("schema_version") != SCHEMA_VERSION:
                raise SourceCatalogError("不支持的来源目录版本")
            return payload

    def _write(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload["revision"] = int(payload.get("revision", 0)) + 1
        payload["updated_at"] = utc_now()
        _atomic_write_json(self.catalog_path, payload)
        return deepcopy(payload)

    def list_sources(self) -> dict[str, Any]:
        catalog = self.read()
        pending = sum(1 for source in catalog["sources"] if source.get("pending_action"))
        return {
            "catalog_revision": catalog["revision"],
            "active_revision_id": catalog.get("active_revision_id", ""),
            "source_count": len(catalog["sources"]),
            "pending_count": pending,
            "sources": catalog["sources"],
        }

    def get_source(self, source_id: str) -> dict[str, Any]:
        source = next(
            (item for item in self.read()["sources"] if item["source_id"] == source_id), None
        )
        if source is None:
            raise KeyError(source_id)
        return source

    def _find_source(self, catalog: dict[str, Any], source_id: str) -> dict[str, Any]:
        source = next((item for item in catalog["sources"] if item["source_id"] == source_id), None)
        if source is None:
            raise KeyError(source_id)
        return source

    def _ensure_unique_hash(self, catalog: dict[str, Any], sha256: str) -> None:
        for source in catalog["sources"]:
            if any(version.get("sha256") == sha256 for version in source.get("versions", [])):
                raise SourceCatalogError(f"该 PDF 已存在于来源 {source['source_id']}")

    def _store_object(self, path: Path, sha256: str) -> Path:
        target = self.objects_dir / sha256[:2] / f"{sha256}.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            temporary = target.with_suffix(".pdf.tmp")
            shutil.copyfile(path, temporary)
            temporary.replace(target)
        return target

    def _object_path(self, version: dict[str, Any]) -> Path:
        recorded = Path(str(version.get("object_path") or ""))
        if recorded.is_absolute():
            raise SourceCatalogError("来源资产路径必须是数据目录内的相对路径")
        resolved = (self.data_dir / recorded).resolve()
        try:
            resolved.relative_to(self.objects_dir.resolve())
        except ValueError as exc:
            raise SourceCatalogError("来源资产路径超出内容寻址对象目录") from exc
        return resolved

    def register_upload(
        self, path: Path, filename: str, *, source_id: str | None = None
    ) -> dict[str, Any]:
        filename = _safe_pdf_name(filename)
        page_count = validate_pdf(path)
        sha256 = _sha256(path)
        with self._lock:
            catalog = self.read()
            self._ensure_unique_hash(catalog, sha256)
            object_path = self._store_object(path, sha256)
            parsed = parse_spec_filename(filename)
            version = {
                "asset_version_id": f"asset-{uuid4().hex[:12]}",
                "sha256": sha256,
                "original_filename": filename,
                "object_path": object_path.relative_to(self.data_dir).as_posix(),
                "size_bytes": path.stat().st_size,
                "page_count": page_count,
                "uploaded_at": utc_now(),
                "validation_status": "validated",
                "validation_errors": [],
            }
            if source_id:
                source = self._find_source(catalog, source_id)
                if source.get("pending_action"):
                    raise SourceCatalogError("该来源已有待处理变更，请先应用或撤销")
                source["versions"].append(version)
                source["pending_asset_version_id"] = version["asset_version_id"]
                source["pending_action"] = "replace"
                source["lifecycle_status"] = "ready"
            else:
                metadata = parsed.to_dict()
                metadata["image_access"] = "disabled"
                metadata["page_image_access"] = "disabled"
                source = {
                    "source_id": _source_id(parsed.code),
                    "lifecycle_status": "draft",
                    "pending_action": "add",
                    "active_asset_version_id": "",
                    "pending_asset_version_id": version["asset_version_id"],
                    "metadata": metadata,
                    "governance": {
                        "source_kind": "user_upload",
                        "release_scope": "internal_research",
                        "acquisition_date": datetime.now(UTC).date().isoformat(),
                        "acquisition_method": "admin_upload",
                        "reference_index": "",
                        "rights_status": "B",
                        "allowed_uses": ["internal_research", "retrieval_evaluation"],
                        "notes": "上传来源默认不可公开分发，需由使用者确认授权边界。",
                    },
                    "versions": [version],
                    "created_at": utc_now(),
                    "updated_at": utc_now(),
                }
                catalog["sources"].append(source)
            self._refresh_source_readiness(source)
            self._write(catalog)
            return deepcopy(source)

    def _refresh_source_readiness(self, source: dict[str, Any]) -> None:
        metadata = source.get("metadata", {})
        version_id = source.get("pending_asset_version_id") or source.get("active_asset_version_id")
        version = next(
            (item for item in source.get("versions", []) if item["asset_version_id"] == version_id),
            None,
        )
        ready = bool(
            metadata.get("code")
            and metadata.get("name")
            and version
            and version.get("validation_status") == "validated"
        )
        if source.get("pending_action") == "retire":
            source["lifecycle_status"] = "active"
        elif ready:
            source["lifecycle_status"] = (
                "active"
                if source.get("active_asset_version_id")
                else ("ready" if source.get("pending_action") else "active")
            )
        else:
            source["lifecycle_status"] = "draft"
        metadata["metadata_status"] = (
            "complete" if metadata.get("code") and metadata.get("name") else "partial"
        )
        source["updated_at"] = utc_now()

    def update_source(
        self, source_id: str, metadata: dict[str, Any], governance: dict[str, Any]
    ) -> dict[str, Any]:
        with self._lock:
            catalog = self.read()
            source = self._find_source(catalog, source_id)
            previous_metadata = deepcopy(source.get("metadata", {}))
            previous_governance = deepcopy(source.get("governance", {}))
            immutable = {"source_file", "status", "metadata_status"}
            source["metadata"].update(
                {key: value for key, value in metadata.items() if key not in immutable}
            )
            source["governance"].update(governance)
            for key in ("image_access", "page_image_access"):
                if source["metadata"].get(key) not in ACCESS_SCOPES:
                    raise SourceCatalogError(f"{key} 不是有效的访问范围")
            if source["governance"].get("rights_status") not in RIGHTS_STATUSES:
                raise SourceCatalogError("rights_status 必须是 A、B、C 或 unknown")
            changed = (
                source.get("metadata") != previous_metadata
                or source.get("governance") != previous_governance
            )
            if changed and source.get("active_asset_version_id"):
                source.setdefault("active_metadata", previous_metadata)
                source.setdefault("active_governance", previous_governance)
                if not source.get("pending_action"):
                    source["pending_action"] = "update"
            self._refresh_source_readiness(source)
            self._write(catalog)
            return deepcopy(source)

    def retire(self, source_id: str) -> dict[str, Any]:
        with self._lock:
            catalog = self.read()
            source = self._find_source(catalog, source_id)
            if not source.get("active_asset_version_id"):
                raise SourceCatalogError("未上线来源无需执行下架")
            source["pending_action"] = "retire"
            source["pending_asset_version_id"] = ""
            self._refresh_source_readiness(source)
            self._write(catalog)
            return deepcopy(source)

    def validate_source(self, source_id: str) -> dict[str, Any]:
        with self._lock:
            catalog = self.read()
            source = self._find_source(catalog, source_id)
            version = self._selected_version(source)
            if version is None:
                raise SourceCatalogError("该来源没有可校验的 PDF 版本")
            errors: list[str] = []
            try:
                object_path = self._object_path(version)
                page_count = validate_pdf(object_path)
                if _sha256(object_path) != version["sha256"]:
                    errors.append("资产哈希与登记值不一致")
                version["page_count"] = page_count
            except (OSError, SourceCatalogError) as exc:
                errors.append(str(exc))
            version["validation_errors"] = errors
            version["validation_status"] = "invalid" if errors else "validated"
            self._refresh_source_readiness(source)
            if errors:
                source["lifecycle_status"] = "draft"
            self._write(catalog)
            return deepcopy(source)

    def discard_pending(self, source_id: str) -> dict[str, Any] | None:
        with self._lock:
            catalog = self.read()
            source = self._find_source(catalog, source_id)
            if source.get("pending_action") == "add" and not source.get("active_asset_version_id"):
                catalog["sources"].remove(source)
                self._write(catalog)
                return None
            pending_id = source.get("pending_asset_version_id")
            if pending_id:
                source["versions"] = [
                    item for item in source["versions"] if item["asset_version_id"] != pending_id
                ]
            if source.get("active_asset_version_id"):
                source["metadata"] = deepcopy(
                    source.get("active_metadata") or source.get("metadata", {})
                )
                source["governance"] = deepcopy(
                    source.get("active_governance") or source.get("governance", {})
                )
            source["pending_action"] = ""
            source["pending_asset_version_id"] = ""
            self._refresh_source_readiness(source)
            self._write(catalog)
            return deepcopy(source)

    def delete_draft(self, source_id: str) -> None:
        with self._lock:
            catalog = self.read()
            source = self._find_source(catalog, source_id)
            if source.get("active_asset_version_id"):
                raise SourceCatalogError("已上线来源不能物理删除，请执行下架")
            catalog["sources"].remove(source)
            self._write(catalog)

    def _selected_version(self, source: dict[str, Any]) -> dict[str, Any] | None:
        selected_id = (
            source.get("pending_asset_version_id")
            if source.get("pending_action") in {"add", "replace"}
            else source.get("active_asset_version_id")
        )
        return next(
            (
                item
                for item in source.get("versions", [])
                if item["asset_version_id"] == selected_id
            ),
            None,
        )

    def plan_changes(self) -> dict[str, Any]:
        catalog = self.read()
        changes = {
            "added": [],
            "updated": [],
            "replaced": [],
            "retired": [],
            "unchanged": [],
        }
        blockers: list[dict[str, str]] = []
        desired: list[dict[str, Any]] = []
        retirements: list[dict[str, str]] = []
        filenames: set[str] = set()
        for source in catalog["sources"]:
            action = source.get("pending_action")
            if action == "retire":
                changes["retired"].append(source["source_id"])
                retirements.append(
                    {
                        "source_id": source["source_id"],
                        "source_updated_at": str(source.get("updated_at") or ""),
                        "active_asset_version_id": str(source.get("active_asset_version_id") or ""),
                    }
                )
                continue
            version = self._selected_version(source)
            metadata = source.get("metadata", {})
            if (
                not version
                or version.get("validation_status") != "validated"
                or not metadata.get("code")
                or not metadata.get("name")
            ):
                if action or source.get("active_asset_version_id"):
                    blockers.append(
                        {"source_id": source["source_id"], "message": "PDF、规范编号和名称必须完整"}
                    )
                continue
            governance = source.get("governance", {})
            if governance.get("rights_status") == "C":
                blockers.append(
                    {"source_id": source["source_id"], "message": "权利状态 C 禁止进入知识库"}
                )
                continue
            if governance.get("rights_status") in {"B", "unknown"} and (
                metadata.get("image_access") == "public"
                or metadata.get("page_image_access") == "public"
            ):
                blockers.append(
                    {
                        "source_id": source["source_id"],
                        "message": "内部或待确认来源不能配置公开图片访问",
                    }
                )
                continue
            filename = _safe_pdf_name(
                str(metadata.get("source_file") or version["original_filename"])
            )
            if filename in filenames:
                blockers.append(
                    {"source_id": source["source_id"], "message": f"来源文件名重复：{filename}"}
                )
                continue
            filenames.add(filename)
            desired.append(
                {
                    "source_id": source["source_id"],
                    "asset_version_id": version["asset_version_id"],
                    "sha256": version["sha256"],
                    "object_path": version["object_path"],
                    "source_file": filename,
                    "metadata": {**metadata, "source_file": filename},
                    "governance": source.get("governance", {}),
                    "source_updated_at": str(source.get("updated_at") or ""),
                }
            )
            bucket = {"add": "added", "replace": "replaced", "update": "updated"}.get(
                action, "unchanged"
            )
            changes[bucket].append(source["source_id"])
        return {
            "catalog_revision": catalog["revision"],
            "active_revision_id": catalog.get("active_revision_id", ""),
            "changes": changes,
            "desired_source_count": len(desired),
            "blockers": blockers,
            "ready": not blockers and bool(desired),
            "desired": desired,
            "_retirements": retirements,
        }

    def create_revision(self) -> dict[str, Any]:
        with self._lock:
            catalog = self.read()
            if any(item.get("status") == "candidate" for item in catalog["revisions"]):
                raise SourceCatalogError("已有候选来源 revision 正在构建")
            plan = self.plan_changes()
            if not plan["ready"]:
                messages = "; ".join(item["message"] for item in plan["blockers"])
                raise SourceCatalogError(messages or "没有可构建的规范来源")
            revision_id = f"src-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
            revision_dir = self.revisions_dir / revision_id
            input_dir = revision_dir / "input"
            input_dir.mkdir(parents=True, exist_ok=False)
            try:
                documents = []
                for item in plan["desired"]:
                    source_path = self._object_path(item)
                    if not source_path.is_file() or _sha256(source_path) != item["sha256"]:
                        raise SourceCatalogError(f"来源资产缺失或哈希不一致：{item['source_id']}")
                    validate_pdf(source_path)
                    target = input_dir / item["source_file"]
                    try:
                        os.link(source_path, target)
                    except OSError:
                        shutil.copy2(source_path, target)
                    documents.append(item["metadata"])
                metadata_path = revision_dir / "specs.json"
                _atomic_write_json(metadata_path, {"documents": documents})
                snapshot = {
                    "schema_version": SCHEMA_VERSION,
                    "revision_id": revision_id,
                    "catalog_revision": plan["catalog_revision"],
                    "created_at": utc_now(),
                    "status": "candidate",
                    "changes": plan["changes"],
                    "sources": plan["desired"],
                    "retirements": plan["_retirements"],
                    "input_dir": input_dir.relative_to(self.data_dir).as_posix(),
                    "metadata_path": metadata_path.relative_to(self.data_dir).as_posix(),
                }
                _atomic_write_json(revision_dir / "snapshot.json", snapshot)
            except Exception:
                shutil.rmtree(revision_dir, ignore_errors=True)
                raise
            catalog["revisions"].append(
                {
                    "revision_id": revision_id,
                    "status": "candidate",
                    "created_at": snapshot["created_at"],
                    "source_count": len(plan["desired"]),
                    "changes": plan["changes"],
                    "error": "",
                    "data_version_hash": "",
                }
            )
            self._write(catalog)
            return snapshot

    def revision(self, revision_id: str) -> dict[str, Any]:
        path = self.revisions_dir / revision_id / "snapshot.json"
        if not path.exists():
            raise KeyError(revision_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def resolve_source_pdf(
        self, source_file: str, *, revision_id: str | None = None
    ) -> Path | None:
        """Resolve an active source PDF without exposing catalog paths to callers."""
        requested = Path(source_file).name.casefold()
        requested_stem = Path(requested).stem

        def matches(candidate: str) -> bool:
            name = Path(candidate).name.casefold()
            return requested in {name, Path(name).stem} or requested_stem == Path(name).stem

        catalog = self.read()
        selected_revision_id = revision_id or str(catalog.get("active_revision_id") or "")
        if selected_revision_id:
            try:
                snapshot = self.revision(selected_revision_id)
            except KeyError:
                snapshot = None
            if snapshot:
                input_dir = (self.data_dir / str(snapshot.get("input_dir") or "")).resolve()
                try:
                    input_dir.relative_to(self.data_dir)
                except ValueError:
                    input_dir = None
                if input_dir and input_dir.is_dir():
                    for item in snapshot.get("sources", []):
                        candidate_name = str(item.get("source_file") or "")
                        if (
                            candidate_name
                            and Path(candidate_name).name == candidate_name
                            and matches(candidate_name)
                        ):
                            candidate = input_dir / candidate_name
                            if candidate.is_file():
                                return candidate

        for source in catalog.get("sources", []):
            if not source.get("active_asset_version_id"):
                continue
            metadata = source.get("active_metadata") or source.get("metadata") or {}
            candidate_name = str(metadata.get("source_file") or "")
            if not candidate_name or not matches(candidate_name):
                continue
            version_id = str(source.get("active_asset_version_id") or "")
            version = next(
                (
                    item
                    for item in source.get("versions", [])
                    if str(item.get("asset_version_id") or "") == version_id
                ),
                None,
            )
            if not version:
                continue
            try:
                candidate = self._object_path(version)
            except SourceCatalogError:
                continue
            if candidate.is_file():
                return candidate
        return None

    def validate_republish_revision(self, revision_id: str) -> dict[str, Any]:
        """Validate that a failed source snapshot is still safe to publish."""
        with self._lock:
            catalog = self.read()
            record = next(
                (item for item in catalog["revisions"] if item["revision_id"] == revision_id),
                None,
            )
            if record is None:
                raise SourceCatalogError("来源 revision 不存在")
            if record.get("status") != "failed":
                raise SourceCatalogError("只有失败的来源候选可以重试发布")
            if catalog.get("active_revision_id") == revision_id:
                raise SourceCatalogError("来源 revision 已经是活动版本")

            snapshot = self.revision(revision_id)
            plan = self.plan_changes()
            if not plan["ready"]:
                messages = "; ".join(item["message"] for item in plan["blockers"])
                raise SourceCatalogError(messages or "当前来源目录不能发布")

            expected_sources = sorted(
                snapshot.get("sources", []), key=lambda item: str(item.get("source_id", ""))
            )
            current_sources = sorted(
                plan.get("desired", []), key=lambda item: str(item.get("source_id", ""))
            )
            if json.dumps(expected_sources, ensure_ascii=False, sort_keys=True) != json.dumps(
                current_sources, ensure_ascii=False, sort_keys=True
            ):
                raise SourceCatalogError("来源目录在候选生成后发生变化，请重新生成候选")
            expected_retirements = sorted(
                snapshot.get("retirements", []), key=lambda item: str(item.get("source_id", ""))
            )
            current_retirements = sorted(
                plan.get("_retirements", []), key=lambda item: str(item.get("source_id", ""))
            )
            if expected_retirements != current_retirements:
                raise SourceCatalogError("来源下架计划在候选生成后发生变化，请重新生成候选")
            return deepcopy(snapshot)

    def activate_revision(self, revision_id: str, data_version_hash: str) -> None:
        with self._lock:
            catalog = self.read()
            snapshot = self.revision(revision_id)
            included = {item["source_id"]: item for item in snapshot["sources"]}
            retired = {item["source_id"]: item for item in snapshot.get("retirements", [])}
            for source in catalog["sources"]:
                item = included.get(source["source_id"])
                if item:
                    changed_after_snapshot = source.get("updated_at") != item.get(
                        "source_updated_at"
                    )
                    source["active_asset_version_id"] = item["asset_version_id"]
                    source["active_metadata"] = deepcopy(item.get("metadata", {}))
                    source["active_governance"] = deepcopy(item.get("governance", {}))
                    source["lifecycle_status"] = "active"
                    if changed_after_snapshot:
                        if source.get("pending_action") == "add":
                            source["pending_action"] = "update"
                            source["pending_asset_version_id"] = ""
                    else:
                        source["metadata"] = deepcopy(item.get("metadata", {}))
                        source["governance"] = deepcopy(item.get("governance", {}))
                        source["pending_asset_version_id"] = ""
                        source["pending_action"] = ""
                elif source["source_id"] in retired:
                    retirement = retired[source["source_id"]]
                    changed_after_snapshot = source.get("updated_at") != retirement.get(
                        "source_updated_at"
                    )
                    previous_asset = str(source.get("active_asset_version_id") or "")
                    source["active_asset_version_id"] = ""
                    if changed_after_snapshot and source.get("pending_action") != "retire":
                        source["pending_action"] = "add"
                        source["pending_asset_version_id"] = previous_asset
                        source["lifecycle_status"] = "ready"
                    else:
                        source["pending_action"] = ""
                        source["pending_asset_version_id"] = ""
                        source["lifecycle_status"] = "retired"
                source["updated_at"] = utc_now()
            for revision in catalog["revisions"]:
                if revision["revision_id"] == revision_id:
                    revision["status"] = "active"
                    revision["data_version_hash"] = data_version_hash
                elif revision["status"] == "active":
                    revision["status"] = "superseded"
            catalog["active_revision_id"] = revision_id
            self._write(catalog)

    def fail_revision(self, revision_id: str, error: str) -> None:
        with self._lock:
            catalog = self.read()
            for revision in catalog["revisions"]:
                if revision["revision_id"] == revision_id:
                    revision["status"] = "failed"
                    revision["error"] = error[:2000]
            self._write(catalog)

    def bootstrap_legacy(self, raw_dir: Path, metadata_path: Path) -> dict[str, Any]:
        with self._lock:
            catalog_existed = self.catalog_path.exists()
            original_catalog = self.read()
            if original_catalog["sources"]:
                raise SourceCatalogError("来源目录已有数据，不能重复导入")
            try:
                overrides = load_metadata_overrides(metadata_path)
                imported = []
                for pdf in sorted(raw_dir.glob("*.pdf")):
                    override = overrides.get(pdf.name, {})
                    if override.get("status") == "test":
                        continue
                    source = self.register_upload(pdf, pdf.name)
                    if override:
                        source = self.update_source(source["source_id"], override, {})
                    imported.append(source["source_id"])
                if not imported:
                    raise SourceCatalogError("data/raw 中没有可导入的 PDF")
                snapshot = self.create_revision()
                self.activate_revision(snapshot["revision_id"], "legacy-current")
                return {
                    "imported_count": len(imported),
                    "revision_id": snapshot["revision_id"],
                }
            except Exception:
                if catalog_existed:
                    _atomic_write_json(self.catalog_path, original_catalog)
                else:
                    self.catalog_path.unlink(missing_ok=True)
                raise
