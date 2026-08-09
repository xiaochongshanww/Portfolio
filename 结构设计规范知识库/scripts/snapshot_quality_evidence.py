from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = Path("docs/quality/质量证据状态.json")
DEFAULT_SYSTEM_CARD = Path("docs/quality/检索增强生成系统卡.md")
DEFAULT_HISTORY_DIR = Path("docs/quality/质量证据历史")
DEFAULT_HISTORY_INDEX = Path("docs/quality/质量证据历史索引.json")
REPORT_PATHS = {
    "verification": Path("data/audit/reports/verification_latest.json"),
    "quality_gate": Path("data/audit/reports/quality_gate_latest.json"),
}
EVALUATION_PATHS = {
    "regular": Path("data/evaluation/queries.jsonl"),
    "structured": Path("data/evaluation/complex_structured_tables.jsonl"),
    "answer": Path("data/evaluation/answer_holdout.jsonl"),
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class EvidenceSnapshotError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_utf8_lf(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EvidenceSnapshotError(f"无法读取文本以计算哈希：{path}") from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceSnapshotError(f"无法读取 JSON：{path}") from exc
    if not isinstance(payload, dict):
        raise EvidenceSnapshotError(f"JSON 顶层必须是对象：{path}")
    return payload


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _snapshot_fingerprint(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(snapshot)).hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise EvidenceSnapshotError(f"无法原子写入 JSON：{path}") from exc
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _case_count(path: Path) -> int:
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError as exc:
        raise EvidenceSnapshotError(f"无法读取评估集：{path}") from exc


def _report_summary(
    relative_path: Path,
    absolute_path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    generated_at = payload.get("generated_at")
    passed = payload.get("passed")
    if not isinstance(generated_at, str) or not generated_at:
        raise EvidenceSnapshotError(f"报告缺少 generated_at：{relative_path}")
    if not isinstance(passed, bool):
        raise EvidenceSnapshotError(f"报告缺少布尔 passed：{relative_path}")
    return {
        "path": relative_path.as_posix(),
        "sha256": _sha256(absolute_path),
        "hash_mode": "raw_bytes",
        "generated_at": generated_at,
        "passed": passed,
    }


def build_snapshot(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    reports: dict[str, dict[str, Any]] = {}
    raw_reports: dict[str, dict[str, Any]] = {}
    for name, relative_path in REPORT_PATHS.items():
        absolute_path = project_root / relative_path
        payload = _read_json(absolute_path)
        raw_reports[name] = payload
        reports[name] = _report_summary(relative_path, absolute_path, payload)

    quality_gate = raw_reports["quality_gate"]
    failed_checks = quality_gate.get("failed_checks")
    if not isinstance(failed_checks, list) or not all(
        isinstance(item, str) and item for item in failed_checks
    ):
        raise EvidenceSnapshotError("质量门禁报告的 failed_checks 无效")

    evaluation_sets: dict[str, dict[str, Any]] = {}
    for name, relative_path in EVALUATION_PATHS.items():
        absolute_path = project_root / relative_path
        evaluation_sets[name] = {
            "path": relative_path.as_posix(),
            "sha256": _sha256_utf8_lf(absolute_path),
            "hash_mode": "utf8_lf",
            "case_count": _case_count(absolute_path),
        }

    release_quality_passed = all(report["passed"] for report in reports.values())
    return {
        "schema_version": 1,
        "release_quality_status": ("passed" if release_quality_passed else "not_passed"),
        "reports": reports,
        "quality_gate_failed_checks": failed_checks,
        "evaluation_sets": evaluation_sets,
    }


def _require_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise EvidenceSnapshotError(f"快照字段必须是对象：{key}")
    return value


def _validate_report_entry(name: str, report: dict[str, Any]) -> None:
    if report.get("path") != REPORT_PATHS[name].as_posix():
        raise EvidenceSnapshotError(f"报告路径不符合契约：{name}")
    if not isinstance(report.get("generated_at"), str):
        raise EvidenceSnapshotError(f"报告时间无效：{name}")
    if not isinstance(report.get("passed"), bool):
        raise EvidenceSnapshotError(f"报告状态无效：{name}")
    if not isinstance(report.get("sha256"), str) or not SHA256_RE.fullmatch(report["sha256"]):
        raise EvidenceSnapshotError(f"报告哈希无效：{name}")
    if report.get("hash_mode") != "raw_bytes":
        raise EvidenceSnapshotError(f"报告哈希模式无效：{name}")


def _validate_snapshot_structure(snapshot: dict[str, Any]) -> str:
    if snapshot.get("schema_version") != 1:
        raise EvidenceSnapshotError("不支持的质量证据快照版本")

    reports = _require_mapping(snapshot, "reports")
    if set(reports) != set(REPORT_PATHS):
        raise EvidenceSnapshotError("质量报告集合与契约不一致")
    for name, report in reports.items():
        if not isinstance(report, dict):
            raise EvidenceSnapshotError(f"报告摘要必须是对象：{name}")
        _validate_report_entry(name, report)

    expected_status = (
        "passed" if all(report["passed"] for report in reports.values()) else "not_passed"
    )
    if snapshot.get("release_quality_status") != expected_status:
        raise EvidenceSnapshotError("发布质量状态与报告摘要不一致")

    failed_checks = snapshot.get("quality_gate_failed_checks")
    if not isinstance(failed_checks, list) or not all(
        isinstance(item, str) and item for item in failed_checks
    ):
        raise EvidenceSnapshotError("质量门禁失败项无效")

    evaluation_sets = _require_mapping(snapshot, "evaluation_sets")
    if set(evaluation_sets) != set(EVALUATION_PATHS):
        raise EvidenceSnapshotError("评估集集合与契约不一致")
    for name, relative_path in EVALUATION_PATHS.items():
        entry = evaluation_sets[name]
        if not isinstance(entry, dict):
            raise EvidenceSnapshotError(f"评估集摘要必须是对象：{name}")
        if entry.get("path") != relative_path.as_posix():
            raise EvidenceSnapshotError(f"评估集路径不符合契约：{name}")
        if entry.get("hash_mode") != "utf8_lf":
            raise EvidenceSnapshotError(f"评估集哈希模式无效：{name}")
        if not isinstance(entry.get("sha256"), str) or not SHA256_RE.fullmatch(entry["sha256"]):
            raise EvidenceSnapshotError(f"评估集哈希无效：{name}")
        if not isinstance(entry.get("case_count"), int) or entry["case_count"] < 0:
            raise EvidenceSnapshotError(f"评估集数量无效：{name}")

    return expected_status


def _system_card_markers(snapshot: dict[str, Any]) -> list[str]:
    reports = _require_mapping(snapshot, "reports")
    evaluation_sets = _require_mapping(snapshot, "evaluation_sets")
    failed_checks = snapshot.get("quality_gate_failed_checks")
    if not isinstance(failed_checks, list):
        raise EvidenceSnapshotError("快照 failed_checks 无效")

    markers: list[str] = []
    for name in ("verification", "quality_gate"):
        report = reports[name]
        markers.extend(
            [
                f"`{name}.generated_at={report['generated_at']}`",
                f"`{name}.passed={str(report['passed']).lower()}`",
            ]
        )
    markers.append(f"`quality_gate.failed_checks={','.join(failed_checks)}`")
    for name in ("regular", "structured", "answer"):
        markers.append(f"`evaluation_set.{name}.case_count={evaluation_sets[name]['case_count']}`")
    return markers


def validate_snapshot(
    project_root: Path = PROJECT_ROOT,
    snapshot_path: Path = DEFAULT_SNAPSHOT,
    system_card_path: Path = DEFAULT_SYSTEM_CARD,
) -> dict[str, Any]:
    snapshot = _read_json(project_root / snapshot_path)
    expected_status = _validate_snapshot_structure(snapshot)
    reports = _require_mapping(snapshot, "reports")
    failed_checks = snapshot.get("quality_gate_failed_checks")
    evaluation_sets = _require_mapping(snapshot, "evaluation_sets")
    for name, relative_path in EVALUATION_PATHS.items():
        entry = evaluation_sets[name]
        if not isinstance(entry, dict):
            raise EvidenceSnapshotError(f"评估集摘要必须是对象：{name}")
        absolute_path = project_root / relative_path
        expected = {
            "path": relative_path.as_posix(),
            "sha256": _sha256_utf8_lf(absolute_path),
            "hash_mode": "utf8_lf",
            "case_count": _case_count(absolute_path),
        }
        if entry != expected:
            raise EvidenceSnapshotError(f"评估集摘要已漂移：{name}")

    verified_source_reports = 0
    for name, relative_path in REPORT_PATHS.items():
        absolute_path = project_root / relative_path
        if not absolute_path.is_file():
            continue
        payload = _read_json(absolute_path)
        expected = _report_summary(relative_path, absolute_path, payload)
        if reports[name] != expected:
            raise EvidenceSnapshotError(f"本地质量报告与快照不一致：{name}")
        if name == "quality_gate" and payload.get("failed_checks") != failed_checks:
            raise EvidenceSnapshotError("本地质量门禁失败项与快照不一致")
        verified_source_reports += 1

    try:
        system_card = (project_root / system_card_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise EvidenceSnapshotError("无法读取 RAG 系统卡") from exc
    missing_markers = [
        marker for marker in _system_card_markers(snapshot) if marker not in system_card
    ]
    if missing_markers:
        raise EvidenceSnapshotError("RAG 系统卡缺少质量证据机器标记")
    if expected_status != "passed" and "当前没有可用于发布的完整通过证据" not in system_card:
        raise EvidenceSnapshotError("系统卡未声明当前不可作为发布通过证据")

    return {
        "ok": True,
        "snapshot": snapshot_path.as_posix(),
        "release_quality_status": expected_status,
        "evaluation_set_count": len(evaluation_sets),
        "verified_source_report_count": verified_source_reports,
    }


def _archive_name(snapshot: dict[str, Any]) -> str:
    reports = _require_mapping(snapshot, "reports")
    generated_at = reports["verification"]["generated_at"]
    try:
        parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceSnapshotError("验证报告时间不是 ISO 8601") from exc
    if parsed.tzinfo is None:
        raise EvidenceSnapshotError("验证报告时间必须包含时区")
    stamp = parsed.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{_snapshot_fingerprint(snapshot)[:12]}.json"


def _history_entry(snapshot: dict[str, Any], archive_path: Path) -> dict[str, Any]:
    reports = _require_mapping(snapshot, "reports")
    evaluation_sets = _require_mapping(snapshot, "evaluation_sets")
    return {
        "archive_path": archive_path.as_posix(),
        "snapshot_sha256": _snapshot_fingerprint(snapshot),
        "release_quality_status": snapshot["release_quality_status"],
        "verification_generated_at": reports["verification"]["generated_at"],
        "quality_gate_generated_at": reports["quality_gate"]["generated_at"],
        "failed_checks": snapshot["quality_gate_failed_checks"],
        "evaluation_case_counts": {
            name: evaluation_sets[name]["case_count"]
            for name in ("regular", "structured", "answer")
        },
    }


def build_history_index(
    project_root: Path = PROJECT_ROOT,
    history_dir: Path = DEFAULT_HISTORY_DIR,
) -> dict[str, Any]:
    directory = project_root / history_dir
    if not directory.is_dir():
        raise EvidenceSnapshotError("质量证据历史目录不存在")

    entries: list[dict[str, Any]] = []
    fingerprints: set[str] = set()
    for archive in sorted(directory.glob("*.json"), reverse=True):
        snapshot = _read_json(archive)
        _validate_snapshot_structure(snapshot)
        fingerprint = _snapshot_fingerprint(snapshot)
        if archive.name != _archive_name(snapshot):
            raise EvidenceSnapshotError(f"历史归档文件名与内容指纹不一致：{archive.name}")
        if fingerprint in fingerprints:
            raise EvidenceSnapshotError("质量证据历史包含重复内容")
        fingerprints.add(fingerprint)
        entries.append(_history_entry(snapshot, history_dir / archive.name))

    if not entries:
        raise EvidenceSnapshotError("质量证据历史不能为空")
    return {"schema_version": 1, "entries": entries}


def validate_history(
    project_root: Path = PROJECT_ROOT,
    snapshot_path: Path = DEFAULT_SNAPSHOT,
    history_dir: Path = DEFAULT_HISTORY_DIR,
    history_index_path: Path = DEFAULT_HISTORY_INDEX,
) -> dict[str, Any]:
    current_snapshot = _read_json(project_root / snapshot_path)
    _validate_snapshot_structure(current_snapshot)
    expected_index = build_history_index(project_root, history_dir)
    actual_index = _read_json(project_root / history_index_path)
    if actual_index != expected_index:
        raise EvidenceSnapshotError("质量证据历史索引与归档不一致")

    current_fingerprint = _snapshot_fingerprint(current_snapshot)
    fingerprints = {entry["snapshot_sha256"] for entry in expected_index["entries"]}
    if current_fingerprint not in fingerprints:
        raise EvidenceSnapshotError("当前质量证据快照尚未归档")
    return {
        "history_entry_count": len(expected_index["entries"]),
        "current_snapshot_archived": True,
        "current_snapshot_sha256": current_fingerprint,
    }


def write_snapshot(
    project_root: Path = PROJECT_ROOT,
    snapshot_path: Path = DEFAULT_SNAPSHOT,
    history_dir: Path = DEFAULT_HISTORY_DIR,
    history_index_path: Path = DEFAULT_HISTORY_INDEX,
) -> Path:
    target = project_root / snapshot_path
    snapshot = build_snapshot(project_root)
    archive_relative = history_dir / _archive_name(snapshot)
    archive = project_root / archive_relative
    if archive.exists():
        if _read_json(archive) != snapshot:
            raise EvidenceSnapshotError("质量证据历史归档发生文件名冲突")
    else:
        _write_json_atomic(archive, snapshot)
    index = build_history_index(project_root, history_dir)
    _write_json_atomic(project_root / history_index_path, index)
    # Publish latest only after the immutable archive and its index are durable.
    _write_json_atomic(target, snapshot)
    return target


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成或验证脱敏质量证据快照")
    parser.add_argument("--write", action="store_true", help="从本地报告重建快照")
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT,
        help="相对于项目根的快照路径",
    )
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=DEFAULT_HISTORY_DIR,
        help="相对于项目根的历史归档目录",
    )
    parser.add_argument(
        "--history-index",
        type=Path,
        default=DEFAULT_HISTORY_INDEX,
        help="相对于项目根的历史索引路径",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.write:
            write_snapshot(
                PROJECT_ROOT,
                args.snapshot,
                args.history_dir,
                args.history_index,
            )
        result = validate_snapshot(PROJECT_ROOT, args.snapshot)
        result.update(
            validate_history(
                PROJECT_ROOT,
                args.snapshot,
                args.history_dir,
                args.history_index,
            )
        )
    except EvidenceSnapshotError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True))
        return 1
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
