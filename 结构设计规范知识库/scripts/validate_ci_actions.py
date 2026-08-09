from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


PINNED_REF_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_COMMENT_RE = re.compile(
    r"(?:^|\s)v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:\s|$)"
)
USES_RE = re.compile(
    r"^\s*(?:-\s*)?uses:\s*(?P<target>[^#\s]+)\s*(?:#\s*(?P<comment>.*))?$"
)

# These minimum majors are the first project-verified releases using Node.js 24.
MINIMUM_ACTION_MAJORS = {
    "actions/checkout": 6,
    "actions/setup-python": 6,
    "actions/setup-node": 7,
    "actions/upload-artifact": 6,
    "actions/download-artifact": 7,
}


@dataclass(frozen=True)
class ActionReference:
    workflow: str
    line: int
    source: str
    ref: str
    version: str | None


@dataclass(frozen=True)
class ValidationError:
    workflow: str
    line: int
    code: str
    message: str


def default_workflow_directory() -> Path:
    return Path(__file__).resolve().parents[2] / ".github" / "workflows"


def discover_workflows(workflow_directory: Path) -> list[Path]:
    return sorted(
        [
            *workflow_directory.glob("*.yml"),
            *workflow_directory.glob("*.yaml"),
        ]
    )


def _action_family(source: str) -> str:
    parts = source.lower().split("/")
    return "/".join(parts[:2]) if len(parts) >= 2 else source.lower()


def _is_local_or_container_action(target: str) -> bool:
    return target.startswith(("./", "docker://"))


def validate_workflows(
    workflow_directory: Path,
) -> tuple[list[ActionReference], list[ValidationError], int]:
    workflows = discover_workflows(workflow_directory)
    references: list[ActionReference] = []
    errors: list[ValidationError] = []

    if not workflows:
        errors.append(
            ValidationError(
                workflow=str(workflow_directory),
                line=0,
                code="NO_WORKFLOWS",
                message="No GitHub Actions workflow files were found.",
            )
        )
        return references, errors, 0

    for workflow in workflows:
        for line_number, raw_line in enumerate(
            workflow.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if "uses:" not in raw_line or raw_line.lstrip().startswith("#"):
                continue
            match = USES_RE.match(raw_line)
            if match is None:
                errors.append(
                    ValidationError(
                        workflow=workflow.name,
                        line=line_number,
                        code="USES_SYNTAX_UNSUPPORTED",
                        message="Action references must use a single-line uses declaration.",
                    )
                )
                continue

            target = match.group("target").strip("'\"")
            if _is_local_or_container_action(target):
                continue
            if "@" not in target:
                errors.append(
                    ValidationError(
                        workflow=workflow.name,
                        line=line_number,
                        code="ACTION_REF_MISSING",
                        message=f"External action {target!r} has no immutable ref.",
                    )
                )
                continue

            source, ref = target.rsplit("@", 1)
            comment = (match.group("comment") or "").strip()
            version_match = VERSION_COMMENT_RE.search(comment)
            version = version_match.group(0).strip() if version_match else None
            references.append(
                ActionReference(
                    workflow=workflow.name,
                    line=line_number,
                    source=source,
                    ref=ref,
                    version=version,
                )
            )

            if PINNED_REF_RE.fullmatch(ref) is None:
                errors.append(
                    ValidationError(
                        workflow=workflow.name,
                        line=line_number,
                        code="ACTION_REF_MUTABLE",
                        message=(
                            f"External action {source!r} must be pinned to a full "
                            "40-character lowercase commit SHA."
                        ),
                    )
                )
            if version_match is None:
                errors.append(
                    ValidationError(
                        workflow=workflow.name,
                        line=line_number,
                        code="ACTION_VERSION_COMMENT_MISSING",
                        message=(
                            f"Pinned action {source!r} must include a reviewer-readable "
                            "semantic version comment."
                        ),
                    )
                )
                continue

            family = _action_family(source)
            minimum_major = MINIMUM_ACTION_MAJORS.get(family)
            actual_major = int(version_match.group("major"))
            if minimum_major is not None and actual_major < minimum_major:
                errors.append(
                    ValidationError(
                        workflow=workflow.name,
                        line=line_number,
                        code="ACTION_RUNTIME_DEPRECATED",
                        message=(
                            f"{family} v{actual_major} is below the project-verified "
                            f"Node.js 24 generation v{minimum_major}."
                        ),
                    )
                )

    if not references:
        errors.append(
            ValidationError(
                workflow=str(workflow_directory),
                line=0,
                code="NO_EXTERNAL_ACTIONS",
                message="No external GitHub Action references were found.",
            )
        )
    return references, errors, len(workflows)


def build_report(workflow_directory: Path) -> dict[str, object]:
    references, errors, workflow_count = validate_workflows(workflow_directory)
    return {
        "ok": not errors,
        "workflow_directory": str(workflow_directory),
        "workflow_count": workflow_count,
        "external_reference_count": len(references),
        "references": [asdict(reference) for reference in references],
        "errors": [asdict(error) for error in errors],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate immutable GitHub Actions references and project-verified "
            "Node.js runtime generations."
        )
    )
    parser.add_argument(
        "--workflow-directory",
        type=Path,
        default=default_workflow_directory(),
        help="Directory containing GitHub Actions workflow YAML files.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args.workflow_directory.resolve())
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
