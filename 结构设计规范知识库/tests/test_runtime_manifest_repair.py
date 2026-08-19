from pathlib import Path

import pytest
from scripts.repair_runtime_manifest import (
    RuntimeManifestRepairError,
    build_repaired_manifest,
)


def _manifest() -> dict:
    return {
        "documents": [
            {"source_file": "production.pdf", "status": "active", "chunk_count": 3},
            {"source_file": "fixture.pdf", "status": "test", "chunk_count": 1},
        ],
        "document_count": 2,
        "chunk_count": 4,
        "embedding_model": "embedding-2",
        "collection_name": "design_specs",
        "build_params": {"mode": "rebuild", "loaded_chunks": 4},
    }


def test_build_repaired_manifest_removes_test_sources_and_recomputes_contract():
    repaired, excluded = build_repaired_manifest(_manifest(), candidate_db_dir=Path("candidate/db"))

    assert excluded == ["fixture.pdf"]
    assert repaired["document_count"] == 1
    assert repaired["chunk_count"] == 3
    assert repaired["build_params"]["mode"] == "runtime-manifest-repair"
    assert repaired["build_params"]["loaded_chunks"] == 3
    assert len(repaired["data_version_hash"]) == 64


def test_build_repaired_manifest_requires_test_source():
    manifest = _manifest()
    manifest["documents"] = manifest["documents"][:1]

    with pytest.raises(RuntimeManifestRepairError, match="不包含可移除的 test 来源"):
        build_repaired_manifest(manifest, candidate_db_dir=Path("candidate/db"))
