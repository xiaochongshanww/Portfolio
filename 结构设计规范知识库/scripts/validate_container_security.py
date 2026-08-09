from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

SEMVER_RE = re.compile(r"^v\d+\.\d+\.\d+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
DURATION_RE = re.compile(r"^[1-9]\d*[smh]$")
TRIVY_REPOSITORY = "aquasecurity/trivy"
TRIVY_RELEASE_API = f"https://api.github.com/repos/{TRIVY_REPOSITORY}/releases/latest"


@dataclass(frozen=True)
class ValidationError:
    source: str
    location: str
    code: str
    message: str


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repository_root() -> Path:
    return project_root().parent


def _error(source: str, location: str, code: str, message: str) -> ValidationError:
    return ValidationError(source=source, location=location, code=code, message=message)


def load_json_object(path: Path) -> tuple[dict[str, Any] | None, ValidationError | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return None, _error(
            str(path), "file", "FILE_UNAVAILABLE", "Required security policy file is unavailable."
        )
    except json.JSONDecodeError:
        return None, _error(
            str(path), "file", "JSON_INVALID", "Security policy file must use strict JSON syntax."
        )
    if not isinstance(value, dict):
        return None, _error(
            str(path), "root", "JSON_ROOT_INVALID", "Security policy root must be an object."
        )
    return value, None


def validate_lock(
    lock: dict[str, Any], *, source: str
) -> tuple[dict[str, Any] | None, list[ValidationError]]:
    errors: list[ValidationError] = []
    if lock.get("schema_version") != 1:
        errors.append(
            _error(source, "schema_version", "LOCK_SCHEMA_INVALID", "Schema version must be 1.")
        )

    scanner = lock.get("scanner")
    policy = lock.get("policy")
    if not isinstance(scanner, dict):
        errors.append(
            _error(source, "scanner", "SCANNER_MISSING", "Scanner lock must be an object.")
        )
        scanner = {}
    if not isinstance(policy, dict):
        errors.append(_error(source, "policy", "POLICY_MISSING", "Policy must be an object."))
        policy = {}

    if scanner.get("name") != "trivy":
        errors.append(
            _error(source, "scanner.name", "SCANNER_NAME_INVALID", "Scanner name must be trivy.")
        )
    if scanner.get("repository") != TRIVY_REPOSITORY:
        errors.append(
            _error(
                source,
                "scanner.repository",
                "SCANNER_REPOSITORY_INVALID",
                "Scanner repository must use the reviewed official Trivy repository.",
            )
        )
    version = scanner.get("version")
    if not isinstance(version, str) or SEMVER_RE.fullmatch(version) is None:
        errors.append(
            _error(
                source,
                "scanner.version",
                "SCANNER_VERSION_INVALID",
                "Scanner version must be a complete vMAJOR.MINOR.PATCH value.",
            )
        )
    release_url = scanner.get("release_url")
    if not isinstance(release_url, str) or not release_url.startswith("https://github.com/"):
        errors.append(
            _error(
                source,
                "scanner.release_url",
                "RELEASE_URL_INVALID",
                "Scanner release URL must use the official GitHub HTTPS location.",
            )
        )
    elif isinstance(version, str) and not release_url.endswith(f"/tag/{version}"):
        errors.append(
            _error(
                source,
                "scanner.release_url",
                "RELEASE_VERSION_MISMATCH",
                "Scanner release URL must match the locked scanner version.",
            )
        )
    if scanner.get("release_immutable") is not True:
        errors.append(
            _error(
                source,
                "scanner.release_immutable",
                "RELEASE_NOT_REVIEWED_IMMUTABLE",
                "The reviewed upstream release must be recorded as immutable.",
            )
        )
    archive_digest = scanner.get("linux_amd64_archive_sha256")
    if not isinstance(archive_digest, str) or SHA256_RE.fullmatch(archive_digest) is None:
        errors.append(
            _error(
                source,
                "scanner.linux_amd64_archive_sha256",
                "RELEASE_DIGEST_INVALID",
                "The reviewed Linux amd64 release asset must have a lowercase SHA-256 digest.",
            )
        )
    asset_name = scanner.get("linux_amd64_asset_name")
    if (
        not isinstance(asset_name, str)
        or asset_name != f"trivy_{str(version).removeprefix('v')}_Linux-64bit.tar.gz"
    ):
        errors.append(
            _error(
                source,
                "scanner.linux_amd64_asset_name",
                "RELEASE_ASSET_NAME_INVALID",
                "The reviewed Linux amd64 asset name must match the locked scanner version.",
            )
        )
    advisory = scanner.get("incident_advisory")
    if not isinstance(advisory, str) or not advisory.startswith(
        "https://github.com/aquasecurity/trivy/security/advisories/"
    ):
        errors.append(
            _error(
                source,
                "scanner.incident_advisory",
                "INCIDENT_ADVISORY_INVALID",
                "The official scanner supply-chain advisory must remain recorded.",
            )
        )

    setup_action = scanner.get("setup_action")
    if not isinstance(setup_action, dict):
        errors.append(
            _error(
                source,
                "scanner.setup_action",
                "SETUP_ACTION_MISSING",
                "Scanner setup action lock must be an object.",
            )
        )
        setup_action = {}
    if setup_action.get("source") != "aquasecurity/setup-trivy":
        errors.append(
            _error(
                source,
                "scanner.setup_action.source",
                "SETUP_ACTION_SOURCE_INVALID",
                "Scanner setup action must use the reviewed Aqua Security source.",
            )
        )
    action_ref = setup_action.get("ref")
    if not isinstance(action_ref, str) or COMMIT_RE.fullmatch(action_ref) is None:
        errors.append(
            _error(
                source,
                "scanner.setup_action.ref",
                "SETUP_ACTION_REF_INVALID",
                "Scanner setup action must be pinned to a full lowercase commit SHA.",
            )
        )
    action_version = setup_action.get("version")
    if not isinstance(action_version, str) or SEMVER_RE.fullmatch(action_version) is None:
        errors.append(
            _error(
                source,
                "scanner.setup_action.version",
                "SETUP_ACTION_VERSION_INVALID",
                "Scanner setup action must retain a readable semantic version.",
            )
        )

    expected_policy = {
        "image": "structural-spec-kb:ci",
        "severities": ["HIGH", "CRITICAL"],
        "package_types": ["os", "library"],
        "ignore_unfixed": True,
    }
    for field, expected in expected_policy.items():
        if policy.get(field) != expected:
            errors.append(
                _error(
                    source,
                    f"policy.{field}",
                    "POLICY_VALUE_INVALID",
                    f"Container security policy field {field!r} does not match the approved baseline.",
                )
            )
    timeout = policy.get("timeout")
    if not isinstance(timeout, str) or DURATION_RE.fullmatch(timeout) is None:
        errors.append(
            _error(
                source,
                "policy.timeout",
                "POLICY_TIMEOUT_INVALID",
                "Scanner timeout must be a positive duration ending in s, m, or h.",
            )
        )
    for field in ("artifact_retention_days", "maximum_exception_days"):
        value = policy.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > 90:
            errors.append(
                _error(
                    source,
                    f"policy.{field}",
                    "POLICY_DURATION_INVALID",
                    f"Policy field {field!r} must be an integer from 1 through 90.",
                )
            )

    normalized = {"scanner": scanner, "policy": policy}
    return (normalized if not errors else None), errors


def validate_remote_release(
    release: dict[str, Any], *, source: str, lock: dict[str, Any]
) -> list[ValidationError]:
    scanner = lock["scanner"]
    errors: list[ValidationError] = []
    if release.get("tag_name") != scanner["version"]:
        errors.append(
            _error(
                source,
                "tag_name",
                "SCANNER_RELEASE_DRIFT",
                "The latest upstream scanner release differs from the reviewed lock.",
            )
        )
    if release.get("immutable") is not True:
        errors.append(
            _error(
                source,
                "immutable",
                "SCANNER_RELEASE_NOT_IMMUTABLE",
                "The latest upstream scanner release is not marked immutable.",
            )
        )
    assets = release.get("assets")
    if not isinstance(assets, list):
        return errors + [
            _error(
                source,
                "assets",
                "REMOTE_RESPONSE_INVALID",
                "The upstream release response does not contain an asset list.",
            )
        ]
    matching_assets = [
        asset
        for asset in assets
        if isinstance(asset, dict) and asset.get("name") == scanner["linux_amd64_asset_name"]
    ]
    if len(matching_assets) != 1:
        errors.append(
            _error(
                source,
                "assets",
                "SCANNER_RELEASE_ASSET_MISSING",
                "The reviewed Linux amd64 scanner asset is missing or ambiguous upstream.",
            )
        )
    elif matching_assets[0].get("digest") != f"sha256:{scanner['linux_amd64_archive_sha256']}":
        errors.append(
            _error(
                source,
                "assets.digest",
                "SCANNER_ASSET_DIGEST_DRIFT",
                "The upstream Linux amd64 scanner asset digest differs from the reviewed lock.",
            )
        )
    return errors


def fetch_remote_release(*, attempts: int = 3, timeout: float = 10.0) -> dict[str, Any]:
    request = urllib.request.Request(
        TRIVY_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "structural-spec-kb-container-security-validator",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                value = json.load(response)
            if not isinstance(value, dict):
                raise ValueError("GitHub release response root is not an object")
            return value
        except (OSError, ValueError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1 + attempt)
    raise RuntimeError("Unable to resolve the latest upstream scanner release.") from last_error


def _string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
    )


def validate_exceptions(
    exceptions: dict[str, Any],
    *,
    source: str,
    today: date,
    maximum_exception_days: int,
) -> tuple[int, list[ValidationError]]:
    errors: list[ValidationError] = []
    if set(exceptions) != {"vulnerabilities"}:
        errors.append(
            _error(
                source,
                "root",
                "EXCEPTION_ROOT_INVALID",
                "Exception file may contain only the vulnerabilities list.",
            )
        )
    items = exceptions.get("vulnerabilities")
    if not isinstance(items, list):
        return 0, errors + [
            _error(
                source,
                "vulnerabilities",
                "EXCEPTION_LIST_INVALID",
                "Vulnerability exceptions must be a list.",
            )
        ]

    allowed_fields = {"id", "paths", "purls", "expired_at", "statement"}
    seen: set[tuple[str, tuple[str, ...], tuple[str, ...]]] = set()
    for index, item in enumerate(items):
        location = f"vulnerabilities[{index}]"
        if not isinstance(item, dict):
            errors.append(
                _error(source, location, "EXCEPTION_INVALID", "Each exception must be an object.")
            )
            continue
        unknown = sorted(set(item) - allowed_fields)
        if unknown:
            errors.append(
                _error(
                    source,
                    location,
                    "EXCEPTION_FIELD_UNKNOWN",
                    "Exception contains fields outside the approved Trivy schema.",
                )
            )
        vulnerability_id = item.get("id")
        if not isinstance(vulnerability_id, str) or not vulnerability_id.strip():
            errors.append(
                _error(
                    source,
                    f"{location}.id",
                    "EXCEPTION_ID_INVALID",
                    "Exception must identify one vulnerability.",
                )
            )
            vulnerability_id = ""
        paths = item.get("paths")
        purls = item.get("purls")
        if paths is not None and not _string_list(paths):
            errors.append(
                _error(
                    source,
                    f"{location}.paths",
                    "EXCEPTION_SCOPE_INVALID",
                    "Exception paths must be a non-empty string list.",
                )
            )
        if purls is not None and not _string_list(purls):
            errors.append(
                _error(
                    source,
                    f"{location}.purls",
                    "EXCEPTION_SCOPE_INVALID",
                    "Exception PURLs must be a non-empty string list.",
                )
            )
        if not _string_list(paths) and not _string_list(purls):
            errors.append(
                _error(
                    source,
                    location,
                    "EXCEPTION_SCOPE_MISSING",
                    "Global vulnerability exceptions are forbidden; paths or PURLs are required.",
                )
            )

        raw_expiry = item.get("expired_at")
        expiry: date | None = None
        if isinstance(raw_expiry, str):
            try:
                expiry = datetime.strptime(raw_expiry, "%Y-%m-%d").date()
            except ValueError:
                pass
        if expiry is None:
            errors.append(
                _error(
                    source,
                    f"{location}.expired_at",
                    "EXCEPTION_EXPIRY_INVALID",
                    "Exception expiry must use YYYY-MM-DD.",
                )
            )
        elif expiry <= today:
            errors.append(
                _error(
                    source,
                    f"{location}.expired_at",
                    "EXCEPTION_EXPIRED",
                    "Expired vulnerability exceptions fail closed.",
                )
            )
        elif expiry > today + timedelta(days=maximum_exception_days):
            errors.append(
                _error(
                    source,
                    f"{location}.expired_at",
                    "EXCEPTION_EXPIRY_TOO_LONG",
                    "Exception expiry exceeds the approved review window.",
                )
            )

        statement = item.get("statement")
        if not isinstance(statement, str) or not all(
            marker in statement for marker in ("owner=", "tracking=", "reason=")
        ):
            errors.append(
                _error(
                    source,
                    f"{location}.statement",
                    "EXCEPTION_STATEMENT_INVALID",
                    "Exception statement must record owner=, tracking=, and reason=.",
                )
            )

        identity = (
            vulnerability_id,
            tuple(sorted(paths)) if _string_list(paths) else (),
            tuple(sorted(purls)) if _string_list(purls) else (),
        )
        if identity in seen:
            errors.append(
                _error(
                    source,
                    location,
                    "EXCEPTION_DUPLICATE",
                    "Duplicate vulnerability exception scope is forbidden.",
                )
            )
        seen.add(identity)
    return len(items), errors


def validate_workflow_text(
    text: str, *, source: str, lock: dict[str, Any]
) -> list[ValidationError]:
    scanner = lock["scanner"]
    policy = lock["policy"]
    action = scanner["setup_action"]
    expected_action = f"uses: {action['source']}@{action['ref']} # {action['version']}"
    required = {
        "SETUP_ACTION_CONTRACT_MISSING": expected_action,
        "SCANNER_VERSION_CONTRACT_MISSING": f"version: {scanner['version']}",
        "SCANNER_IDENTITY_OUTPUT_MISSING": "trivy version",
        "SBOM_OUTPUT_MISSING": "--format spdx-json",
        "SBOM_PATH_MISSING": "container-sbom.spdx.json",
        "VULNERABILITY_REPORT_MISSING": "container-vulnerabilities.json",
        "VULNERABILITY_JSON_MISSING": "--format json",
        "SEVERITY_GATE_MISSING": f"--severity {','.join(policy['severities'])}",
        "PACKAGE_TYPE_GATE_MISSING": f"--pkg-types {','.join(policy['package_types'])}",
        "UNFIXED_POLICY_MISSING": "--ignore-unfixed",
        "EXCEPTION_FILE_MISSING": "--ignorefile .trivyignore.yaml",
        "BLOCKING_EXIT_CODE_MISSING": "--exit-code 1",
        "SCAN_TIMEOUT_MISSING": f"--timeout {policy['timeout']}",
        "ARTIFACT_RETENTION_MISSING": f"retention-days: {policy['artifact_retention_days']}",
        "WEEKLY_SCAN_MISSING": "schedule:",
        "POLICY_VALIDATOR_MISSING": "python scripts/validate_container_security.py",
    }
    return [
        _error(
            source,
            "workflow",
            code,
            f"Container security workflow contract is missing required token: {token}",
        )
        for code, token in required.items()
        if token not in text
    ]


def build_report(
    *,
    lock_path: Path,
    exceptions_path: Path,
    workflow_path: Path,
    today: date | None = None,
    remote_release: dict[str, Any] | None = None,
) -> dict[str, object]:
    errors: list[ValidationError] = []
    lock_data, lock_error = load_json_object(lock_path)
    if lock_error is not None:
        errors.append(lock_error)
        lock_data = {}
    normalized_lock, lock_errors = validate_lock(lock_data or {}, source=str(lock_path))
    errors.extend(lock_errors)
    if normalized_lock is not None and remote_release is not None:
        errors.extend(
            validate_remote_release(remote_release, source=TRIVY_RELEASE_API, lock=normalized_lock)
        )

    exceptions_data, exceptions_error = load_json_object(exceptions_path)
    if exceptions_error is not None:
        errors.append(exceptions_error)
        exceptions_data = {}
    policy = (normalized_lock or {}).get("policy", {})
    maximum_days = policy.get("maximum_exception_days", 90)
    if not isinstance(maximum_days, int):
        maximum_days = 90
    exception_count, exception_errors = validate_exceptions(
        exceptions_data or {},
        source=str(exceptions_path),
        today=today or date.today(),
        maximum_exception_days=maximum_days,
    )
    errors.extend(exception_errors)

    try:
        workflow_text = workflow_path.read_text(encoding="utf-8")
    except OSError:
        errors.append(
            _error(
                str(workflow_path),
                "file",
                "WORKFLOW_UNAVAILABLE",
                "Container CI workflow is unavailable.",
            )
        )
    else:
        if normalized_lock is not None:
            errors.extend(
                validate_workflow_text(
                    workflow_text, source=str(workflow_path), lock=normalized_lock
                )
            )

    unique_errors = {
        (error.source, error.location, error.code, error.message): error for error in errors
    }
    return {
        "ok": not unique_errors,
        "scanner_version": (normalized_lock or {}).get("scanner", {}).get("version"),
        "exception_count": exception_count,
        "errors": [asdict(error) for error in unique_errors.values()],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(
        description="Validate the container SBOM, vulnerability gate, and exception governance contract."
    )
    parser.add_argument(
        "--lock", type=Path, default=root / "security" / "container-security-lock.json"
    )
    parser.add_argument("--exceptions", type=Path, default=root / ".trivyignore.yaml")
    parser.add_argument(
        "--workflow",
        type=Path,
        default=repository_root() / ".github" / "workflows" / "structural-spec-kb-ci.yml",
    )
    parser.add_argument(
        "--check-remote",
        action="store_true",
        help="Compare the reviewed scanner release and asset digest with GitHub's latest release.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    remote_release: dict[str, Any] | None = None
    remote_error: ValidationError | None = None
    if args.check_remote:
        try:
            remote_release = fetch_remote_release()
        except RuntimeError:
            remote_error = _error(
                TRIVY_RELEASE_API,
                "request",
                "REMOTE_QUERY_FAILED",
                "Unable to verify the latest upstream scanner release after bounded retries.",
            )
    report = build_report(
        lock_path=args.lock.resolve(),
        exceptions_path=args.exceptions.resolve(),
        workflow_path=args.workflow.resolve(),
        remote_release=remote_release,
    )
    if remote_error is not None:
        errors = report["errors"]
        assert isinstance(errors, list)
        errors.append(asdict(remote_error))
        report["ok"] = False
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
