import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from src.pipeline.active_db import active_db_dir, read_active_manifest
from src.pipeline.knowledge_package import (
    KnowledgePackageError,
    export_runtime_package,
    import_runtime_package,
    validate_runtime_package,
)


@pytest.fixture(autouse=True)
def passing_quality_gate(monkeypatch):
    monkeypatch.setattr(
        "src.pipeline.knowledge_package.evaluate_quality_gate",
        lambda **_: {
            "generated_at": "2026-08-08T00:00:00+00:00",
            "passed": True,
            "failed_checks": [],
            "checks": [],
            "jobs": {},
            "data_version_hash": "a" * 64,
        },
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _source_runtime(tmp_path: Path) -> dict[str, Path]:
    project = tmp_path / "source"
    data = project / "data"
    version = data / "db_versions" / "build-1"
    database = version / "db"
    database.mkdir(parents=True)
    (database / "chroma.sqlite3").write_bytes(b"sqlite-data")
    (database / "segment" / "header.bin").parent.mkdir()
    (database / "segment" / "header.bin").write_bytes(b"index-data")

    manifest = {
        "schema_version": 1,
        "built_at": "2026-08-08T00:00:00+00:00",
        "documents": [
            {
                "source_file": "GB 50009-2012_测试规范.pdf",
                "code": "GB 50009-2012",
                "name": "测试规范",
                "chunk_count": 2,
            }
        ],
        "document_count": 1,
        "chunk_count": 2,
        "image_count": 1,
        "embedding_model": "embedding-2",
        "collection_name": "design_specs",
        "data_version_hash": "a" * 64,
    }
    manifest_path = version / "manifest.json"
    _write_json(manifest_path, manifest)
    _write_json(
        data / "active_db.json",
        {
            "active_db_dir": str(database),
            "images_dir": str(data / "images"),
            "manifest": str(manifest_path),
            "data_version_hash": manifest["data_version_hash"],
        },
    )
    structured = data / "structured_tables"
    _write_json(structured / "table.json", {"schema_version": "0.1", "rows": [{"item": "办公室", "value": 2.0}]})
    images = data / "images"
    images.mkdir()
    (images / "preview.png").write_bytes(b"png-data")
    metadata = data / "metadata"
    _write_json(
        metadata / "specs.json",
        {
            "documents": [
                {
                    "source_file": "GB 50009-2012_测试规范.pdf",
                    "image_access": "authenticated",
                    "page_image_access": "authenticated",
                }
            ]
        },
    )
    raw = data / "raw"
    raw.mkdir()
    (raw / "GB 50009-2012_测试规范.pdf").write_bytes(b"%PDF-test")
    (raw / "ignore.txt").write_text("not a PDF", encoding="utf-8")
    return {
        "project": project,
        "data": data,
        "active": data / "active_db.json",
        "database": database,
        "manifest": manifest_path,
        "structured": structured,
        "images": images,
        "metadata": metadata,
        "raw": raw,
    }


def _export(tmp_path: Path, *, include_source_pdfs: bool = False) -> Path:
    source = _source_runtime(tmp_path)
    package = tmp_path / "runtime-package.zip"
    result = export_runtime_package(
        package,
        active_db_path=source["active"],
        fallback_manifest_path=source["manifest"],
        structured_tables_dir=source["structured"],
        images_dir=source["images"],
        metadata_dir=source["metadata"],
        raw_dir=source["raw"],
        include_source_pdfs=include_source_pdfs,
        export_actor="test-suite",
        export_audit_dir=source["data"] / "audit" / "package_exports",
    )
    assert result["ok"] is True
    return package


def test_runtime_package_round_trip_without_source_pdfs(tmp_path: Path):
    package = _export(tmp_path)

    validation = validate_runtime_package(package)

    assert validation["valid"] is True
    assert validation["package_id"].startswith("kp-" + "a" * 12 + "-")
    assert validation["capabilities"] == {
        "prebuilt_vector_index": True,
        "structured_tables": True,
        "extracted_images": True,
        "source_pdfs": False,
        "page_images": False,
        "source_access_policy": True,
    }
    assert validation["quality"]["gate_passed"] is True
    assert validation["quality"]["waiver"]["used"] is False
    with zipfile.ZipFile(package) as archive:
        package_manifest = json.loads(archive.read("knowledge-package.json"))
        names = set(archive.namelist())
        assert package_manifest["schema_version"] == 4
        audit_event_id = package_manifest["quality"]["audit_event_id"]
        audit_record = tmp_path / "source" / "data" / "audit" / "package_exports" / f"{audit_event_id}.json"
        assert json.loads(audit_record.read_text(encoding="utf-8"))["outcome"] == "exported"
        assert "knowledge-package.json" in names
        assert "runtime/manifest.json" in names
        assert "runtime/db/chroma.sqlite3" in names
        assert "runtime/structured_tables/table.json" in names
        assert "runtime/images/preview.png" in names
        assert "runtime/metadata/specs.json" in names
        assert not any(name.startswith("runtime/raw/") for name in names)

    target_data = tmp_path / "target" / "data"
    imported = import_runtime_package(package, data_dir=target_data)
    active = json.loads((target_data / "active_db.json").read_text(encoding="utf-8"))

    assert imported["activated"] is True
    assert imported["restart_required"] is True
    assert active_db_dir(target_data / "active_db.json").is_dir()
    assert read_active_manifest(target_data / "active_db.json")["data_version_hash"] == "a" * 64
    assert active["data_version_hash"] == "a" * 64
    assert (target_data / "structured_tables" / "table.json").is_file()
    assert (target_data / "images" / "preview.png").read_bytes() == b"png-data"
    assert (target_data / "metadata" / "specs.json").is_file()
    assert not (target_data / "raw").exists()


def test_runtime_package_includes_only_pdfs_when_explicit(tmp_path: Path):
    default_package = _export(tmp_path / "default")
    default_id = validate_runtime_package(default_package)["package_id"]
    package = _export(tmp_path / "with-pdf", include_source_pdfs=True)

    validation = validate_runtime_package(package)

    assert validation["package_id"] != default_id
    assert validation["capabilities"]["source_pdfs"] is True
    assert validation["capabilities"]["page_images"] is True
    with zipfile.ZipFile(package) as archive:
        names = set(archive.namelist())
        assert "runtime/raw/GB 50009-2012_测试规范.pdf" in names
        assert "runtime/raw/ignore.txt" not in names


def test_runtime_package_rejects_hash_tampering(tmp_path: Path):
    package = _export(tmp_path)
    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(package) as source, zipfile.ZipFile(tampered, "w") as target:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename == "runtime/db/chroma.sqlite3":
                content = bytes([content[0] ^ 0xFF]) + content[1:]
            target.writestr(info.filename, content)

    with pytest.raises(KnowledgePackageError, match="SHA-256 不匹配"):
        validate_runtime_package(tampered)


def test_runtime_package_rejects_invalid_file_metadata_cleanly(tmp_path: Path):
    package = _export(tmp_path)
    malformed = tmp_path / "malformed.zip"
    with zipfile.ZipFile(package) as source, zipfile.ZipFile(malformed, "w") as target:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename == "knowledge-package.json":
                manifest = json.loads(content.decode("utf-8"))
                manifest["files"][0]["size_bytes"] = "invalid"
                content = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
            target.writestr(info.filename, content)

    with pytest.raises(KnowledgePackageError, match="文件大小声明无效"):
        validate_runtime_package(malformed)


def test_runtime_package_rejects_output_inside_payload_directory(tmp_path: Path):
    source = _source_runtime(tmp_path)

    with pytest.raises(KnowledgePackageError, match="输出不能位于待打包目录内"):
        export_runtime_package(
            source["database"] / "knowledge.zip",
            active_db_path=source["active"],
            fallback_manifest_path=source["manifest"],
            structured_tables_dir=source["structured"],
            images_dir=source["images"],
            metadata_dir=source["metadata"],
            raw_dir=source["raw"],
        )


def test_runtime_package_rejects_path_traversal(tmp_path: Path):
    package = tmp_path / "unsafe.zip"
    manifest = {
        "format": "structural-spec-knowledge-package",
        "schema_version": 1,
        "package_id": "kp-safe",
        "profile": "runtime",
        "files": [],
    }
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("knowledge-package.json", json.dumps(manifest))
        archive.writestr("../outside.txt", b"unsafe")

    with pytest.raises(KnowledgePackageError, match="不安全路径"):
        validate_runtime_package(package)


def test_runtime_package_requires_replace_for_conflicting_assets(tmp_path: Path):
    package = _export(tmp_path)
    target_data = tmp_path / "target" / "data"
    target_image = target_data / "images" / "preview.png"
    target_image.parent.mkdir(parents=True)
    target_image.write_bytes(b"existing-different")

    with pytest.raises(KnowledgePackageError, match="--replace"):
        import_runtime_package(package, data_dir=target_data)
    assert not (target_data / "active_db.json").exists()
    assert target_image.read_bytes() == b"existing-different"

    imported = import_runtime_package(package, data_dir=target_data, replace=True)

    assert imported["activated"] is True
    assert target_image.read_bytes() == b"png-data"


def test_runtime_package_can_install_without_activation(tmp_path: Path):
    package = _export(tmp_path)
    target_data = tmp_path / "target" / "data"

    imported = import_runtime_package(package, data_dir=target_data, activate=False)

    assert imported["activated"] is False
    assert imported["restart_required"] is False
    assert Path(imported["version_dir"]).is_dir()
    assert not (target_data / "active_db.json").exists()
    assert not (target_data / "manifest.json").exists()


def test_runtime_package_blocks_failed_quality_gate_and_audits_attempt(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "src.pipeline.knowledge_package.evaluate_quality_gate",
        lambda **_: {
            "generated_at": "2026-08-08T00:00:00+00:00",
            "passed": False,
            "failed_checks": ["answer_report_freshness"],
            "checks": [],
            "jobs": {},
            "data_version_hash": "a" * 64,
        },
    )
    source = _source_runtime(tmp_path)
    package = tmp_path / "blocked.zip"
    audit_dir = source["data"] / "audit" / "package_exports"

    with pytest.raises(KnowledgePackageError, match="质量门禁未通过"):
        export_runtime_package(
            package,
            active_db_path=source["active"],
            fallback_manifest_path=source["manifest"],
            structured_tables_dir=source["structured"],
            images_dir=source["images"],
            metadata_dir=source["metadata"],
            raw_dir=source["raw"],
            export_actor="test-suite",
            export_audit_dir=audit_dir,
        )

    assert not package.exists()
    records = list(audit_dir.glob("*.json"))
    assert len(records) == 1
    blocked_audit = json.loads(records[0].read_text(encoding="utf-8"))
    assert blocked_audit["outcome"] == "blocked"
    assert blocked_audit["waiver"]["used"] is False


def test_runtime_package_requires_source_access_policy(tmp_path: Path):
    source = _source_runtime(tmp_path)
    (source["metadata"] / "specs.json").unlink()

    with pytest.raises(KnowledgePackageError, match="来源访问策略不存在"):
        export_runtime_package(
            tmp_path / "knowledge.zip",
            active_db_path=source["active"],
            fallback_manifest_path=source["manifest"],
            structured_tables_dir=source["structured"],
            images_dir=source["images"],
            metadata_dir=source["metadata"],
            raw_dir=source["raw"],
        )


def test_runtime_package_requires_complete_source_access_policy(tmp_path: Path):
    source = _source_runtime(tmp_path)
    policy_path = source["metadata"] / "specs.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["documents"][0].pop("page_image_access")
    _write_json(policy_path, policy)

    with pytest.raises(KnowledgePackageError, match="来源访问策略覆盖不完整"):
        export_runtime_package(
            tmp_path / "knowledge.zip",
            active_db_path=source["active"],
            fallback_manifest_path=source["manifest"],
            structured_tables_dir=source["structured"],
            images_dir=source["images"],
            metadata_dir=source["metadata"],
            raw_dir=source["raw"],
        )

def test_runtime_package_allows_complete_audited_quality_waiver(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "src.pipeline.knowledge_package.evaluate_quality_gate",
        lambda **_: {
            "generated_at": "2026-08-08T00:00:00+00:00",
            "passed": False,
            "failed_checks": ["answer_report_freshness"],
            "checks": [],
            "jobs": {},
            "data_version_hash": "a" * 64,
        },
    )
    source = _source_runtime(tmp_path)
    package = tmp_path / "waived.zip"
    audit_dir = source["data"] / "audit" / "package_exports"

    result = export_runtime_package(
        package,
        active_db_path=source["active"],
        fallback_manifest_path=source["manifest"],
        structured_tables_dir=source["structured"],
        metadata_dir=source["metadata"],
        raw_dir=source["raw"],
        quality_waiver_actor="release-owner",
        quality_waiver_reason="紧急回归验证期间的受控交付",
        export_actor="test-suite",
        export_audit_dir=audit_dir,
    )
    validation = validate_runtime_package(package)

    assert result["quality"]["gate_passed"] is False
    assert validation["quality"]["waiver"] == {
        "used": True,
        "actor": "release-owner",
        "reason": "紧急回归验证期间的受控交付",
    }
    audit = json.loads(Path(result["audit_record"]).read_text(encoding="utf-8"))
    assert audit["outcome"] == "exported"
    assert audit["waiver"]["used"] is True


def test_runtime_package_v1_without_quality_evidence_remains_compatible(tmp_path: Path):
    package = _export(tmp_path)
    legacy = tmp_path / "legacy-v1.zip"
    with zipfile.ZipFile(package) as source, zipfile.ZipFile(legacy, "w") as target:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename == "knowledge-package.json":
                manifest = json.loads(content.decode("utf-8"))
                manifest["schema_version"] = 1
                manifest.pop("quality")
                manifest["package_id"] = (
                    f"kp-{manifest['data_version_hash'][:12]}-{manifest['payload_hash'][:12]}"
                )
                content = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
            target.writestr(info.filename, content)

    validation = validate_runtime_package(legacy)

    assert validation["valid"] is True
    assert validation["quality"] is None


def test_runtime_package_v2_requires_consistent_quality_evidence(tmp_path: Path):
    package = _export(tmp_path)
    malformed = tmp_path / "missing-quality.zip"
    with zipfile.ZipFile(package) as source, zipfile.ZipFile(malformed, "w") as target:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename == "knowledge-package.json":
                manifest = json.loads(content.decode("utf-8"))
                manifest["schema_version"] = 2
                manifest.pop("quality")
                content = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
            target.writestr(info.filename, content)

    with pytest.raises(KnowledgePackageError, match="缺少 quality"):
        validate_runtime_package(malformed)


def test_runtime_package_v4_id_binds_quality_evidence(tmp_path: Path):
    package = _export(tmp_path)
    tampered = tmp_path / "tampered-quality.zip"
    with zipfile.ZipFile(package) as source, zipfile.ZipFile(tampered, "w") as target:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename == "knowledge-package.json":
                manifest = json.loads(content.decode("utf-8"))
                manifest["quality"]["audit_event_id"] = "different-event"
                content = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
            target.writestr(info.filename, content)

    with pytest.raises(KnowledgePackageError, match="身份元数据不一致"):
        validate_runtime_package(tampered)


def test_runtime_package_v4_id_binds_compatibility_metadata(tmp_path: Path):
    package = _export(tmp_path)
    tampered = tmp_path / "tampered-compatibility.zip"
    with zipfile.ZipFile(package) as source, zipfile.ZipFile(tampered, "w") as target:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename == "knowledge-package.json":
                manifest = json.loads(content.decode("utf-8"))
                manifest["compatibility"]["chromadb_version"] = "99.0.0"
                content = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
            target.writestr(info.filename, content)

    with pytest.raises(KnowledgePackageError, match="身份元数据不一致"):
        validate_runtime_package(tampered)


def test_runtime_package_v3_remains_compatible(tmp_path: Path):
    package = _export(tmp_path)
    legacy = tmp_path / "legacy-v3.zip"
    with zipfile.ZipFile(package) as source, zipfile.ZipFile(legacy, "w") as target:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename == "knowledge-package.json":
                manifest = json.loads(content.decode("utf-8"))
                manifest["schema_version"] = 3
                quality_json = json.dumps(
                    manifest["quality"],
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                quality_hash = hashlib.sha256(quality_json.encode("utf-8")).hexdigest()
                manifest["package_id"] = (
                    f"kp-{manifest['data_version_hash'][:12]}-"
                    f"{manifest['payload_hash'][:12]}-{quality_hash[:12]}"
                )
                content = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
            target.writestr(info.filename, content)

    validation = validate_runtime_package(legacy)

    assert validation["schema_version"] == 3
    assert validation["valid"] is True


def test_machine_architecture_aliases_do_not_create_false_warning(tmp_path: Path, monkeypatch):
    package = _export(tmp_path)
    monkeypatch.setattr("src.pipeline.knowledge_package.platform.machine", lambda: "AMD64")

    validation = validate_runtime_package(package)

    assert not any("处理器架构不同" in warning for warning in validation["warnings"])
