from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from dotenv.parser import parse_stream

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"
PASSTHROUGH_ENV_NAMES = {
    "COMSPEC",
    "HOME",
    "PATH",
    "PATHEXT",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "WINDIR",
}
SENSITIVE_SUFFIXES = (
    "_KEY",
    "_KEYS",
    "_PASSWORD",
    "_SECRET",
    "_SECRETS",
    "_TOKEN",
    "_TOKENS",
)
ENV_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
EXPECTED_EXAMPLE_KEYS = {
    "ANSWER_EVALUATION_API_BASE",
    "API_AUTH_ENABLED",
    "API_KEYS",
    "ASSET_SIGNING_KEY",
    "ASSET_URL_TTL_SECONDS",
    "CORS_ALLOW_CREDENTIALS",
    "CORS_ORIGINS",
    "DATA_DIR",
    "DB_DIR",
    "EMBEDDING_MODEL",
    "IMG_BASE_URL",
    "JOB_HEARTBEAT_SECONDS",
    "JOB_STALE_AFTER_SECONDS",
    "LLM_TIMEOUT_SECONDS",
    "LOG_FORMAT",
    "LOG_LEVEL",
    "MAX_REQUEST_BYTES",
    "MIMO_API_KEY",
    "MIMO_BASE_URL",
    "MIMO_MODEL",
    "MINERU_ARGS",
    "MINERU_BIN",
    "MINERU_COMPATIBILITY_POLICY",
    "OPENWEBUI_API_KEY",
    "OPENWEBUI_AUTH",
    "PDF_PARSER_BACKEND",
    "PUBLIC_ASSET_BASE_URL",
    "QUALITY_API_KEY",
    "RAG_MIN_SCORE",
    "RAG_TOP_K",
    "RATE_LIMIT_ENABLED",
    "RATE_LIMIT_PER_MINUTE",
    "RERANK_ENABLED",
    "RERANK_PROVIDER",
    "RETRIEVAL_BM25_WEIGHT",
    "RETRIEVAL_CLAUSE_BOOST",
    "RETRIEVAL_DENSE_WEIGHT",
    "STATIC_DIR",
    "VERSION_RETENTION_FAILED_DAYS",
    "VERSION_RETENTION_HIGH_WATERMARK_BYTES",
    "VERSION_RETENTION_KEEP_RECENT_PASSED",
    "VERSION_RETENTION_LOW_WATERMARK_BYTES",
    "VERSION_RETENTION_MINIMUM_AGE_HOURS",
    "VERSION_RETENTION_PLAN_TTL_MINUTES",
    "VERSION_RETENTION_SUCCESS_DAYS",
    "ZHIPUAI_API_KEY",
}


class ConfigurationExampleError(ValueError):
    def __init__(self, issues: list[str] | str):
        self.issues = (issues,) if isinstance(issues, str) else tuple(issues)
        super().__init__("；".join(self.issues))


@dataclass(frozen=True)
class ConfigurationExample:
    path: Path
    values: dict[str, str]
    sensitive_key_count: int


def _is_sensitive_name(name: str) -> bool:
    normalized = name.upper()
    return normalized == "PASSWORD" or normalized.endswith(SENSITIVE_SUFFIXES)


def _parse_stream(stream: TextIO, *, path: Path) -> ConfigurationExample:
    values: dict[str, str] = {}
    first_names: dict[str, tuple[str, int]] = {}
    issues: list[str] = []
    sensitive_key_count = 0

    for binding in parse_stream(stream):
        line_number = binding.original.line
        if binding.error:
            issues.append(f"第 {line_number} 行不是有效的 dotenv 语法")
            continue
        if binding.key is None:
            continue
        name = binding.key
        normalized_name = name.upper()
        if not ENV_NAME_PATTERN.fullmatch(name):
            issues.append(f"第 {line_number} 行的变量名 {name!r} 不符合环境变量格式")
            continue
        if normalized_name in first_names:
            first_name, first_line = first_names[normalized_name]
            issues.append(
                f"变量 {name} 与 {first_name} 在第 {first_line} 行和第 {line_number} 行重复"
            )
            continue
        if binding.value is None:
            issues.append(f"变量 {name} 必须显式使用 KEY=VALUE 格式")
            continue
        values[name] = binding.value
        first_names[normalized_name] = (name, line_number)
        if _is_sensitive_name(name):
            sensitive_key_count += 1
            if binding.value:
                issues.append(f"敏感变量 {name} 在示例文件中必须留空")

    if not values:
        issues.append("配置示例没有任何有效变量")
    if issues:
        raise ConfigurationExampleError(issues)
    return ConfigurationExample(
        path=path,
        values=values,
        sensitive_key_count=sensitive_key_count,
    )


def parse_configuration_example(path: Path) -> ConfigurationExample:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ConfigurationExampleError(f"配置示例文件不存在：{resolved}")
    try:
        with resolved.open(encoding="utf-8") as stream:
            return _parse_stream(stream, path=resolved)
    except UnicodeDecodeError as exc:
        raise ConfigurationExampleError("配置示例必须是 UTF-8 文本") from exc
    except OSError as exc:
        raise ConfigurationExampleError(f"无法读取配置示例：{resolved}") from exc


def validate_example_key_contract(example: ConfigurationExample) -> None:
    actual = set(example.values)
    missing = sorted(EXPECTED_EXAMPLE_KEYS - actual)
    unexpected = sorted(actual - EXPECTED_EXAMPLE_KEYS)
    issues: list[str] = []
    if missing:
        issues.append("配置示例缺少约定变量：" + ", ".join(missing))
    if unexpected:
        issues.append("配置示例包含未知变量：" + ", ".join(unexpected))
    if issues:
        raise ConfigurationExampleError(issues)


def _isolated_environment(values: dict[str, str]) -> dict[str, str]:
    environment = {
        name: value for name, value in os.environ.items() if name.upper() in PASSTHROUGH_ENV_NAMES
    }
    environment.update(values)
    environment["PYTHON_DOTENV_DISABLED"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def validate_application_configuration(example: ConfigurationExample) -> None:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "src.app.core.config"],
            cwd=PROJECT_ROOT,
            env=_isolated_environment(example.values),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
    except OSError as exc:
        raise ConfigurationExampleError("无法启动应用配置预检子进程") from exc
    if completed.returncode != 0:
        raise ConfigurationExampleError(
            f"应用配置预检失败，退出码 {completed.returncode}；"
            "请运行 python -m src.app.core.config 定位具体字段"
        )


def validate_configuration_example(path: Path = DEFAULT_EXAMPLE_PATH) -> dict[str, object]:
    example = parse_configuration_example(path)
    validate_example_key_contract(example)
    validate_application_configuration(example)
    return {
        "ok": True,
        "path": str(example.path),
        "key_count": len(example.values),
        "sensitive_key_count": example.sensitive_key_count,
        "configuration_preflight": "passed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="验证 dotenv 配置示例及应用启动配置")
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_EXAMPLE_PATH,
        help="待验证的 dotenv 示例，默认使用项目根 .env.example",
    )
    args = parser.parse_args()
    try:
        result = validate_configuration_example(args.path)
    except ConfigurationExampleError as exc:
        result = {
            "ok": False,
            "error": "configuration_example_invalid",
            "issues": list(exc.issues),
        }
        print(json.dumps(result, ensure_ascii=True), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
