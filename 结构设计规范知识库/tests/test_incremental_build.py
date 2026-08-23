from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

from src.app.core.config import settings
from src.app.retrieval.dense_vector_store import build_dense_vector_store
from src.pipeline import builder, incremental, load_to_db
from src.pipeline.active_db import write_active_db
from src.pipeline.metadata import parse_spec_filename


def _write_processed(processed_dir: Path, source_file: str, chunk_id: str) -> None:
    stem = Path(source_file).stem
    processed_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_file": source_file,
        "parser_backend": "pymupdf",
        "parser_metadata": {},
        "artifacts": [],
        "audit": {"finding_count": 0, "high_risk_count": 0},
        "corrections": {"approved_count": 0, "applied_count": 0, "skipped_count": 0},
        "elements": [{"type": "Text", "text": "test", "page": 1}],
    }
    chunk = {
        "chunk_id": chunk_id,
        "source": source_file,
        "source_file": source_file,
        "code": "TEST",
        "name": "测试",
        "version": "",
        "effective_date": "",
        "status": "active",
        "title": "测试",
        "clause_number": "1.0.1",
        "chunk_type": "text",
        "section_type": "body",
        "authority_level": 90,
        "is_table": False,
        "table_id": "",
        "table_name": "",
        "pages": [1],
        "images": [],
        "metadata_status": "complete",
        "text": "test",
    }
    (processed_dir / f"{stem}.json").write_text(json.dumps(payload), encoding="utf-8")
    (processed_dir / f"{stem}_chunks.json").write_text(json.dumps([chunk]), encoding="utf-8")


def _active_version(
    tmp_path: Path,
    monkeypatch,
    *,
    source_pdf: Path,
    contract: dict,
    fingerprint: dict,
    artifacts: list[dict] | None = None,
) -> tuple[Path, Path]:
    data_dir = tmp_path / "data"
    version = data_dir / "db_versions" / "v1"
    processed = version / "processed"
    db_dir = version / "db"
    images = version / "images"
    images.mkdir(parents=True)
    _write_processed(processed, source_pdf.name, "chunk-old")
    build_dense_vector_store(
        db_dir,
        ["chunk-old"],
        [[1.0] + [0.0] * (settings.embedding_dimensions - 1)],
        embedding_model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    manifest_path = version / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "data_version_hash": "active-v1",
                "build_contract": contract,
                "documents": [
                    {
                        "source_file": source_pdf.name,
                        "build_fingerprint": fingerprint,
                        "artifacts": artifacts or [],
                    },
                    {
                        "source_file": "REMOVED.pdf",
                        "build_fingerprint": {},
                        "artifacts": [],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    pointer = data_dir / "active_db.json"
    write_active_db(
        {
            "active_db_dir": str(db_dir),
            "processed_dir": str(processed),
            "images_dir": str(images),
            "manifest": str(manifest_path),
        },
        pointer,
    )
    monkeypatch.setattr(incremental, "ACTIVE_DB_PATH", pointer)
    return processed, db_dir


def test_plan_classifies_added_reused_and_removed_documents(tmp_path: Path, monkeypatch) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    current = raw / "TEST 1000-2026_测试规范.pdf"
    added = raw / "TEST 1001-2026_新增规范.pdf"
    current.write_bytes(b"current")
    added.write_bytes(b"added")
    metadata = {path.name: parse_spec_filename(path.name) for path in (current, added)}
    environment = {"implementation": "pymupdf", "version": "", "compatibility": "not_applicable"}
    contract = incremental.build_contract(
        parser_backend="pymupdf", parser_environment=environment, apply_corrections=True
    )
    fingerprint = incremental.document_fingerprint(
        current, metadata[current.name], apply_corrections=True
    )
    _active_version(
        tmp_path,
        monkeypatch,
        source_pdf=current,
        contract=contract,
        fingerprint=fingerprint,
    )

    plan = incremental.plan_incremental_build(
        [current, added],
        metadata,
        parser_backend="pymupdf",
        parser_environment=environment,
        apply_corrections=True,
    ).to_dict()

    assert plan["fallback_to_full"] is False
    assert plan["counts"] == {"added": 1, "changed": 0, "reused": 1, "removed": 1}


def test_plan_reprocesses_document_when_cached_artifact_is_missing(
    tmp_path: Path, monkeypatch
) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    current = raw / "TEST 1000-2026_测试规范.pdf"
    current.write_bytes(b"current")
    spec = parse_spec_filename(current.name)
    environment = {"implementation": "pymupdf", "version": "", "compatibility": "not_applicable"}
    contract = incremental.build_contract(
        parser_backend="pymupdf", parser_environment=environment, apply_corrections=True
    )
    fingerprint = incremental.document_fingerprint(current, spec, apply_corrections=True)
    _active_version(
        tmp_path,
        monkeypatch,
        source_pdf=current,
        contract=contract,
        fingerprint=fingerprint,
        artifacts=[
            {
                "kind": "markdown",
                "path": str(tmp_path / "missing.md"),
                "status": "ok",
                "required": True,
                "sha256": "a" * 64,
            }
        ],
    )

    plan = incremental.plan_incremental_build(
        [current],
        {current.name: spec},
        parser_backend="pymupdf",
        parser_environment=environment,
        apply_corrections=True,
    ).to_dict()

    assert plan["fallback_to_full"] is False
    assert plan["counts"]["changed"] == 1
    assert "missing_artifact:markdown" in plan["documents"][0]["reasons"]


def test_legacy_manifest_without_contract_forces_full_fallback(tmp_path: Path, monkeypatch) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    current = raw / "TEST 1000-2026_测试规范.pdf"
    current.write_bytes(b"current")
    spec = parse_spec_filename(current.name)
    environment = {"implementation": "pymupdf", "version": "", "compatibility": "not_applicable"}
    fingerprint = incremental.document_fingerprint(current, spec, apply_corrections=True)
    _active_version(
        tmp_path,
        monkeypatch,
        source_pdf=current,
        contract={},
        fingerprint=fingerprint,
    )

    plan = incremental.plan_incremental_build(
        [current],
        {current.name: spec},
        parser_backend="pymupdf",
        parser_environment=environment,
        apply_corrections=True,
    ).to_dict()

    assert plan["fallback_to_full"] is True
    assert plan["fallback_reasons"] == ["build_contract_incompatible"]
    assert plan["counts"]["changed"] == 1


class _EmbeddingResponse:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.data = [SimpleNamespace(embedding=vector) for vector in vectors]


class _CountingEmbeddings:
    def __init__(self) -> None:
        self.inputs: list[list[str]] = []

    def create(self, *, input: list[str], **_kwargs) -> _EmbeddingResponse:
        self.inputs.append(input)
        return _EmbeddingResponse(
            [[0.0, 1.0] + [0.0] * (settings.embedding_dimensions - 2) for _ in input]
        )


def test_embedding_stage_reuses_valid_vectors_and_only_calls_provider_for_delta() -> None:
    embeddings = _CountingEmbeddings()
    client = SimpleNamespace(embeddings=embeddings)
    chunks = {
        "doc.pdf": [
            {**_minimal_chunk("reused"), "text": "reused text"},
            {**_minimal_chunk("new"), "text": "new text"},
            {**_minimal_chunk("invalid"), "text": "invalid cached text"},
        ]
    }
    cached = {
        "reused": [1.0] + [0.0] * (settings.embedding_dimensions - 1),
        "invalid": [0.0] * settings.embedding_dimensions,
    }

    batches, stats = load_to_db._embed_chunks_with_reuse(
        client, chunks, reusable_embeddings=cached
    )

    assert embeddings.inputs == [["new text", "invalid cached text"]]
    assert stats == {"reused_embedding_count": 1, "generated_embedding_count": 2}
    assert batches[0][0] == ["reused", "new", "invalid"]


def test_reused_document_copies_images_and_rewrites_verified_artifact_paths(
    tmp_path: Path, monkeypatch
) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    current = raw / "TEST 1000-2026_测试规范.pdf"
    current.write_bytes(b"current")
    spec = parse_spec_filename(current.name)
    environment = {"implementation": "pymupdf", "version": "", "compatibility": "not_applicable"}
    contract = incremental.build_contract(
        parser_backend="pymupdf", parser_environment=environment, apply_corrections=True
    )
    fingerprint = incremental.document_fingerprint(current, spec, apply_corrections=True)
    processed, _db = _active_version(
        tmp_path,
        monkeypatch,
        source_pdf=current,
        contract=contract,
        fingerprint=fingerprint,
    )
    artifact = tmp_path / "active-mineru" / "doc.md"
    artifact.parent.mkdir()
    artifact.write_text("verified", encoding="utf-8")
    element_path = processed / f"{current.stem}.json"
    payload = json.loads(element_path.read_text(encoding="utf-8"))
    payload["artifacts"] = [
        {
            "kind": "markdown",
            "path": str(artifact),
            "relative_path": "raw/doc.md",
            "sha256": incremental.file_sha256(artifact),
            "size_bytes": artifact.stat().st_size,
            "required": True,
            "status": "ok",
        }
    ]
    payload["parser_metadata"] = {"mineru_output_dir": str(artifact.parent)}
    element_path.write_text(json.dumps(payload), encoding="utf-8")
    active_images = incremental.active_images_dir(incremental.ACTIVE_DB_PATH)
    (active_images / f"{current.stem}_p0001.png").write_bytes(b"png")

    result = incremental.load_reused_document(
        current.name,
        target_processed_dir=tmp_path / "candidate" / "processed",
        target_images_dir=tmp_path / "candidate" / "images",
        target_mineru_dir=tmp_path / "candidate" / "mineru",
    )

    rewritten = Path(result["artifacts"][0]["path"])
    assert rewritten.is_file()
    assert rewritten.read_text(encoding="utf-8") == "verified"
    assert rewritten.is_relative_to(tmp_path / "candidate" / "mineru")
    assert (tmp_path / "candidate" / "images" / f"{current.stem}_p0001.png").is_file()


def _minimal_chunk(chunk_id: str) -> dict:
    return {
        "chunk_id": chunk_id,
        "source": "doc.pdf",
        "source_file": "doc.pdf",
        "code": "TEST",
        "name": "测试",
        "version": "",
        "effective_date": "",
        "status": "active",
        "title": "",
        "clause_number": "",
        "chunk_type": "text",
        "pages": [1],
        "images": [],
        "metadata_status": "complete",
    }


def test_incremental_rebuild_reuses_a_complete_active_version_end_to_end(
    tmp_path: Path, monkeypatch
) -> None:
    import fitz

    source = tmp_path / "raw"
    source.mkdir()
    pdf = source / "GB 99999-2026_增量测试规范.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "1.0.1 Incremental build contract test")
    document.save(pdf)
    document.close()

    calls: list[list[str]] = []

    class FakeClient:
        def __init__(self, *, api_key: str) -> None:
            assert api_key
            self.embeddings = self

        def create(self, *, input: list[str], **_kwargs) -> _EmbeddingResponse:
            calls.append(input)
            vectors = []
            for index, _text in enumerate(input):
                vector = [0.0] * settings.embedding_dimensions
                vector[index % settings.embedding_dimensions] = 1.0
                vectors.append(vector)
            return _EmbeddingResponse(vectors)

    zai = sys.modules.get("zai") or types.ModuleType("zai")
    monkeypatch.setitem(sys.modules, "zai", zai)
    monkeypatch.setattr(zai, "ZhipuAiClient", FakeClient, raising=False)
    monkeypatch.setenv("ZHIPUAI_API_KEY", "incremental-test")
    first = tmp_path / "data" / "db_versions" / "v1"
    first_manifest = builder.rebuild(
        source,
        parser_backend="pymupdf",
        apply_corrections=False,
        db_dir=first / "db",
        manifest_path=first / "manifest.json",
        processed_dir=first / "processed",
        images_dir=first / "images",
        mineru_output_dir=first / "mineru",
        audit_dir=first / "audit",
    )
    assert first_manifest["chunk_count"] > 0
    assert calls

    pointer = tmp_path / "data" / "active_db.json"
    write_active_db(
        {
            "active_db_dir": str(first / "db"),
            "processed_dir": str(first / "processed"),
            "images_dir": str(first / "images"),
            "mineru_dir": str(first / "mineru"),
            "audit_dir": str(first / "audit"),
            "manifest": str(first / "manifest.json"),
        },
        pointer,
    )
    monkeypatch.setattr(incremental, "ACTIVE_DB_PATH", pointer)
    calls.clear()
    second = tmp_path / "data" / "db_versions" / "v2"
    second_manifest = builder.incremental_rebuild(
        source,
        parser_backend="pymupdf",
        apply_corrections=False,
        db_dir=second / "db",
        manifest_path=second / "manifest.json",
        processed_dir=second / "processed",
        images_dir=second / "images",
        mineru_output_dir=second / "mineru",
        audit_dir=second / "audit",
    )

    assert second_manifest["build_params"]["mode"] == "incremental"
    assert second_manifest["incremental_plan"]["counts"]["reused"] == 1
    assert second_manifest["build_params"]["generated_embedding_count"] == 0
    assert second_manifest["build_params"]["reused_embedding_count"] == first_manifest["chunk_count"]
    assert calls == []
