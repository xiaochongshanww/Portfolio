from __future__ import annotations

import json
from copy import deepcopy
from datetime import date
from pathlib import Path

from scripts.validate_container_security import (
    build_report,
    validate_exceptions,
    validate_lock,
    validate_remote_release,
    validate_workflow_text,
)


def valid_lock() -> dict[str, object]:
    return {
        "schema_version": 1,
        "scanner": {
            "name": "trivy",
            "repository": "aquasecurity/trivy",
            "version": "v0.73.0",
            "release_url": "https://github.com/aquasecurity/trivy/releases/tag/v0.73.0",
            "release_immutable": True,
            "linux_amd64_asset_name": "trivy_0.73.0_Linux-64bit.tar.gz",
            "linux_amd64_archive_sha256": "a" * 64,
            "incident_advisory": (
                "https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23"
            ),
            "setup_action": {
                "source": "aquasecurity/setup-trivy",
                "ref": "b" * 40,
                "version": "v0.2.6",
            },
        },
        "policy": {
            "image": "structural-spec-kb:ci",
            "severities": ["HIGH", "CRITICAL"],
            "package_types": ["os", "library"],
            "ignore_unfixed": True,
            "timeout": "10m",
            "artifact_retention_days": 14,
            "maximum_exception_days": 90,
        },
    }


def valid_workflow(lock: dict[str, object]) -> str:
    scanner = lock["scanner"]
    policy = lock["policy"]
    assert isinstance(scanner, dict)
    assert isinstance(policy, dict)
    action = scanner["setup_action"]
    assert isinstance(action, dict)
    return f"""
on:
  schedule:
    - cron: '43 4 * * 2'
steps:
  - run: python scripts/validate_container_security.py
  - uses: {action["source"]}@{action["ref"]} # {action["version"]}
    with:
      version: {scanner["version"]}
  - run: trivy version
  - run: trivy image --format spdx-json --output container-sbom.spdx.json
  - run: trivy image --format json --output container-vulnerabilities.json
  - run: >-
      trivy image --severity HIGH,CRITICAL --pkg-types os,library
      --ignore-unfixed --ignorefile .trivyignore.yaml --exit-code 1
      --timeout {policy["timeout"]} structural-spec-kb:ci
  - uses: actions/upload-artifact@{"c" * 40} # v7.0.1
    with:
      retention-days: {policy["artifact_retention_days"]}
"""


def write_report_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    lock = valid_lock()
    lock_path = tmp_path / "lock.json"
    exceptions_path = tmp_path / ".trivyignore.yaml"
    workflow_path = tmp_path / "workflow.yml"
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    exceptions_path.write_text(json.dumps({"vulnerabilities": []}), encoding="utf-8")
    workflow_path.write_text(valid_workflow(lock), encoding="utf-8")
    return lock_path, exceptions_path, workflow_path


def test_valid_container_security_contract_passes(tmp_path: Path) -> None:
    lock_path, exceptions_path, workflow_path = write_report_inputs(tmp_path)

    report = build_report(
        lock_path=lock_path,
        exceptions_path=exceptions_path,
        workflow_path=workflow_path,
        today=date(2026, 8, 9),
    )

    assert report["ok"] is True
    assert report["scanner_version"] == "v0.73.0"
    assert report["exception_count"] == 0
    assert report["errors"] == []


def test_lock_rejects_mutable_action_and_incomplete_scanner_version() -> None:
    lock = valid_lock()
    scanner = lock["scanner"]
    assert isinstance(scanner, dict)
    scanner["version"] = "latest"
    action = scanner["setup_action"]
    assert isinstance(action, dict)
    action["ref"] = "v0.2.6"

    normalized, errors = validate_lock(lock, source="lock.json")

    assert normalized is None
    assert {error.code for error in errors} >= {
        "SCANNER_VERSION_INVALID",
        "SETUP_ACTION_REF_INVALID",
    }


def test_lock_rejects_policy_drift_and_unreviewed_release() -> None:
    lock = valid_lock()
    scanner = lock["scanner"]
    policy = lock["policy"]
    assert isinstance(scanner, dict)
    assert isinstance(policy, dict)
    scanner["release_immutable"] = False
    policy["severities"] = ["CRITICAL"]
    policy["ignore_unfixed"] = False

    _, errors = validate_lock(lock, source="lock.json")

    assert {error.code for error in errors} >= {
        "RELEASE_NOT_REVIEWED_IMMUTABLE",
        "POLICY_VALUE_INVALID",
    }


def test_matching_remote_release_passes() -> None:
    lock = valid_lock()
    scanner = lock["scanner"]
    assert isinstance(scanner, dict)
    release = {
        "tag_name": scanner["version"],
        "immutable": True,
        "assets": [
            {
                "name": scanner["linux_amd64_asset_name"],
                "digest": f"sha256:{scanner['linux_amd64_archive_sha256']}",
            }
        ],
    }

    errors = validate_remote_release(release, source="release-api", lock=lock)

    assert errors == []


def test_remote_release_drift_is_rejected() -> None:
    lock = valid_lock()
    scanner = lock["scanner"]
    assert isinstance(scanner, dict)
    release = {
        "tag_name": "v0.74.0",
        "immutable": False,
        "assets": [
            {
                "name": scanner["linux_amd64_asset_name"],
                "digest": "sha256:" + "f" * 64,
            }
        ],
    }

    errors = validate_remote_release(release, source="release-api", lock=lock)

    assert {error.code for error in errors} == {
        "SCANNER_RELEASE_DRIFT",
        "SCANNER_RELEASE_NOT_IMMUTABLE",
        "SCANNER_ASSET_DIGEST_DRIFT",
    }


def test_remote_release_requires_reviewed_asset() -> None:
    lock = valid_lock()
    scanner = lock["scanner"]
    assert isinstance(scanner, dict)

    errors = validate_remote_release(
        {"tag_name": scanner["version"], "immutable": True, "assets": []},
        source="release-api",
        lock=lock,
    )

    assert "SCANNER_RELEASE_ASSET_MISSING" in {error.code for error in errors}


def test_scoped_exception_with_governance_metadata_passes() -> None:
    exceptions = {
        "vulnerabilities": [
            {
                "id": "CVE-2026-1234",
                "purls": ["pkg:pypi/example@1.0.0"],
                "expired_at": "2026-09-01",
                "statement": "owner=platform; tracking=SEC-12; reason=no compatible fix",
            }
        ]
    }

    count, errors = validate_exceptions(
        exceptions,
        source=".trivyignore.yaml",
        today=date(2026, 8, 9),
        maximum_exception_days=90,
    )

    assert count == 1
    assert errors == []


def test_global_exception_is_rejected() -> None:
    exceptions = {
        "vulnerabilities": [
            {
                "id": "CVE-2026-1234",
                "expired_at": "2026-09-01",
                "statement": "owner=platform; tracking=SEC-12; reason=no compatible fix",
            }
        ]
    }

    _, errors = validate_exceptions(
        exceptions,
        source=".trivyignore.yaml",
        today=date(2026, 8, 9),
        maximum_exception_days=90,
    )

    assert "EXCEPTION_SCOPE_MISSING" in {error.code for error in errors}


def test_expired_and_overlong_exceptions_are_rejected() -> None:
    template = {
        "id": "CVE-2026-1234",
        "paths": ["usr/lib/example"],
        "statement": "owner=platform; tracking=SEC-12; reason=no compatible fix",
    }
    exceptions = {
        "vulnerabilities": [
            {**template, "expired_at": "2026-08-09"},
            {**template, "id": "CVE-2026-5678", "expired_at": "2026-12-01"},
        ]
    }

    _, errors = validate_exceptions(
        exceptions,
        source=".trivyignore.yaml",
        today=date(2026, 8, 9),
        maximum_exception_days=90,
    )

    assert {error.code for error in errors} >= {
        "EXCEPTION_EXPIRED",
        "EXCEPTION_EXPIRY_TOO_LONG",
    }


def test_exception_requires_owner_tracking_and_reason() -> None:
    exceptions = {
        "vulnerabilities": [
            {
                "id": "CVE-2026-1234",
                "paths": ["usr/lib/example"],
                "expired_at": "2026-09-01",
                "statement": "temporarily accepted",
            }
        ]
    }

    _, errors = validate_exceptions(
        exceptions,
        source=".trivyignore.yaml",
        today=date(2026, 8, 9),
        maximum_exception_days=90,
    )

    assert "EXCEPTION_STATEMENT_INVALID" in {error.code for error in errors}


def test_duplicate_exception_scope_is_rejected() -> None:
    item = {
        "id": "CVE-2026-1234",
        "paths": ["usr/lib/example"],
        "expired_at": "2026-09-01",
        "statement": "owner=platform; tracking=SEC-12; reason=no compatible fix",
    }

    _, errors = validate_exceptions(
        {"vulnerabilities": [item, deepcopy(item)]},
        source=".trivyignore.yaml",
        today=date(2026, 8, 9),
        maximum_exception_days=90,
    )

    assert "EXCEPTION_DUPLICATE" in {error.code for error in errors}


def test_unknown_exception_fields_are_rejected() -> None:
    exceptions = {
        "vulnerabilities": [
            {
                "id": "CVE-2026-1234",
                "paths": ["usr/lib/example"],
                "expired_at": "2026-09-01",
                "statement": "owner=platform; tracking=SEC-12; reason=no compatible fix",
                "forever": True,
            }
        ]
    }

    _, errors = validate_exceptions(
        exceptions,
        source=".trivyignore.yaml",
        today=date(2026, 8, 9),
        maximum_exception_days=90,
    )

    assert "EXCEPTION_FIELD_UNKNOWN" in {error.code for error in errors}


def test_workflow_contract_detects_missing_blocking_gate() -> None:
    lock = valid_lock()

    errors = validate_workflow_text(
        valid_workflow(lock).replace("--exit-code 1", "--exit-code 0"),
        source="workflow.yml",
        lock=lock,
    )

    assert "BLOCKING_EXIT_CODE_MISSING" in {error.code for error in errors}


def test_workflow_contract_detects_mutable_scanner_setup() -> None:
    lock = valid_lock()
    scanner = lock["scanner"]
    assert isinstance(scanner, dict)
    action = scanner["setup_action"]
    assert isinstance(action, dict)

    errors = validate_workflow_text(
        valid_workflow(lock).replace(str(action["ref"]), "v0.2.6"),
        source="workflow.yml",
        lock=lock,
    )

    assert "SETUP_ACTION_CONTRACT_MISSING" in {error.code for error in errors}


def test_report_rejects_invalid_exception_json(tmp_path: Path) -> None:
    lock_path, exceptions_path, workflow_path = write_report_inputs(tmp_path)
    exceptions_path.write_text("vulnerabilities:\n  - id: CVE-1", encoding="utf-8")

    report = build_report(
        lock_path=lock_path,
        exceptions_path=exceptions_path,
        workflow_path=workflow_path,
        today=date(2026, 8, 9),
    )

    assert report["ok"] is False
    assert "JSON_INVALID" in {error["code"] for error in report["errors"]}
