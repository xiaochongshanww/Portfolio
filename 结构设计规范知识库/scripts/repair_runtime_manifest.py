from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import chromadb
except ImportError:  # pragma: no cover - reported as a CLI error
    chromadb = None

from src.pipeline.active_db import (
    read_active_db,
    resolve_pointer_path,
    write_active_db,
)
from src.pipeline.manifest import compute_data_version_hash, read_manifest, write_manifest
from src.pipeline.paths import ACTIVE_DB_PATH, DB_VERSIONS_DIR, MANIFEST_PATH
from src.quality import (
    CandidateActivationAssessment,
    assess_candidate_activation,
    write_candidate_activation_artifacts,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUALITY_REPORTS_DIR = PROJECT_ROOT / "data" / "audit" / "reports"


class RuntimeManifestRepairError(RuntimeError):
    pass


def _resolve_active_paths(active_db_path: Path) -> tuple[dict[str, Any], Path, Path]:
    active_db = read_active_db(active_db_path)
    db_dir = resolve_pointer_path(
        active_db.get("active_db_dir"), active_db_path, active_db_path.parent
    )
    manifest_path = resolve_pointer_path(
        active_db.get("manifest"), active_db_path, active_db_path.parent / "manifest.json"
    )
    manifest = read_manifest(manifest_path) or {}
    if not manifest:
        raise RuntimeManifestRepairError(f"活动 manifest 不存在或为空：{manifest_path}")
    if not db_dir.is_dir():
        raise RuntimeManifestRepairError(f"活动数据库目录不存在：{db_dir}")
    return active_db, db_dir, manifest_path


def _runtime_source_counts(db_dir: Path, collection_name: str) -> Counter[str]:
    if chromadb is None:
        raise RuntimeManifestRepairError("缺少 chromadb，无法核对活动数据库来源")
    try:
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection(collection_name)
        payload = collection.get(include=["metadatas"])
    except Exception as exc:
        raise RuntimeManifestRepairError(f"无法读取活动数据库来源：{exc}") from exc
    metadatas = payload.get("metadatas") or []
    return Counter(
        str(item.get("source_file") or "") for item in metadatas if isinstance(item, dict)
    )


def _runtime_corpus_digest(db_dir: Path, collection_name: str) -> str:
    if chromadb is None:
        raise RuntimeManifestRepairError("缺少 chromadb，无法计算运行语料摘要")
    try:
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection(collection_name)
        payload = collection.get(include=["documents", "metadatas"])
    except Exception as exc:
        raise RuntimeManifestRepairError(f"无法读取运行语料：{exc}") from exc
    ids = payload.get("ids") or []
    documents = payload.get("documents") or []
    metadatas = payload.get("metadatas") or []
    records = [
        {"id": ids[index], "document": documents[index], "metadata": metadatas[index]}
        for index in range(len(ids))
    ]
    stable = json.dumps(
        sorted(records, key=lambda item: str(item["id"])), ensure_ascii=False, sort_keys=True
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _read_quality_artifacts(active_data_version_hash: str) -> dict[str, Any]:
    pointer_path = QUALITY_REPORTS_DIR / "quality_run_latest.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    if pointer.get("status") != "complete" or pointer.get("passed") is not True:
        raise RuntimeManifestRepairError("最近一次完整质量证据不是 passed")
    run_id = str(pointer.get("verification_run_id") or "")
    run_dir = QUALITY_REPORTS_DIR / "runs" / run_id
    run_manifest_path = run_dir / "manifest.json"
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    if run_manifest.get("passed") is not True:
        raise RuntimeManifestRepairError("最近一次质量运行清单不是 passed")
    expected_manifest_hash = str(pointer.get("manifest_sha256") or "")
    actual_manifest_hash = hashlib.sha256(run_manifest_path.read_bytes()).hexdigest()
    if expected_manifest_hash != actual_manifest_hash:
        raise RuntimeManifestRepairError("质量运行清单 SHA-256 不一致")

    artifact_payloads: dict[str, dict[str, Any]] = {}
    for key in ("regular_json", "structured_json", "answer_json", "gate_json"):
        artifact = run_manifest.get("artifacts", {}).get(key)
        if not isinstance(artifact, dict):
            raise RuntimeManifestRepairError(f"质量运行缺少 {key}")
        artifact_path = run_dir / str(artifact.get("filename") or "")
        if hashlib.sha256(artifact_path.read_bytes()).hexdigest() != artifact.get("sha256"):
            raise RuntimeManifestRepairError(f"质量产物 SHA-256 不一致：{key}")
        artifact_payloads[key] = json.loads(artifact_path.read_text(encoding="utf-8"))

    for key in ("regular_json", "structured_json", "answer_json"):
        if artifact_payloads[key].get("ok") is not True:
            raise RuntimeManifestRepairError(f"质量产物未通过：{key}")
        if artifact_payloads[key].get("data_version_hash") != active_data_version_hash:
            raise RuntimeManifestRepairError(f"质量产物数据版本不匹配：{key}")
    if artifact_payloads["gate_json"].get("passed") is not True:
        raise RuntimeManifestRepairError("质量门禁产物不是 passed")
    return {
        "verification_run_id": run_id,
        "data_version_hash": active_data_version_hash,
        "regular": artifact_payloads["regular_json"],
        "structured": artifact_payloads["structured_json"],
        "answer": artifact_payloads["answer_json"],
    }


def _aggregate_documents(documents: list[dict[str, Any]]) -> dict[str, Any]:
    missing_artifacts = [
        {
            "source_file": document["source_file"],
            "kind": artifact["kind"],
            "required": artifact["required"],
        }
        for document in documents
        for artifact in document.get("artifacts", [])
        if artifact.get("status") != "ok"
    ]
    return {
        "metadata_status": (
            "partial"
            if any(document.get("metadata_status") == "partial" for document in documents)
            else "complete"
        ),
        "audit_status": {
            "finding_count": sum(
                document.get("audit", {}).get("finding_count", 0) for document in documents
            ),
            "high_risk_count": sum(
                document.get("audit", {}).get("high_risk_count", 0) for document in documents
            ),
        },
        "correction_status": {
            "approved_count": sum(
                document.get("corrections", {}).get("approved_count", 0) for document in documents
            ),
            "applied_count": sum(
                document.get("corrections", {}).get("applied_count", 0) for document in documents
            ),
            "skipped_count": sum(
                document.get("corrections", {}).get("skipped_count", 0) for document in documents
            ),
        },
        "artifact_status": {
            "missing_count": len(missing_artifacts),
            "missing_required_count": sum(1 for item in missing_artifacts if item["required"]),
            "missing": missing_artifacts,
        },
    }


def _equivalent_candidate_assessment(
    *,
    active_db_dir: Path,
    candidate_db_dir: Path,
    candidate_manifest: dict[str, Any],
    collection_name: str,
) -> CandidateActivationAssessment:
    active_digest = _runtime_corpus_digest(active_db_dir, collection_name)
    candidate_digest = _runtime_corpus_digest(candidate_db_dir, collection_name)
    if active_digest != candidate_digest:
        raise RuntimeManifestRepairError("候选数据库与活动数据库的运行语料摘要不一致")
    active_hash = str(
        candidate_manifest.get("build_params", {}).get("source_data_version_hash") or ""
    )
    evidence = _read_quality_artifacts(active_hash)
    regular = dict(evidence["regular"])
    structured = dict(evidence["structured"])
    answer = dict(evidence["answer"])
    for payload in (regular, structured, answer):
        payload.update(
            {
                "data_version_hash": candidate_manifest["data_version_hash"],
                "evidence_mode": "inherited_runtime_corpus_equivalence",
                "inherited_from_data_version_hash": active_hash,
                "runtime_corpus_sha256": candidate_digest,
            }
        )
    verification_run_id = evidence["verification_run_id"]
    checks = [
        {
            "name": "candidate_runtime",
            "status": "passed",
            "severity": "info",
            "message": f"候选集合 {candidate_manifest['chunk_count']} 条且可独立打开",
            "details": {"collection_count": candidate_manifest["chunk_count"]},
        },
        {
            "name": "runtime_corpus_equivalence",
            "status": "passed",
            "severity": "info",
            "message": "候选与活动数据库的 ID、文本和元数据摘要完全一致",
            "details": {"sha256": candidate_digest},
        },
        {
            "name": "regular_evaluation",
            "status": "passed",
            "severity": "info",
            "message": "继承语料等价的 100 项常规评估",
            "details": {"verification_run_id": verification_run_id},
        },
        {
            "name": "structured_evaluation",
            "status": "passed",
            "severity": "info",
            "message": "继承语料等价的 12 项结构化评估",
            "details": {"verification_run_id": verification_run_id},
        },
        {
            "name": "answer_evaluation",
            "status": "passed",
            "severity": "info",
            "message": "继承语料等价的回答级盲测，不重新调用模型",
            "details": {"verification_run_id": verification_run_id},
        },
    ]
    result = {
        "schema_version": 1,
        "gate": "candidate_activation",
        "generated_at": datetime.now(UTC).isoformat(),
        "passed": True,
        "failed_checks": [],
        "checks": checks,
        "data_version_hash": candidate_manifest["data_version_hash"],
        "manifest_path": "",
        "db_dir": str(candidate_db_dir),
        "answer_evaluation_included": True,
        "answer_evaluation_note": "本候选只修复运行 manifest；候选数据库与活动数据库逐条等价，因此继承已封存质量证据。",
        "evidence_mode": "inherited_runtime_corpus_equivalence",
        "inherited_from_data_version_hash": active_hash,
        "runtime_corpus_sha256": candidate_digest,
    }
    return CandidateActivationAssessment(result, None, regular, structured)


def build_repaired_manifest(
    manifest: dict[str, Any], *, candidate_db_dir: Path
) -> tuple[dict[str, Any], list[str]]:
    documents = manifest.get("documents")
    if not isinstance(documents, list) or not documents:
        raise RuntimeManifestRepairError("活动 manifest 缺少 documents")
    production_documents = [
        document
        for document in documents
        if isinstance(document, dict) and document.get("status") != "test"
    ]
    excluded_sources = [
        str(document.get("source_file") or "")
        for document in documents
        if isinstance(document, dict) and document.get("status") == "test"
    ]
    if not excluded_sources:
        raise RuntimeManifestRepairError("活动 manifest 不包含可移除的 test 来源")
    if not all(str(document.get("source_file") or "").strip() for document in production_documents):
        raise RuntimeManifestRepairError("生产文档缺少 source_file")

    chunk_count = sum(int(document.get("chunk_count", 0)) for document in production_documents)
    repaired = dict(manifest)
    repaired["built_at"] = datetime.now(UTC).isoformat()
    repaired["documents"] = production_documents
    repaired["document_count"] = len(production_documents)
    repaired["chunk_count"] = chunk_count
    build_params = dict(manifest.get("build_params") or {})
    build_params.update(
        {
            "mode": "runtime-manifest-repair",
            "db_dir": str(candidate_db_dir),
            "loaded_chunks": chunk_count,
            "excluded_test_sources": excluded_sources,
        }
    )
    repaired["build_params"] = build_params
    repaired.update(_aggregate_documents(production_documents))
    repaired["data_version_hash"] = compute_data_version_hash(
        {
            "documents": production_documents,
            "embedding_model": repaired.get("embedding_model", ""),
            "collection_name": repaired.get("collection_name", ""),
            "build_params": build_params,
        }
    )
    return repaired, excluded_sources


def _snapshot(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def _restore(path: Path, content: bytes | None) -> None:
    if content is None:
        path.unlink(missing_ok=True)
        return
    temporary = path.with_suffix(f"{path.suffix}.repair-rollback.tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def repair_runtime_manifest(
    *,
    active_db_path: Path = ACTIVE_DB_PATH,
    root_manifest_path: Path = MANIFEST_PATH,
    candidate_dir: Path | None = None,
    collection_name: str = "design_specs",
    activate: bool = False,
    reuse_equivalent_evidence: bool = False,
) -> dict[str, Any]:
    active_db_path = active_db_path.resolve()
    root_manifest_path = root_manifest_path.resolve()
    active_db, active_db_dir, active_manifest_path = _resolve_active_paths(active_db_path)
    active_manifest = read_manifest(active_manifest_path) or {}
    source_counts = _runtime_source_counts(active_db_dir, collection_name)
    documents = active_manifest.get("documents", [])
    expected_counts = Counter(
        {
            str(document.get("source_file") or ""): int(document.get("chunk_count", 0))
            for document in documents
            if isinstance(document, dict) and document.get("status") != "test"
        }
    )
    if source_counts != expected_counts:
        raise RuntimeManifestRepairError(
            f"活动数据库来源计数与生产 manifest 不一致：实际={dict(source_counts)}，"
            f"期望={dict(expected_counts)}"
        )
    if any(key and key.endswith(".pdf") and key not in expected_counts for key in source_counts):
        raise RuntimeManifestRepairError("活动数据库包含未登记的生产来源")

    candidate_dir = (
        candidate_dir
        or DB_VERSIONS_DIR / f"runtime-manifest-repair-{datetime.now(UTC):%Y%m%d%H%M%S}"
    ).resolve()
    if candidate_dir.exists():
        raise RuntimeManifestRepairError(f"候选目录已存在：{candidate_dir}")
    candidate_db_dir = candidate_dir / "db"
    candidate_manifest_path = candidate_dir / "manifest.json"
    candidate_quality_dir = candidate_dir / "quality"
    candidate_dir.mkdir(parents=True)
    try:
        shutil.copytree(active_db_dir, candidate_db_dir)
        repaired_manifest, excluded_sources = build_repaired_manifest(
            active_manifest, candidate_db_dir=candidate_db_dir
        )
        repaired_manifest["build_params"] = {
            **repaired_manifest.get("build_params", {}),
            "source_data_version_hash": active_manifest.get("data_version_hash", ""),
        }
        repaired_manifest["data_version_hash"] = compute_data_version_hash(
            {
                "documents": repaired_manifest["documents"],
                "embedding_model": repaired_manifest.get("embedding_model", ""),
                "collection_name": repaired_manifest.get("collection_name", ""),
                "build_params": repaired_manifest["build_params"],
            }
        )
        write_manifest(candidate_manifest_path, repaired_manifest)
        if reuse_equivalent_evidence:
            assessment = _equivalent_candidate_assessment(
                active_db_dir=active_db_dir,
                candidate_db_dir=candidate_db_dir,
                candidate_manifest=repaired_manifest,
                collection_name=collection_name,
            )
        else:
            assessment = assess_candidate_activation(
                manifest_path=candidate_manifest_path,
                db_dir=candidate_db_dir,
            )
        gate_artifacts = write_candidate_activation_artifacts(assessment, candidate_quality_dir)
        result: dict[str, Any] = {
            "ok": assessment.result.get("passed") is True,
            "activated": False,
            "candidate_dir": str(candidate_dir),
            "candidate_manifest": str(candidate_manifest_path),
            "candidate_db": str(candidate_db_dir),
            "excluded_test_sources": excluded_sources,
            "source_counts": dict(source_counts),
            "candidate_gate": assessment.result,
            "candidate_gate_report": gate_artifacts["gate_report"],
        }
        if not result["ok"] or not activate:
            return result

        old_root_manifest = _snapshot(root_manifest_path)
        old_active_db = _snapshot(active_db_path)
        pointer = dict(active_db)
        pointer.update(
            {
                "active_db_dir": str(candidate_db_dir),
                "manifest": str(candidate_manifest_path),
                "job_id": candidate_dir.name,
                "data_version_hash": repaired_manifest["data_version_hash"],
                "chunk_count": repaired_manifest["chunk_count"],
                "activated_at": datetime.now(UTC).isoformat(),
                "candidate_gate_report": gate_artifacts["gate_report"],
            }
        )
        try:
            write_manifest(root_manifest_path, repaired_manifest)
            write_active_db(pointer, active_db_path)
        except Exception:
            _restore(active_db_path, old_active_db)
            _restore(root_manifest_path, old_root_manifest)
            raise
        result["activated"] = True
        result["active_manifest"] = str(root_manifest_path)
        result["active_db_pointer"] = str(active_db_path)
        result["reload_required"] = True
        return result
    except Exception:
        if (
            not activate
            or not (candidate_dir / "quality" / "candidate_activation_gate.json").is_file()
        ):
            shutil.rmtree(candidate_dir, ignore_errors=True)
        raise


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="通过候选门禁修复活动运行 manifest 的测试来源漂移")
    parser.add_argument("--active-db", type=Path, default=ACTIVE_DB_PATH)
    parser.add_argument("--root-manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--candidate-dir", type=Path)
    parser.add_argument("--collection", default="design_specs")
    parser.add_argument("--activate", action="store_true", help="候选门禁通过后原子切换活动指针")
    parser.add_argument(
        "--reuse-equivalent-evidence",
        action="store_true",
        help="仅在候选数据库与活动数据库逐条等价时继承已封存质量证据",
    )
    args = parser.parse_args()
    try:
        result = repair_runtime_manifest(
            active_db_path=args.active_db,
            root_manifest_path=args.root_manifest,
            candidate_dir=args.candidate_dir,
            collection_name=args.collection,
            activate=args.activate,
            reuse_equivalent_evidence=args.reuse_equivalent_evidence,
        )
    except (RuntimeManifestRepairError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
