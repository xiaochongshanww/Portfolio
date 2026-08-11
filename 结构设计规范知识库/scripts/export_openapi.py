import argparse
import json
import os
import sys
import tempfile
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUTPUT = ROOT / "frontend" / "openapi.json"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
PAGE_IMAGE_PATH = "/admin/page-image/{doc}/{page}"
RUNTIME_REQUIREMENTS = ROOT / "requirements-runtime.txt"
CONTRACT_GENERATOR_PACKAGES = ("fastapi", "pydantic", "pydantic-core")


class OpenApiContractError(RuntimeError):
    pass


def locked_generator_versions(path: Path = RUNTIME_REQUIREMENTS) -> dict[str, str]:
    versions: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise OpenApiContractError(f"cannot read runtime dependency lock: {path}") from exc
    for line in lines:
        requirement = line.strip()
        for package in CONTRACT_GENERATOR_PACKAGES:
            prefix = f"{package}=="
            if requirement.startswith(prefix):
                versions[package] = requirement[len(prefix) :].split()[0]
    missing = sorted(set(CONTRACT_GENERATOR_PACKAGES) - versions.keys())
    if missing:
        raise OpenApiContractError(
            "runtime dependency lock is missing OpenAPI generators: " + ", ".join(missing)
        )
    return versions


def validate_generator_environment() -> None:
    locked = locked_generator_versions()
    mismatches = []
    for package, expected in locked.items():
        try:
            actual = importlib_metadata.version(package)
        except importlib_metadata.PackageNotFoundError:
            actual = "not-installed"
        if actual != expected:
            mismatches.append(f"{package}={actual} (locked {expected})")
    if mismatches:
        raise OpenApiContractError(
            "OpenAPI generator dependency mismatch: "
            + ", ".join(mismatches)
            + "; install requirements-runtime.txt before exporting"
        )


def build_openapi_document() -> dict[str, Any]:
    validate_generator_environment()
    from src.app.main import app

    document = app.openapi()
    validate_admin_contract(document)
    return document


def count_admin_operations(document: dict[str, Any]) -> int:
    paths = document.get("paths", {})
    if not isinstance(paths, dict):
        return 0
    return sum(
        1
        for path, operations in paths.items()
        if path.startswith("/admin") and isinstance(operations, dict)
        for method, operation in operations.items()
        if method in HTTP_METHODS and isinstance(operation, dict)
    )


def validate_admin_contract(document: dict[str, Any]) -> None:
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise OpenApiContractError("OpenAPI paths must be an object")

    operation_ids: set[str] = set()
    admin_operation_count = 0
    for path, operations in sorted(paths.items()):
        if not path.startswith("/admin") or not isinstance(operations, dict):
            continue
        for method, operation in operations.items():
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            admin_operation_count += 1
            operation_id = str(operation.get("operationId") or "")
            if not operation_id:
                raise OpenApiContractError(f"missing operationId: {method.upper()} {path}")
            if operation_id in operation_ids:
                raise OpenApiContractError(f"duplicate operationId: {operation_id}")
            operation_ids.add(operation_id)

            response = operation.get("responses", {}).get("200", {})
            content = response.get("content", {}) if isinstance(response, dict) else {}
            if path == PAGE_IMAGE_PATH and method == "get":
                if set(content) != {"image/png"}:
                    raise OpenApiContractError(
                        f"page image response must be image/png: {method.upper()} {path}"
                    )
                continue
            schema = content.get("application/json", {}).get("schema")
            if not isinstance(schema, dict) or not schema:
                raise OpenApiContractError(
                    f"empty JSON success response schema: {method.upper()} {path}"
                )

    if admin_operation_count == 0:
        raise OpenApiContractError("no admin operations found")


def render_openapi(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def check_snapshot(path: Path, expected: str) -> None:
    try:
        actual = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise OpenApiContractError(f"OpenAPI snapshot missing: {path}") from exc
    if actual != expected:
        raise OpenApiContractError(
            f"OpenAPI snapshot drifted: run python scripts/export_openapi.py --write ({path})"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export or verify the deterministic OpenAPI snapshot"
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true", help="atomically update the snapshot")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    try:
        document = build_openapi_document()
        rendered = render_openapi(document)
        if args.write:
            atomic_write_text(output, rendered)
            mode = "written"
        else:
            check_snapshot(output, rendered)
            mode = "verified"
    except (OSError, OpenApiContractError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "mode": mode,
                "output": str(output),
                "admin_operation_count": count_admin_operations(document),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
