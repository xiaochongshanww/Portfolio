from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

DEFAULT_ATTEMPTS = 5
DEFAULT_INITIAL_DELAY_SECONDS = 2.0
DEFAULT_MAX_DELAY_SECONDS = 30.0
DEFAULT_ATTEMPT_TIMEOUT_SECONDS = 600.0

SERVICE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b([a-z0-9_-]*(?:api[_-]?key|password|secret|token)[a-z0-9_-]*)"
    r"\s*([:=])\s*([^\s,;]+)"
)
AUTHORIZATION_HEADER_PATTERN = re.compile(
    r"(?i)\b(authorization\s*:\s*(?:bearer|basic))\s+[^\s,;]+"
)
AUTHORIZATION_ASSIGNMENT_PATTERN = re.compile(r"(?i)\b(authorization)\s*(=)\s*([^\s,;]+)")
URL_USERINFO_PATTERN = re.compile(r"(?i)(https?://)([^/@\s:]+):([^/@\s]+)@")

TRANSIENT_ERROR_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "registry_rate_limit",
        (
            "toomanyrequests",
            "too many requests",
            "rate limit",
            "retry-after",
            "status code 429",
            "status: 429",
        ),
    ),
    (
        "network_timeout",
        (
            "tls handshake timeout",
            "tls: bad record mac",
            "i/o timeout",
            "context deadline exceeded",
            "client.timeout exceeded",
            "request canceled while waiting",
        ),
    ),
    (
        "connection_interrupted",
        (
            "connection reset by peer",
            "connection aborted",
            "connection refused",
            "unexpected eof",
        ),
    ),
    (
        "temporary_dns",
        (
            "temporary failure in name resolution",
            "server misbehaving",
        ),
    ),
    (
        "gateway_unavailable",
        (
            "502 bad gateway",
            "503 service unavailable",
            "504 gateway timeout",
        ),
    ),
)


def redact_output(value: str) -> str:
    redacted = AUTHORIZATION_HEADER_PATTERN.sub(r"\1 [REDACTED]", value)
    redacted = AUTHORIZATION_ASSIGNMENT_PATTERN.sub(r"\1\2[REDACTED]", redacted)
    redacted = SENSITIVE_ASSIGNMENT_PATTERN.sub(r"\1\2[REDACTED]", redacted)
    return URL_USERINFO_PATTERN.sub(r"\1[REDACTED]@", redacted)


def classify_transient_error(output: str) -> str | None:
    normalized = output.casefold()
    for category, patterns in TRANSIENT_ERROR_PATTERNS:
        if any(pattern in normalized for pattern in patterns):
            return category
    return None


def build_pull_command(
    services: Sequence[str],
    *,
    policy: str,
    compose_file: Path | None = None,
    project_directory: Path | None = None,
) -> list[str]:
    command = ["docker", "compose"]
    if project_directory is not None:
        command.extend(["--project-directory", str(project_directory)])
    if compose_file is not None:
        command.extend(["--file", str(compose_file)])
    command.extend(["pull", "--ignore-buildable", "--quiet", "--policy", policy, *services])
    return command


def _validate_options(
    services: Sequence[str],
    attempts: int,
    initial_delay: float,
    max_delay: float,
    attempt_timeout: float,
    policy: str,
) -> None:
    if not services:
        raise ValueError("at least one Compose service is required")
    invalid_services = [
        service for service in services if not SERVICE_NAME_PATTERN.fullmatch(service)
    ]
    if invalid_services:
        raise ValueError(f"invalid Compose service name: {invalid_services[0]}")
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if initial_delay < 0:
        raise ValueError("initial delay must not be negative")
    if max_delay < initial_delay:
        raise ValueError("maximum delay must be greater than or equal to initial delay")
    if attempt_timeout <= 0:
        raise ValueError("attempt timeout must be greater than 0")
    if policy not in {"missing", "always"}:
        raise ValueError("policy must be 'missing' or 'always'")


def pull_compose_images(
    services: Sequence[str],
    *,
    attempts: int = DEFAULT_ATTEMPTS,
    initial_delay: float = DEFAULT_INITIAL_DELAY_SECONDS,
    max_delay: float = DEFAULT_MAX_DELAY_SECONDS,
    attempt_timeout: float = DEFAULT_ATTEMPT_TIMEOUT_SECONDS,
    policy: str = "missing",
    compose_file: Path | None = None,
    project_directory: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    sleeper: Callable[[float], None] = time.sleep,
    output: Callable[[str], None] | None = None,
) -> int:
    _validate_options(services, attempts, initial_delay, max_delay, attempt_timeout, policy)
    emit = output or (lambda message: print(message, file=sys.stderr, flush=True))
    command = build_pull_command(
        services,
        policy=policy,
        compose_file=compose_file,
        project_directory=project_directory,
    )
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
                timeout=attempt_timeout,
            )
        except subprocess.TimeoutExpired:
            should_retry = attempt < attempts
            status = "retry" if should_retry else "failed"
            emit(
                "[compose-pull] "
                f"attempt={attempt}/{attempts} status={status} "
                f"classification=attempt_timeout timeout_seconds={attempt_timeout:g}"
            )
            if should_retry:
                sleeper(delay)
                delay = min(max_delay, delay * 2)
                continue
            return 124
        except OSError as exc:
            emit(
                "[compose-pull] "
                f"attempt={attempt}/{attempts} status=failed classification=command_unavailable "
                f"error={redact_output(str(exc))}"
            )
            return 127

        combined_output = "\n".join(
            part.strip() for part in (completed.stdout, completed.stderr) if part and part.strip()
        )
        if completed.returncode == 0:
            if combined_output:
                emit(redact_output(combined_output))
            emit(
                "[compose-pull] "
                f"attempt={attempt}/{attempts} status=success services={','.join(services)}"
            )
            return 0

        classification = classify_transient_error(combined_output)
        should_retry = classification is not None and attempt < attempts
        if combined_output:
            emit(redact_output(combined_output))

        if should_retry:
            emit(
                "[compose-pull] "
                f"attempt={attempt}/{attempts} status=retry "
                f"classification={classification} exit_code={completed.returncode} "
                f"retry_in_seconds={delay:g}"
            )
            sleeper(delay)
            delay = min(max_delay, delay * 2)
            continue

        final_classification = classification or "permanent_or_unknown"
        emit(
            "[compose-pull] "
            f"attempt={attempt}/{attempts} status=failed "
            f"classification={final_classification} exit_code={completed.returncode}"
        )
        return completed.returncode

    raise AssertionError("unreachable retry state")


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must not be negative")
    return parsed


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than 0")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pull selected Docker Compose service images with bounded transient retries."
    )
    parser.add_argument("services", nargs="+", help="Compose service names to pull")
    parser.add_argument("--attempts", type=_positive_int, default=DEFAULT_ATTEMPTS)
    parser.add_argument(
        "--initial-delay",
        type=_non_negative_float,
        default=DEFAULT_INITIAL_DELAY_SECONDS,
        help="seconds before the first retry",
    )
    parser.add_argument(
        "--max-delay",
        type=_non_negative_float,
        default=DEFAULT_MAX_DELAY_SECONDS,
        help="maximum delay between retries",
    )
    parser.add_argument(
        "--attempt-timeout",
        type=_positive_float,
        default=DEFAULT_ATTEMPT_TIMEOUT_SECONDS,
        help="maximum seconds for one Compose pull attempt",
    )
    parser.add_argument("--policy", choices=("missing", "always"), default="missing")
    parser.add_argument("--compose-file", type=Path)
    parser.add_argument("--project-directory", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return pull_compose_images(
            args.services,
            attempts=args.attempts,
            initial_delay=args.initial_delay,
            max_delay=args.max_delay,
            attempt_timeout=args.attempt_timeout,
            policy=args.policy,
            compose_file=args.compose_file,
            project_directory=args.project_directory,
        )
    except ValueError as exc:
        print(f"compose image pull configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
