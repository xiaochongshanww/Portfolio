from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SYNTAX_RE = re.compile(r"^\s*#\s*syntax=(?P<reference>\S+)\s*$")
FROM_RE = re.compile(
    r"^\s*FROM(?:\s+--platform=\S+)?\s+(?P<reference>\S+)"
    r"(?:\s+AS\s+(?P<stage>[A-Za-z0-9_.-]+))?\s*$",
    re.IGNORECASE,
)

DEFAULT_REMOTE_ATTEMPTS = 3
DEFAULT_REMOTE_TIMEOUT_SECONDS = 60.0
DEFAULT_REMOTE_INITIAL_DELAY_SECONDS = 2.0


@dataclass(frozen=True)
class ImageReference:
    source: str
    location: str
    reference: str
    tag_reference: str
    digest: str
    stage: str | None = None


@dataclass(frozen=True)
class ValidationError:
    source: str
    location: str
    code: str
    message: str


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def split_pinned_reference(reference: str) -> tuple[str, str] | None:
    tag_reference, separator, digest = reference.rpartition("@")
    if not separator or not tag_reference or DIGEST_RE.fullmatch(digest) is None:
        return None
    image_name = tag_reference.rsplit("/", 1)[-1]
    if ":" not in image_name:
        return None
    return tag_reference, digest


def _validate_reference(
    reference: str,
    *,
    source: str,
    location: str,
    stage: str | None = None,
) -> tuple[ImageReference | None, ValidationError | None]:
    parsed = split_pinned_reference(reference)
    if parsed is None:
        return None, ValidationError(
            source=source,
            location=location,
            code="IMAGE_REFERENCE_NOT_PINNED",
            message=(
                "External container images must use a reviewer-readable tag followed by "
                "an immutable sha256 digest."
            ),
        )
    tag_reference, digest = parsed
    return (
        ImageReference(
            source=source,
            location=location,
            reference=reference,
            tag_reference=tag_reference,
            digest=digest,
            stage=stage,
        ),
        None,
    )


def validate_dockerfile_text(
    text: str,
    *,
    source: str = "Dockerfile",
) -> tuple[list[ImageReference], list[ValidationError]]:
    references: list[ImageReference] = []
    errors: list[ValidationError] = []
    stage_aliases: set[str] = set()
    syntax_found = False

    for line_number, line in enumerate(text.splitlines(), start=1):
        syntax_match = SYNTAX_RE.match(line)
        if syntax_match is not None:
            syntax_found = True
            reference, error = _validate_reference(
                syntax_match.group("reference"),
                source=source,
                location=f"line {line_number} (syntax)",
            )
            if reference is not None:
                references.append(reference)
            if error is not None:
                errors.append(error)
            continue

        from_match = FROM_RE.match(line)
        if from_match is None:
            continue
        image = from_match.group("reference")
        stage = from_match.group("stage")
        normalized_image = image.casefold()
        if normalized_image != "scratch" and normalized_image not in stage_aliases:
            reference, error = _validate_reference(
                image,
                source=source,
                location=f"line {line_number} (FROM)",
                stage=stage,
            )
            if reference is not None:
                references.append(reference)
            if error is not None:
                errors.append(error)
        if stage:
            stage_aliases.add(stage.casefold())

    if not syntax_found:
        errors.append(
            ValidationError(
                source=source,
                location="line 1",
                code="DOCKERFILE_SYNTAX_MISSING",
                message="Dockerfile must declare an immutable external syntax frontend.",
            )
        )
    if not any(reference.stage is not None for reference in references):
        errors.append(
            ValidationError(
                source=source,
                location="Dockerfile",
                code="DOCKERFILE_EXTERNAL_BASE_MISSING",
                message="Dockerfile has no validated external build stage image.",
            )
        )

    _append_tag_conflict_errors(references, errors)
    _append_required_stage_errors(references, errors)
    return references, errors


def _append_tag_conflict_errors(
    references: Sequence[ImageReference], errors: list[ValidationError]
) -> None:
    digests_by_tag: dict[str, set[str]] = {}
    for reference in references:
        digests_by_tag.setdefault(reference.tag_reference, set()).add(reference.digest)
    for tag_reference, digests in sorted(digests_by_tag.items()):
        if len(digests) > 1:
            errors.append(
                ValidationError(
                    source="container-images",
                    location=tag_reference,
                    code="TAG_DIGEST_CONFLICT",
                    message="The same image tag is pinned to more than one digest.",
                )
            )


def _append_required_stage_errors(
    references: Sequence[ImageReference], errors: list[ValidationError]
) -> None:
    by_stage = {
        reference.stage.casefold(): reference
        for reference in references
        if reference.stage is not None
    }
    builder = by_stage.get("python-builder")
    runtime = by_stage.get("runtime")
    if builder is None or runtime is None:
        errors.append(
            ValidationError(
                source="Dockerfile",
                location="python-builder/runtime",
                code="PYTHON_STAGE_PAIR_MISSING",
                message="Dockerfile must retain python-builder and runtime stages.",
            )
        )
    elif builder.reference != runtime.reference:
        errors.append(
            ValidationError(
                source="Dockerfile",
                location="python-builder/runtime",
                code="PYTHON_STAGE_IMAGE_MISMATCH",
                message="Python builder and runtime stages must use the exact same pinned image.",
            )
        )


def validate_compose_config(
    config: dict[str, Any],
    *,
    source: str = "docker-compose.yml",
) -> tuple[list[ImageReference], list[ValidationError]]:
    references: list[ImageReference] = []
    errors: list[ValidationError] = []
    services = config.get("services")
    if not isinstance(services, dict) or not services:
        return references, [
            ValidationError(
                source=source,
                location="services",
                code="COMPOSE_SERVICES_MISSING",
                message="Rendered Compose configuration has no services mapping.",
            )
        ]

    local_build_images = {
        service.get("image")
        for service in services.values()
        if isinstance(service, dict) and service.get("build") and service.get("image")
    }
    if not local_build_images:
        errors.append(
            ValidationError(
                source=source,
                location="services",
                code="COMPOSE_LOCAL_BUILD_IMAGE_MISSING",
                message="Compose must declare at least one named image produced from local build context.",
            )
        )

    for service_name, service in sorted(services.items()):
        if not isinstance(service, dict):
            errors.append(
                ValidationError(
                    source=source,
                    location=f"services.{service_name}",
                    code="COMPOSE_SERVICE_INVALID",
                    message="Rendered Compose service must be an object.",
                )
            )
            continue
        image = service.get("image")
        if not isinstance(image, str) or not image:
            continue
        if image in local_build_images:
            continue
        reference, error = _validate_reference(
            image,
            source=source,
            location=f"services.{service_name}.image",
        )
        if reference is not None:
            references.append(reference)
        if error is not None:
            errors.append(error)

    _append_tag_conflict_errors(references, errors)
    return references, errors


def load_compose_config(
    *,
    compose_file: Path,
    env_file: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[dict[str, Any] | None, ValidationError | None]:
    command = [
        "docker",
        "compose",
        "--env-file",
        str(env_file),
        "--file",
        str(compose_file),
        "config",
        "--format",
        "json",
    ]
    try:
        completed = runner(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, ValidationError(
            source=str(compose_file),
            location="docker compose config",
            code="COMPOSE_COMMAND_UNAVAILABLE",
            message="Docker Compose could not render the project configuration.",
        )
    if completed.returncode != 0:
        return None, ValidationError(
            source=str(compose_file),
            location="docker compose config",
            code="COMPOSE_RENDER_FAILED",
            message=f"Docker Compose rendering failed with exit code {completed.returncode}.",
        )
    try:
        config = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None, ValidationError(
            source=str(compose_file),
            location="docker compose config",
            code="COMPOSE_JSON_INVALID",
            message="Docker Compose returned invalid JSON.",
        )
    if not isinstance(config, dict):
        return None, ValidationError(
            source=str(compose_file),
            location="docker compose config",
            code="COMPOSE_JSON_INVALID",
            message="Docker Compose JSON root must be an object.",
        )
    return config, None


def resolve_remote_digest(
    tag_reference: str,
    *,
    attempts: int = DEFAULT_REMOTE_ATTEMPTS,
    timeout: float = DEFAULT_REMOTE_TIMEOUT_SECONDS,
    initial_delay: float = DEFAULT_REMOTE_INITIAL_DELAY_SECONDS,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    sleeper: Callable[[float], None] = time.sleep,
) -> tuple[str | None, str | None]:
    command = [
        "docker",
        "buildx",
        "imagetools",
        "inspect",
        tag_reference,
        "--format",
        "{{json .Manifest}}",
    ]
    last_error = "REMOTE_QUERY_FAILED"
    delay = initial_delay
    for attempt in range(1, attempts + 1):
        try:
            completed = runner(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            last_error = "REMOTE_QUERY_TIMEOUT"
        except OSError:
            return None, "REMOTE_COMMAND_UNAVAILABLE"
        else:
            if completed.returncode == 0:
                try:
                    manifest = json.loads(completed.stdout)
                except json.JSONDecodeError:
                    last_error = "REMOTE_MANIFEST_INVALID"
                else:
                    digest = manifest.get("digest") if isinstance(manifest, dict) else None
                    if isinstance(digest, str) and DIGEST_RE.fullmatch(digest):
                        return digest, None
                    last_error = "REMOTE_MANIFEST_INVALID"
            else:
                last_error = "REMOTE_QUERY_FAILED"
        if attempt < attempts:
            sleeper(delay)
            delay *= 2
    return None, last_error


def check_remote_drift(
    references: Sequence[ImageReference],
    *,
    resolver: Callable[[str], tuple[str | None, str | None]],
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    unique = {reference.tag_reference: reference.digest for reference in references}
    for tag_reference, expected_digest in sorted(unique.items()):
        actual_digest, error_code = resolver(tag_reference)
        if error_code is not None:
            errors.append(
                ValidationError(
                    source="registry",
                    location=tag_reference,
                    code=error_code,
                    message="The remote multi-platform image digest could not be resolved.",
                )
            )
        elif actual_digest != expected_digest:
            errors.append(
                ValidationError(
                    source="registry",
                    location=tag_reference,
                    code="REMOTE_DIGEST_DRIFT",
                    message=(
                        f"Pinned digest {expected_digest} differs from remote digest {actual_digest}."
                    ),
                )
            )
    return errors


def build_report(
    *,
    dockerfile: Path,
    compose_file: Path,
    env_file: Path,
    check_remote: bool,
    compose_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    remote_resolver: Callable[[str], tuple[str | None, str | None]] | None = None,
) -> dict[str, object]:
    references, errors = validate_dockerfile_text(
        dockerfile.read_text(encoding="utf-8"), source=str(dockerfile)
    )
    compose_config, compose_error = load_compose_config(
        compose_file=compose_file,
        env_file=env_file,
        runner=compose_runner,
    )
    if compose_error is not None:
        errors.append(compose_error)
    elif compose_config is not None:
        compose_references, compose_errors = validate_compose_config(
            compose_config, source=str(compose_file)
        )
        references.extend(compose_references)
        errors.extend(compose_errors)

    _append_tag_conflict_errors(references, errors)
    if check_remote and not errors:
        resolver = remote_resolver or (lambda tag: resolve_remote_digest(tag))
        errors.extend(check_remote_drift(references, resolver=resolver))

    unique_references = {reference.reference: reference for reference in references}
    unique_errors = {
        (error.source, error.location, error.code, error.message): error for error in errors
    }
    return {
        "ok": not unique_errors,
        "remote_check": check_remote,
        "external_image_count": len(unique_references),
        "references": [
            asdict(reference)
            for reference in sorted(unique_references.values(), key=lambda item: item.reference)
        ],
        "errors": [asdict(error) for error in unique_errors.values()],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(
        description="Validate immutable external container image references and optional registry drift."
    )
    parser.add_argument("--dockerfile", type=Path, default=root / "Dockerfile")
    parser.add_argument("--compose-file", type=Path, default=root / "docker-compose.yml")
    parser.add_argument("--env-file", type=Path, default=root / ".env.example")
    parser.add_argument("--check-remote", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_report(
            dockerfile=args.dockerfile.resolve(),
            compose_file=args.compose_file.resolve(),
            env_file=args.env_file.resolve(),
            check_remote=args.check_remote,
        )
    except OSError as exc:
        report = {
            "ok": False,
            "remote_check": args.check_remote,
            "external_image_count": 0,
            "references": [],
            "errors": [
                asdict(
                    ValidationError(
                        source="container-images",
                        location="input",
                        code="INPUT_FILE_UNAVAILABLE",
                        message=str(exc),
                    )
                )
            ],
        }
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
