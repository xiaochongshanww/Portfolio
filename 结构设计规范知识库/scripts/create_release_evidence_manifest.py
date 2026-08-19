from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTER_PATH = PROJECT_ROOT / "docs" / "governance" / "来源登记台账.json"


def _load_register(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"来源登记台账无法读取：{path}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("documents"), list):
        raise ValueError("来源登记台账 documents 必须是数组")
    return value


def build_manifest(register_path: Path = DEFAULT_REGISTER_PATH) -> dict[str, Any]:
    register = _load_register(register_path.resolve())
    production = [
        item
        for item in register["documents"]
        if isinstance(item, dict) and item.get("release_scope") == "production"
    ]
    production.sort(key=lambda item: str(item.get("source_id") or ""))
    return {
        "schema_version": 1,
        "status": "draft",
        "updated_at": date.today().isoformat(),
        "source_register_version": f"source-register-{register.get('updated_at', 'unknown')}",
        "sources": [
            {
                "source_id": item.get("source_id"),
                "source_file": item.get("source_file"),
                "evidence": {
                    "acquisition": {"status": "pending", "reference": None},
                    "rights_review": {"status": "pending", "reference": None},
                    "storage_disposition": {"status": "pending", "reference": None},
                },
                "reviewed_by": None,
                "reviewed_at": None,
            }
            for item in production
        ],
        "trial": {
            "status": "pending",
            "record": None,
        },
        "decisions": {
            "D-001": {"status": "pending", "reference": None},
            "D-002": {"status": "pending", "reference": None},
        },
        "rerank": {
            "status": "disabled",
            "comparison_report": None,
            "answer_report": None,
        },
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="生成受控发布证据包索引草稿")
    parser.add_argument(
        "--output", type=Path, required=True, help="受限目录中的 manifest JSON 路径"
    )
    parser.add_argument("--source-register", type=Path, default=DEFAULT_REGISTER_PATH)
    args = parser.parse_args()
    try:
        manifest = build_manifest(args.source_register)
        args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.output.resolve().write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "status": manifest["status"],
                "source_count": len(manifest["sources"]),
                "output": str(args.output.resolve()),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
