from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def inspect_collection(database: Path, collection_name: str) -> dict[str, object]:
    import chromadb

    client = chromadb.PersistentClient(path=str(database.resolve()))
    collection = client.get_collection(collection_name)
    count = collection.count()
    sample = collection.get(limit=1, include=["documents", "metadatas"])
    return {
        "ok": True,
        "count": count,
        "sample_ids": sample.get("ids", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="在隔离进程中打开 Chroma 集合")
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--collection", required=True)
    args = parser.parse_args()
    try:
        payload = inspect_collection(args.database, args.collection)
    except Exception as exc:
        print(
            json.dumps(
                {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                ensure_ascii=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
