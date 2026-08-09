from __future__ import annotations

import json
import subprocess

import pytest
from scripts import validate_container_images as validator

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64


def pinned(tag: str, digest: str = DIGEST_A) -> str:
    return f"{tag}@{digest}"


def valid_dockerfile(*, runtime_digest: str = DIGEST_B) -> str:
    return "\n".join(
        [
            f"# syntax={pinned('docker/dockerfile:1')}",
            f"FROM {pinned('node:22-alpine')} AS frontend-builder",
            f"FROM {pinned('python:3.11-slim', DIGEST_B)} AS python-builder",
            f"FROM {pinned('python:3.11-slim', runtime_digest)} AS runtime",
        ]
    )


def valid_compose_config(*, external_image: str | None = None):
    return {
        "services": {
            "api": {"build": {"context": "."}, "image": "structural-spec-kb:local"},
            "openwebui-preflight": {"image": "structural-spec-kb:local"},
            "open-webui": {
                "image": external_image or pinned("ghcr.io/open-webui/open-webui:v0.9.5", DIGEST_C)
            },
        }
    }


def completed(returncode: int, *, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(
        ["docker", "buildx", "imagetools", "inspect"],
        returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_split_pinned_reference_requires_tag_and_sha256_digest():
    assert validator.split_pinned_reference(pinned("python:3.11-slim")) == (
        "python:3.11-slim",
        DIGEST_A,
    )
    assert validator.split_pinned_reference(f"python@{DIGEST_A}") is None
    assert validator.split_pinned_reference("python:3.11-slim") is None
    assert validator.split_pinned_reference("python:3.11-slim@sha256:not-a-digest") is None


def test_dockerfile_validation_accepts_pinned_frontend_and_matching_stages():
    references, errors = validator.validate_dockerfile_text(valid_dockerfile())

    assert errors == []
    assert len(references) == 4
    assert {reference.stage for reference in references} == {
        None,
        "frontend-builder",
        "python-builder",
        "runtime",
    }


def test_dockerfile_validation_rejects_mutable_frontend_and_base_images():
    text = (
        valid_dockerfile()
        .replace(pinned("docker/dockerfile:1"), "docker/dockerfile:1")
        .replace(pinned("node:22-alpine"), "node:22-alpine")
    )

    _references, errors = validator.validate_dockerfile_text(text)

    assert [error.code for error in errors].count("IMAGE_REFERENCE_NOT_PINNED") == 2


def test_dockerfile_validation_requires_syntax_and_python_stage_pair():
    text = "\n".join(
        [
            f"FROM {pinned('python:3.11-slim')} AS builder",
            "FROM builder AS final",
        ]
    )

    _references, errors = validator.validate_dockerfile_text(text)

    assert {error.code for error in errors} >= {
        "DOCKERFILE_SYNTAX_MISSING",
        "PYTHON_STAGE_PAIR_MISSING",
    }
    assert all(error.code != "IMAGE_REFERENCE_NOT_PINNED" for error in errors)


def test_dockerfile_validation_allows_scratch_without_treating_it_as_external():
    text = valid_dockerfile() + "\nFROM scratch AS export"

    references, errors = validator.validate_dockerfile_text(text)

    assert errors == []
    assert all(reference.stage != "export" for reference in references)


def test_dockerfile_validation_rejects_python_stage_digest_mismatch():
    _references, errors = validator.validate_dockerfile_text(
        valid_dockerfile(runtime_digest=DIGEST_C)
    )

    assert {error.code for error in errors} == {
        "TAG_DIGEST_CONFLICT",
        "PYTHON_STAGE_IMAGE_MISMATCH",
    }


def test_compose_validation_allows_named_local_build_image_reuse():
    references, errors = validator.validate_compose_config(valid_compose_config())

    assert errors == []
    assert [reference.tag_reference for reference in references] == [
        "ghcr.io/open-webui/open-webui:v0.9.5"
    ]


def test_compose_validation_rejects_mutable_external_image():
    _references, errors = validator.validate_compose_config(
        valid_compose_config(external_image="ghcr.io/open-webui/open-webui:v0.9.5")
    )

    assert [error.code for error in errors] == ["IMAGE_REFERENCE_NOT_PINNED"]


def test_compose_validation_requires_explicit_local_build_image():
    config = {"services": {"external": {"image": pinned("example/image:1")}}}

    _references, errors = validator.validate_compose_config(config)

    assert "COMPOSE_LOCAL_BUILD_IMAGE_MISSING" in {error.code for error in errors}


def test_load_compose_config_uses_json_render_without_exposing_stderr(tmp_path):
    calls: list[tuple[list[str], dict]] = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return completed(0, stdout=json.dumps(valid_compose_config()), stderr="SECRET=value")

    config, error = validator.load_compose_config(
        compose_file=tmp_path / "compose.yml",
        env_file=tmp_path / ".env",
        runner=run,
    )

    assert error is None
    assert config == valid_compose_config()
    assert calls[0][0][-3:] == ["config", "--format", "json"]
    assert calls[0][1]["timeout"] == 30


@pytest.mark.parametrize(
    ("runner", "expected_code"),
    [
        (lambda *_args, **_kwargs: completed(1, stderr="SECRET=value"), "COMPOSE_RENDER_FAILED"),
        (lambda *_args, **_kwargs: completed(0, stdout="not-json"), "COMPOSE_JSON_INVALID"),
    ],
)
def test_load_compose_config_reports_stable_failures(tmp_path, runner, expected_code):
    config, error = validator.load_compose_config(
        compose_file=tmp_path / "compose.yml",
        env_file=tmp_path / ".env",
        runner=runner,
    )

    assert config is None
    assert error is not None
    assert error.code == expected_code
    assert "SECRET" not in error.message


def test_load_compose_config_reports_unavailable_command_without_exception_details(tmp_path):
    def unavailable(*_args, **_kwargs):
        raise FileNotFoundError("SECRET docker path")

    config, error = validator.load_compose_config(
        compose_file=tmp_path / "compose.yml",
        env_file=tmp_path / ".env",
        runner=unavailable,
    )

    assert config is None
    assert error is not None
    assert error.code == "COMPOSE_COMMAND_UNAVAILABLE"
    assert "SECRET" not in error.message


def test_resolve_remote_digest_retries_then_returns_manifest_digest():
    results = iter(
        [
            completed(1, stderr="temporary registry failure"),
            completed(0, stdout=json.dumps({"digest": DIGEST_A})),
        ]
    )
    sleeps: list[float] = []

    digest, error = validator.resolve_remote_digest(
        "python:3.11-slim",
        attempts=2,
        initial_delay=0.5,
        runner=lambda *_args, **_kwargs: next(results),
        sleeper=sleeps.append,
    )

    assert digest == DIGEST_A
    assert error is None
    assert sleeps == [0.5]


def test_resolve_remote_digest_distinguishes_timeout_and_invalid_manifest():
    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(["docker", "buildx"], 1)

    digest, error = validator.resolve_remote_digest("python:3.11-slim", attempts=1, runner=timeout)
    invalid_digest, invalid_error = validator.resolve_remote_digest(
        "python:3.11-slim",
        attempts=1,
        runner=lambda *_args, **_kwargs: completed(0, stdout="{}"),
    )

    assert digest is None
    assert error == "REMOTE_QUERY_TIMEOUT"
    assert invalid_digest is None
    assert invalid_error == "REMOTE_MANIFEST_INVALID"


def test_remote_drift_check_deduplicates_tags_and_reports_drift():
    references, errors = validator.validate_dockerfile_text(valid_dockerfile())
    assert errors == []
    queries: list[str] = []

    def resolve(tag_reference):
        queries.append(tag_reference)
        return (DIGEST_C if tag_reference == "python:3.11-slim" else DIGEST_A), None

    drift_errors = validator.check_remote_drift(references, resolver=resolve)

    assert queries.count("python:3.11-slim") == 1
    assert [error.code for error in drift_errors] == ["REMOTE_DIGEST_DRIFT"]
    assert drift_errors[0].location == "python:3.11-slim"


def test_remote_drift_check_distinguishes_query_failure():
    reference = validator.ImageReference(
        source="Dockerfile",
        location="line 1",
        reference=pinned("python:3.11-slim"),
        tag_reference="python:3.11-slim",
        digest=DIGEST_A,
    )

    errors = validator.check_remote_drift(
        [reference], resolver=lambda _tag: (None, "REMOTE_COMMAND_UNAVAILABLE")
    )

    assert [error.code for error in errors] == ["REMOTE_COMMAND_UNAVAILABLE"]
