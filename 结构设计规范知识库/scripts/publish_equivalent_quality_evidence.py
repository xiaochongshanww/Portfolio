from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import chromadb
except ImportError:  # pragma: no cover - reported as a CLI error
    chromadb = None

from src.pipeline.active_db import read_active_db, resolve_pointer_path
from src.pipeline.manifest import read_manifest
from src.pipeline.paths import ACTIVE_DB_PATH, AUDIT_DIR, MANIFEST_PATH
from src.quality.report_store import (
    REPORT_ARTIFACTS,
    atomic_write_json,
    atomic_write_text,
    finalize_quality_run,
    load_quality_run_manifest,
    load_quality_run_pointer,
    quality_run_artifact_path,
    quality_run_directory,
    read_json_object,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUALITY_REPORTS_DIR = AUDIT_DIR / "reports"
EVIDENCE_MODE = "inherited_runtime_corpus_equivalence"


class EquivalentEvidenceError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime_corpus_digest(db_dir: Path, collection_name: str) -> str:
    if chromadb is None:
        raise EquivalentEvidenceError("缺少 chromadb，无法计算运行语料摘要")
    try:
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection(collection_name)
        payload = collection.get(include=["documents", "metadatas"])
    except Exception as exc:
        raise EquivalentEvidenceError(f"无法读取运行语料：{exc}") from exc
    ids = payload.get("ids") or []
    documents = payload.get("documents") or []
    metadatas = payload.get("metadatas") or []
    if not (len(ids) == len(documents) == len(metadatas)):
        raise EquivalentEvidenceError("运行语料的 ID、文本和元数据数量不一致")
    records = [
        {"id": ids[index], "document": documents[index], "metadata": metadatas[index]}
        for index in range(len(ids))
    ]
    stable = json.dumps(
        sorted(records, key=lambda item: str(item["id"])), ensure_ascii=False, sort_keys=True
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _active_paths(
    active_db_path: Path, fallback_manifest_path: Path
) -> tuple[dict[str, Any], Path, Path, dict[str, Any]]:
    active_db = read_active_db(active_db_path)
    db_dir = resolve_pointer_path(
        active_db.get("active_db_dir"), active_db_path, active_db_path.parent
    )
    manifest_path = resolve_pointer_path(
        active_db.get("manifest"), active_db_path, fallback_manifest_path
    )
    manifest = read_manifest(manifest_path) or {}
    if not manifest:
        raise EquivalentEvidenceError(f"活动 manifest 不存在或为空：{manifest_path}")
    if not db_dir.is_dir():
        raise EquivalentEvidenceError(f"活动数据库目录不存在：{db_dir}")
    return active_db, db_dir, manifest_path, manifest


def _candidate_gate(active_db_path: Path, active_db: dict[str, Any]) -> dict[str, Any]:
    reference = str(active_db.get("candidate_gate_report") or "").strip()
    if not reference:
        raise EquivalentEvidenceError("活动指针缺少 candidate_gate_report")
    path = resolve_pointer_path(reference, active_db_path, active_db_path.parent)
    gate = read_json_object(path)
    if gate.get("passed") is not True or gate.get("evidence_mode") != EVIDENCE_MODE:
        raise EquivalentEvidenceError("活动候选门禁不是等价语料继承模式或未通过")
    if not gate.get("runtime_corpus_sha256"):
        raise EquivalentEvidenceError("活动候选门禁缺少运行语料摘要")
    return gate


def _source_quality_run(reports_dir: Path, source_hash: str) -> tuple[str, dict[str, Any]]:
    pointer = load_quality_run_pointer(reports_dir)
    if pointer is None or pointer.get("passed") is not True:
        raise EquivalentEvidenceError("当前质量运行指针不存在或未通过")
    run_id = str(pointer.get("verification_run_id") or "")
    load_quality_run_manifest(reports_dir, run_id)
    payloads: dict[str, Any] = {}
    for report_kind in ("regular", "structured", "answer", "gate", "verification"):
        path = quality_run_artifact_path(reports_dir, run_id, f"{report_kind}_json")
        payloads[report_kind] = read_json_object(path)
    for report_kind in ("regular", "structured", "answer"):
        payload = payloads[report_kind]
        if payload.get("ok") is not True or payload.get("data_version_hash") != source_hash:
            raise EquivalentEvidenceError(f"既有 {report_kind} 评估与来源数据版本不匹配")
    if payloads["gate"].get("passed") is not True:
        raise EquivalentEvidenceError("既有质量门禁未通过")
    return run_id, payloads


def _patch_quality_payload(
    payload: dict[str, Any],
    *,
    new_run_id: str,
    candidate_hash: str,
    source_run_id: str,
    source_hash: str,
    corpus_digest: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    patched = deepcopy(payload)
    patched["verification_run_id"] = new_run_id
    patched["data_version_hash"] = candidate_hash
    patched["evidence_mode"] = EVIDENCE_MODE
    patched["inherited_from_verification_run_id"] = source_run_id
    patched["inherited_from_data_version_hash"] = source_hash
    patched["runtime_corpus_sha256"] = corpus_digest
    patched["derived_at"] = datetime.now(UTC).isoformat()

    checks = patched.get("checks")
    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, dict):
                continue
            if check.get("name") == "knowledge_base":
                check["message"] = (
                    f"知识库包含 {manifest.get('document_count', 0)} 份文档、"
                    f"{manifest.get('chunk_count', 0)} 个 chunk"
                )
            details = check.get("details")
            if isinstance(details, dict) and check.get("name") == "evaluation_run_consistency":
                details["verification_run_id"] = new_run_id
    return patched


def _patch_markdown(
    markdown: str,
    *,
    source_run_id: str,
    new_run_id: str,
    source_hash: str,
    candidate_hash: str,
    source_run_note: str,
    corpus_digest: str,
) -> str:
    text = markdown.replace(source_run_id, new_run_id).replace(source_hash, candidate_hash)
    if "知识库包含 6 份文档" in text:
        text = text.replace("知识库包含 6 份文档", "知识库包含 5 份文档")
    note = (
        "\n\n> 证据模式：继承等价运行语料。未重新调用模型；"
        f"来源运行 `{source_run_note}`，语料摘要 `{corpus_digest}`。"
    )
    return text.rstrip() + note + "\n"


def publish_equivalent_quality_evidence(
    *,
    active_db_path: Path = ACTIVE_DB_PATH,
    manifest_path: Path = MANIFEST_PATH,
    reports_dir: Path = QUALITY_REPORTS_DIR,
    collection_name: str = "design_specs",
) -> dict[str, Any]:
    active_db_path = active_db_path.resolve()
    reports_dir = reports_dir.resolve()
    active_db, db_dir, _, manifest = _active_paths(active_db_path, manifest_path.resolve())
    candidate_hash = str(manifest.get("data_version_hash") or "")
    pointer_hash = str(active_db.get("data_version_hash") or "")
    if not candidate_hash or candidate_hash != pointer_hash:
        raise EquivalentEvidenceError("活动指针与 manifest 的数据版本不一致")
    source_hash = str(manifest.get("build_params", {}).get("source_data_version_hash") or "")
    if not source_hash or source_hash == candidate_hash:
        raise EquivalentEvidenceError("活动 manifest 没有需要继承的来源数据版本")

    gate = _candidate_gate(active_db_path, active_db)
    if gate.get("data_version_hash") != candidate_hash:
        raise EquivalentEvidenceError("候选门禁与活动 manifest 的数据版本不一致")
    if gate.get("inherited_from_data_version_hash") != source_hash:
        raise EquivalentEvidenceError("候选门禁与活动 manifest 的来源数据版本不一致")
    corpus_digest = _runtime_corpus_digest(db_dir, collection_name)
    if corpus_digest != gate.get("runtime_corpus_sha256"):
        raise EquivalentEvidenceError("活动语料摘要与候选门禁不一致")

    source_run_id, payloads = _source_quality_run(reports_dir, source_hash)
    new_run_id = uuid.uuid4().hex
    new_run_dir = quality_run_directory(reports_dir, new_run_id)
    if new_run_dir.exists():
        raise EquivalentEvidenceError(f"质量运行目录已存在：{new_run_dir}")
    new_run_dir.mkdir(parents=True)
    previous_pointer = reports_dir / "quality_run_latest.json"
    compatibility_filenames = (
        "evaluation_latest.json",
        "evaluation_latest.md",
        "evaluation_structured_latest.json",
        "evaluation_structured_latest.md",
        "evaluation_answer_latest.json",
        "evaluation_answer_latest.md",
        "quality_gate_latest.json",
        "quality_gate_latest.md",
        "verification_latest.json",
        "verification_latest.md",
    )
    previous_compatibility = {
        reports_dir / filename: (reports_dir / filename).read_bytes()
        for filename in compatibility_filenames
        if (reports_dir / filename).is_file()
    }
    previous_pointer_bytes = previous_pointer.read_bytes() if previous_pointer.is_file() else None
    try:
        for report_kind, (json_name, markdown_name) in REPORT_ARTIFACTS.items():
            source_json = payloads[report_kind]
            patched = _patch_quality_payload(
                source_json,
                new_run_id=new_run_id,
                candidate_hash=candidate_hash,
                source_run_id=source_run_id,
                source_hash=source_hash,
                corpus_digest=corpus_digest,
                manifest=manifest,
            )
            atomic_write_json(new_run_dir / json_name, patched)
            source_markdown = quality_run_artifact_path(
                reports_dir, source_run_id, f"{report_kind}_markdown"
            ).read_text(encoding="utf-8")
            atomic_write_text(
                new_run_dir / markdown_name,
                _patch_markdown(
                    source_markdown,
                    source_run_id=source_run_id,
                    new_run_id=new_run_id,
                    source_hash=source_hash,
                    candidate_hash=candidate_hash,
                    source_run_note=source_run_id,
                    corpus_digest=corpus_digest,
                ),
            )
        pointer = finalize_quality_run(
            reports_dir,
            new_run_id,
            passed=True,
            completed_at=datetime.now(UTC).isoformat(),
        )
    except Exception:
        if previous_pointer_bytes is None:
            previous_pointer.unlink(missing_ok=True)
        else:
            previous_pointer.write_bytes(previous_pointer_bytes)
        for path in (reports_dir / filename for filename in compatibility_filenames):
            content = previous_compatibility.get(path)
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)
        shutil.rmtree(new_run_dir, ignore_errors=True)
        raise
    return {
        "ok": True,
        "verification_run_id": new_run_id,
        "inherited_from_verification_run_id": source_run_id,
        "inherited_from_data_version_hash": source_hash,
        "data_version_hash": candidate_hash,
        "runtime_corpus_sha256": corpus_digest,
        "pointer": pointer,
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="发布等价运行语料的继承质量证据")
    parser.add_argument("--active-db", type=Path, default=ACTIVE_DB_PATH)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--reports-dir", type=Path, default=QUALITY_REPORTS_DIR)
    parser.add_argument("--collection", default="design_specs")
    args = parser.parse_args()
    try:
        result = publish_equivalent_quality_evidence(
            active_db_path=args.active_db,
            manifest_path=args.manifest,
            reports_dir=args.reports_dir,
            collection_name=args.collection,
        )
    except (EquivalentEvidenceError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
