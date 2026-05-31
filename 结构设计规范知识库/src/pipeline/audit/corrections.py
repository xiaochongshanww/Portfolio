import json
import time
from pathlib import Path
from typing import Any

from src.pipeline.paths import CORRECTIONS_DIR


SUPPORTED_ACTIONS = {"replace_text", "set_field", "delete_element", "insert_after", "merge_next"}


def _doc_stems(source_file: str) -> list[str]:
    path = Path(source_file)
    stems = [path.stem, source_file]
    return list(dict.fromkeys(stems))


def load_approved_corrections(source_file: str, corrections_dir: Path = CORRECTIONS_DIR) -> list[dict[str, Any]]:
    approved_dir = corrections_dir / "approved"
    corrections: list[dict[str, Any]] = []
    for stem in _doc_stems(source_file):
        path = approved_dir / f"{stem}.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                corrections.extend(payload.get("corrections", []))
            elif isinstance(payload, list):
                corrections.extend(payload)
    return corrections


def apply_approved_corrections(
    elements: list[dict[str, Any]],
    source_file: str,
    corrections_dir: Path = CORRECTIONS_DIR,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    corrections = load_approved_corrections(source_file, corrections_dir)
    corrected = [dict(element) for element in elements]
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for correction in corrections:
        action = str(correction.get("action") or correction.get("suggested_patch", {}).get("action") or "")
        if action not in SUPPORTED_ACTIONS:
            skipped.append({"correction": correction, "reason": "unsupported_action"})
            continue

        target = correction.get("target", {})
        index = target.get("element_index", correction.get("element_index"))
        if not isinstance(index, int) or index < 0 or index >= len(corrected):
            skipped.append({"correction": correction, "reason": "invalid_element_index"})
            continue

        patch = correction.get("suggested_patch", correction)
        field = str(target.get("field") or patch.get("field") or "text")
        value = patch.get("value", correction.get("value", ""))

        if action == "replace_text":
            corrected[index]["text"] = str(value)
        elif action == "set_field":
            corrected[index][field] = value
        elif action == "delete_element":
            corrected[index]["_deleted"] = True
        elif action == "insert_after":
            new_element = dict(value) if isinstance(value, dict) else {"type": "Text", "text": str(value)}
            corrected.insert(index + 1, new_element)
        elif action == "merge_next":
            if index + 1 >= len(corrected):
                skipped.append({"correction": correction, "reason": "missing_next_element"})
                continue
            corrected[index]["text"] = f"{corrected[index].get('text', '')}\n{corrected[index + 1].get('text', '')}".strip()
            corrected[index + 1]["_deleted"] = True

        applied.append({"action": action, "target": target, "id": correction.get("id", "")})

    corrected = [element for element in corrected if not element.get("_deleted")]
    return corrected, {
        "source_file": source_file,
        "approved_count": len(corrections),
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "applied": applied,
        "skipped": skipped,
    }


def load_candidate_corrections(source_file: str, corrections_dir: Path = CORRECTIONS_DIR) -> list[dict[str, Any]]:
    candidates_dir = corrections_dir / "candidates"
    corrections: list[dict[str, Any]] = []
    for stem in _doc_stems(source_file):
        path = candidates_dir / f"{stem}.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                corrections.extend(payload.get("corrections", payload.get("candidates", [])))
            elif isinstance(payload, list):
                corrections.extend(payload)
    return corrections


def normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    patch = candidate.get("suggested_patch", candidate)
    action = str(patch.get("action") or candidate.get("action") or "")
    normalized = {
        "id": candidate.get("id", ""),
        "source_file": candidate.get("source_file", ""),
        "page": candidate.get("page", 0),
        "issue_type": candidate.get("issue_type", ""),
        "severity": candidate.get("severity", ""),
        "confidence": candidate.get("confidence", 0),
        "action": action,
        "target": candidate.get("target", {}),
        "value": patch.get("value", candidate.get("value", "")),
        "evidence": candidate.get("evidence", {}),
        "review_status": "approved",
    }
    if patch.get("field"):
        normalized["field"] = patch["field"]
    return normalized


def promote_approved_candidates(
    source_file: str,
    corrections_dir: Path = CORRECTIONS_DIR,
    *,
    include_pending: bool = False,
) -> dict[str, Any]:
    candidates = load_candidate_corrections(source_file, corrections_dir)
    promoted = []
    skipped = []
    for candidate in candidates:
        review_status = str(candidate.get("review_status", "pending"))
        patch = candidate.get("suggested_patch", candidate)
        action = str(patch.get("action") or candidate.get("action") or "")
        if review_status != "approved" and not include_pending:
            skipped.append({"id": candidate.get("id", ""), "reason": "not_approved", "review_status": review_status})
            continue
        if action not in SUPPORTED_ACTIONS:
            skipped.append({"id": candidate.get("id", ""), "reason": "unsupported_action", "action": action})
            continue
        promoted.append(normalize_candidate(candidate))

    approved_dir = corrections_dir / "approved"
    approved_dir.mkdir(parents=True, exist_ok=True)
    approved_path = approved_dir / f"{Path(source_file).stem}.json"
    existing = []
    if approved_path.exists():
        payload = json.loads(approved_path.read_text(encoding="utf-8"))
        existing = payload.get("corrections", payload if isinstance(payload, list) else [])
    by_id = {str(item.get("id", index)): item for index, item in enumerate(existing)}
    for item in promoted:
        key = str(item.get("id") or f"promoted-{len(by_id)}")
        by_id[key] = item

    payload = {
        "source_file": source_file,
        "updated_at": int(time.time()),
        "corrections": list(by_id.values()),
    }
    approved_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "source_file": source_file,
        "candidate_count": len(candidates),
        "promoted_count": len(promoted),
        "skipped_count": len(skipped),
        "approved_path": str(approved_path),
        "skipped": skipped,
    }


def list_candidate_files(corrections_dir: Path = CORRECTIONS_DIR) -> list[dict[str, Any]]:
    candidates_dir = corrections_dir / "candidates"
    if not candidates_dir.exists():
        return []
    files = []
    for path in sorted(candidates_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        corrections = payload.get("corrections", payload.get("candidates", [])) if isinstance(payload, dict) else payload
        files.append(
            {
                "doc": path.stem,
                "path": str(path),
                "source_file": payload.get("source_file", path.name) if isinstance(payload, dict) else path.name,
                "candidate_count": len(corrections),
                "pending_count": sum(1 for item in corrections if item.get("review_status", "pending") == "pending"),
                "approved_count": sum(1 for item in corrections if item.get("review_status") == "approved"),
                "rejected_count": sum(1 for item in corrections if item.get("review_status") == "rejected"),
            }
        )
    return files


def read_candidate_file(doc: str, corrections_dir: Path = CORRECTIONS_DIR) -> dict[str, Any]:
    path = corrections_dir / "candidates" / f"{Path(doc).stem}.json"
    if not path.exists():
        return {"doc": Path(doc).stem, "source_file": doc, "corrections": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return {"doc": path.stem, "source_file": doc, "corrections": payload}
    payload.setdefault("doc", path.stem)
    payload.setdefault("corrections", payload.get("candidates", []))
    return payload


def update_candidate_status(
    doc: str,
    candidate_id: str,
    status: str,
    corrections_dir: Path = CORRECTIONS_DIR,
) -> dict[str, Any]:
    if status not in {"pending", "approved", "rejected"}:
        raise ValueError("status must be pending, approved, or rejected")
    path = corrections_dir / "candidates" / f"{Path(doc).stem}.json"
    if not path.exists():
        raise FileNotFoundError(f"candidate file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    corrections = payload.get("corrections", payload.get("candidates", [])) if isinstance(payload, dict) else payload
    updated = False
    for index, item in enumerate(corrections):
        if str(item.get("id") or index) == candidate_id:
            item["review_status"] = status
            updated = True
            break
    if not updated:
        raise KeyError(f"candidate not found: {candidate_id}")
    if isinstance(payload, dict):
        payload["corrections"] = corrections
        payload.pop("candidates", None)
    else:
        payload = corrections
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"doc": Path(doc).stem, "candidate_id": candidate_id, "review_status": status}
