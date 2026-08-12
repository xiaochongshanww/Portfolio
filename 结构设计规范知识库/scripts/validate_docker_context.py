from __future__ import annotations

import argparse
import json
import shlex
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

ALLOWED_NEGATIONS = {
    "!.dockerignore",
    "!Dockerfile",
    "!data/",
    "!data/evaluation/",
    "!data/evaluation/**",
    "!data/metadata/",
    "!data/metadata/**",
    "!frontend/",
    "!frontend/**",
    "!requirements-runtime.txt",
    "!src/",
    "!src/**",
}

REQUIRED_NESTED_DENIES = {
    "frontend/node_modules/": "!frontend/**",
    "frontend/dist/": "!frontend/**",
    "frontend/.env*": "!frontend/**",
    "frontend/coverage/": "!frontend/**",
    "frontend/.vite/": "!frontend/**",
    "frontend/.turbo/": "!frontend/**",
    "**/__pycache__/": "!src/**",
    "**/*.pyc": "!src/**",
}

REVIEWED_COPY_SOURCES = {
    "data/evaluation/",
    "data/metadata/",
    "frontend/",
    "frontend/package-lock.json",
    "frontend/package.json",
    "requirements-runtime.txt",
    "src/",
}


@dataclass(frozen=True)
class ValidationError:
    location: str
    code: str
    message: str


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def effective_rules(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def local_copy_sources(dockerfile_text: str) -> tuple[set[str], list[ValidationError]]:
    sources: set[str] = set()
    errors: list[ValidationError] = []
    for line_number, raw_line in enumerate(dockerfile_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line.casefold().startswith("copy "):
            continue
        try:
            tokens = shlex.split(line, posix=True)
        except ValueError as exc:
            errors.append(
                ValidationError(
                    location=f"Dockerfile:{line_number}",
                    code="COPY_PARSE_FAILED",
                    message=f"Unable to parse COPY instruction: {exc}",
                )
            )
            continue

        arguments = tokens[1:]
        flags = [token for token in arguments if token.startswith("--")]
        if any(flag.startswith("--from=") for flag in flags):
            continue
        paths = [token for token in arguments if not token.startswith("--")]
        if len(paths) < 2:
            errors.append(
                ValidationError(
                    location=f"Dockerfile:{line_number}",
                    code="COPY_INVALID",
                    message="Local COPY must declare at least one source and one destination.",
                )
            )
            continue
        sources.update(paths[:-1])
    return sources, errors


def validate_policy_text(
    dockerignore_text: str,
    dockerfile_text: str,
) -> list[ValidationError]:
    rules = effective_rules(dockerignore_text)
    errors: list[ValidationError] = []
    if not rules or rules[0] != "**":
        errors.append(
            ValidationError(
                location=".dockerignore:first-rule",
                code="DEFAULT_DENY_MISSING",
                message="The first effective rule must exclude the complete context with '**'.",
            )
        )

    negations = {rule for rule in rules if rule.startswith("!")}
    for rule in sorted(ALLOWED_NEGATIONS - negations):
        errors.append(
            ValidationError(
                location=".dockerignore",
                code="REQUIRED_ALLOW_MISSING",
                message=f"Required reviewed allow rule is missing: {rule}",
            )
        )
    for rule in sorted(negations - ALLOWED_NEGATIONS):
        errors.append(
            ValidationError(
                location=".dockerignore",
                code="UNREVIEWED_ALLOW_RULE",
                message=f"Context path is allowed without being part of the reviewed minimum: {rule}",
            )
        )

    positions = {rule: index for index, rule in enumerate(rules)}
    for deny, allow in REQUIRED_NESTED_DENIES.items():
        if deny not in positions:
            errors.append(
                ValidationError(
                    location=".dockerignore",
                    code="NESTED_DENY_MISSING",
                    message=f"Generated or secret-bearing path must remain excluded: {deny}",
                )
            )
        elif allow in positions and positions[deny] < positions[allow]:
            errors.append(
                ValidationError(
                    location=".dockerignore",
                    code="NESTED_DENY_ORDER_INVALID",
                    message=f"{deny} must appear after the broader allow rule {allow}.",
                )
            )

    copy_sources, copy_errors = local_copy_sources(dockerfile_text)
    errors.extend(copy_errors)
    for source in sorted(REVIEWED_COPY_SOURCES - copy_sources):
        errors.append(
            ValidationError(
                location="Dockerfile",
                code="REVIEWED_COPY_SOURCE_MISSING",
                message=f"Reviewed local COPY source is no longer present: {source}",
            )
        )
    for source in sorted(copy_sources - REVIEWED_COPY_SOURCES):
        errors.append(
            ValidationError(
                location="Dockerfile",
                code="UNREVIEWED_COPY_SOURCE",
                message=f"Local COPY source is not covered by the reviewed context policy: {source}",
            )
        )
    return errors


def build_report(*, dockerignore_path: Path, dockerfile_path: Path) -> dict[str, object]:
    errors: list[ValidationError] = []
    try:
        dockerignore_text = dockerignore_path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(
            ValidationError(
                location=str(dockerignore_path),
                code="DOCKERIGNORE_UNAVAILABLE",
                message=str(exc),
            )
        )
        dockerignore_text = ""
    try:
        dockerfile_text = dockerfile_path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(
            ValidationError(
                location=str(dockerfile_path),
                code="DOCKERFILE_UNAVAILABLE",
                message=str(exc),
            )
        )
        dockerfile_text = ""

    if not errors:
        errors.extend(validate_policy_text(dockerignore_text, dockerfile_text))
    copy_sources, _ = local_copy_sources(dockerfile_text)
    return {
        "ok": not errors,
        "allow_rule_count": len(ALLOWED_NEGATIONS),
        "copy_source_count": len(copy_sources),
        "errors": [asdict(error) for error in errors],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(
        description="Validate the default-deny Docker build context contract."
    )
    parser.add_argument("--dockerignore", type=Path, default=root / ".dockerignore")
    parser.add_argument("--dockerfile", type=Path, default=root / "Dockerfile")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        dockerignore_path=args.dockerignore.resolve(),
        dockerfile_path=args.dockerfile.resolve(),
    )
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
