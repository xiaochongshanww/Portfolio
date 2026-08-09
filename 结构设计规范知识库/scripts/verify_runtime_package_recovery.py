from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from scripts.create_portability_package import create_portability_package
from scripts.verify_runtime_package_cold_start import verify_imported_runtime_api
from src.pipeline.knowledge_package import import_runtime_package, validate_runtime_package

PACKAGE_A_VARIANT = "recovery-a"
PACKAGE_B_VARIANT = "recovery-b"
TABLE_RELATIVE_PATH = Path("structured_tables") / "表5.1.1-活荷载.json"
IMAGE_RELATIVE_PATH = Path("images") / "第1页-示意图.png"


class RuntimePackageRecoveryError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimePackageRecoveryError(f"无法读取恢复断言文件 {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimePackageRecoveryError(f"恢复断言文件不是 JSON 对象: {path}")
    return payload


def _assert_stage(
    label: str,
    *,
    data_dir: Path,
    validation: dict[str, Any],
    imported: dict[str, Any],
    variant: str,
    startup_timeout: float,
) -> dict[str, Any]:
    expected_db_dir = Path(str(imported["active_db_dir"])).resolve()
    runtime = verify_imported_runtime_api(
        data_dir,
        validation,
        expected_db_dir=expected_db_dir,
        startup_timeout=startup_timeout,
    )
    active = _read_json(data_dir / "active_db.json")
    root_manifest = _read_json(data_dir / "manifest.json")
    structured_table = _read_json(data_dir / TABLE_RELATIVE_PATH)
    image_bytes = (data_dir / IMAGE_RELATIVE_PATH).read_bytes()
    version_root = data_dir / "db_versions" / f"import-{validation['package_id']}"
    checks = {
        **runtime["checks"],
        "pointer_package_id": active.get("package_id") == validation.get("package_id"),
        "pointer_data_version_hash": active.get("data_version_hash")
        == validation.get("data_version_hash"),
        "root_manifest_data_version_hash": root_manifest.get("data_version_hash")
        == validation.get("data_version_hash"),
        "structured_table_variant": structured_table.get("package_variant") == variant,
        "image_variant": image_bytes == f"portability-image:{variant}".encode(),
        "source_policy_present": (data_dir / "metadata" / "specs.json").is_file(),
        "version_root_present": version_root.is_dir(),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimePackageRecoveryError(f"{label} 断言失败: {', '.join(failed)}")
    return {
        "label": label,
        "package_id": validation["package_id"],
        "data_version_hash": validation["data_version_hash"],
        "variant": variant,
        "active_db_dir": str(expected_db_dir),
        "checks": checks,
    }


def verify_runtime_package_recovery(*, startup_timeout: float = 60) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="knowledge-package-recovery-") as temporary_name:
        work_root = Path(temporary_name)
        package_a = work_root / "runtime-a.zip"
        package_b = work_root / "runtime-b.zip"
        data_dir = work_root / "runtime-data"

        create_portability_package(package_a, variant=PACKAGE_A_VARIANT)
        create_portability_package(package_b, variant=PACKAGE_B_VARIANT)
        validation_a = validate_runtime_package(package_a)
        validation_b = validate_runtime_package(package_b)
        identity_checks = {
            "package_ids_differ": validation_a["package_id"] != validation_b["package_id"],
            "data_versions_differ": validation_a["data_version_hash"]
            != validation_b["data_version_hash"],
            "package_archives_differ": _sha256(package_a) != _sha256(package_b),
        }
        failed_identity = [name for name, passed in identity_checks.items() if not passed]
        if failed_identity:
            raise RuntimePackageRecoveryError("双版本样包身份未分离: " + ", ".join(failed_identity))

        imported_a = import_runtime_package(package_a, data_dir=data_dir)
        initial = _assert_stage(
            "initial-a",
            data_dir=data_dir,
            validation=validation_a,
            imported=imported_a,
            variant=PACKAGE_A_VARIANT,
            startup_timeout=startup_timeout,
        )

        imported_b = import_runtime_package(package_b, data_dir=data_dir, replace=True)
        upgraded = _assert_stage(
            "upgrade-b",
            data_dir=data_dir,
            validation=validation_b,
            imported=imported_b,
            variant=PACKAGE_B_VARIANT,
            startup_timeout=startup_timeout,
        )

        rolled_back_a = import_runtime_package(package_a, data_dir=data_dir, replace=True)
        rolled_back = _assert_stage(
            "rollback-a",
            data_dir=data_dir,
            validation=validation_a,
            imported=rolled_back_a,
            variant=PACKAGE_A_VARIANT,
            startup_timeout=startup_timeout,
        )

        version_a = data_dir / "db_versions" / f"import-{validation_a['package_id']}"
        version_b = data_dir / "db_versions" / f"import-{validation_b['package_id']}"
        retained_version_checks = {
            "version_a_retained": version_a.is_dir(),
            "version_b_retained": version_b.is_dir(),
            "version_a_manifest": _read_json(version_a / "manifest.json").get("data_version_hash")
            == validation_a["data_version_hash"],
            "version_b_manifest": _read_json(version_b / "manifest.json").get("data_version_hash")
            == validation_b["data_version_hash"],
        }
        failed_retention = [name for name, passed in retained_version_checks.items() if not passed]
        if failed_retention:
            raise RuntimePackageRecoveryError(
                "回退后版本保留断言失败: " + ", ".join(failed_retention)
            )

        result = {
            "ok": True,
            "workflow": "package-a-to-b-to-a",
            "identity_checks": identity_checks,
            "stages": [initial, upgraded, rolled_back],
            "retained_version_checks": retained_version_checks,
            "package_sha256": {
                "a": _sha256(package_a),
                "b": _sha256(package_b),
            },
            "external_model_calls": 0,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="验证运行知识包 A→B→A 升级与回退")
    parser.add_argument("--startup-timeout", type=float, default=60, help="单次 API 启动超时秒数")
    args = parser.parse_args()
    try:
        result = verify_runtime_package_recovery(startup_timeout=args.startup_timeout)
    except Exception as exc:
        print(
            json.dumps(
                {"ok": False, "error": type(exc).__name__, "message": str(exc)},
                ensure_ascii=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
