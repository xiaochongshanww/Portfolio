from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from src.pipeline.active_db import active_db_dir, read_active_manifest
from src.pipeline.parsers.base import ParserUnavailableError
from src.pipeline.parsers.mineru import probe_mineru_cli

SCHEMA_VERSION = 1
SUPPORTED_PROFILES = {"runtime", "build"}
SUPPORTED_SYSTEMS = {"Linux", "Windows"}
SUPPORTED_MACHINES = {"amd64", "x86_64"}
SENSITIVE_NAME_PARTS = ("KEY", "TOKEN", "SECRET", "PASSWORD")
REQUIREMENT_PATTERN = re.compile(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^]]+\])?")
LOCK_PATTERN = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^]]+\])?==(?P<version>[^\s\\]+)"
)


@dataclass(frozen=True)
class Check:
    id: str
    status: str
    required: bool
    message: str
    remediation: str = ""
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.details is None:
            payload.pop("details")
        if not self.remediation:
            payload.pop("remediation")
        return payload


def _normalize_distribution_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _resolve_project_path(project_root: Path, value: str | None, default: str | Path) -> Path:
    candidate = Path(value) if value else Path(default)
    candidate = candidate.expanduser()
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate.resolve()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON 根节点不是对象")
    return payload


def _nonnegative_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)


def _load_lock_python(project_root: Path) -> str:
    payload = _read_json(project_root / "dependency-lock.json")
    value = str(payload.get("python_version") or "")
    if not re.fullmatch(r"\d+\.\d+", value):
        raise ValueError("dependency-lock.json 缺少有效 python_version")
    return value


def _direct_requirements(path: Path, *, seen: set[Path] | None = None) -> set[str]:
    resolved = path.resolve()
    visited = seen if seen is not None else set()
    if resolved in visited:
        return set()
    visited.add(resolved)
    requirements: set[str] = set()
    for raw_line in resolved.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith(("-r ", "--requirement ")):
            included = line.split(maxsplit=1)[1].strip()
            requirements.update(_direct_requirements(resolved.parent / included, seen=visited))
            continue
        matched = REQUIREMENT_PATTERN.match(line)
        if matched:
            requirements.add(_normalize_distribution_name(matched.group("name")))
    return requirements


def _locked_versions(path: Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        matched = LOCK_PATTERN.match(raw_line.strip())
        if matched:
            versions[_normalize_distribution_name(matched.group("name"))] = matched.group("version")
    return versions


def _redact_sensitive_text(text: str, environment: Mapping[str, str]) -> str:
    redacted = text
    sensitive_values = {
        value
        for name, value in environment.items()
        if value and any(part in name.upper() for part in SENSITIVE_NAME_PARTS)
    }
    for value in sorted(sensitive_values, key=len, reverse=True):
        redacted = redacted.replace(value, "[REDACTED]")
    return redacted


def _default_config_probe(
    project_root: Path, environment: Mapping[str, str]
) -> tuple[bool, list[str]]:
    completed = subprocess.run(
        [sys.executable, "-m", "src.app.core.config"],
        cwd=project_root,
        env=dict(environment),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        timeout=20,
    )
    if completed.returncode == 0:
        return True, []
    rendered = _redact_sensitive_text(
        "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip()),
        environment,
    )
    issues: list[str] = []
    for line in reversed(rendered.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("issues"), list):
            issues = [str(item) for item in payload["issues"]]
            break
    return False, issues or ["应用配置进程校验失败"]


def _check_python(project_root: Path, version_info: tuple[int, int, int]) -> Check:
    try:
        expected = _load_lock_python(project_root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return Check(
            "python_version",
            "failed",
            True,
            f"无法读取 Python 版本契约：{exc}",
            "恢复 dependency-lock.json 后重试。",
        )
    actual = f"{version_info[0]}.{version_info[1]}"
    if actual != expected:
        return Check(
            "python_version",
            "failed",
            True,
            f"当前 Python {actual}，项目要求 {expected}。",
            f"使用 Python {expected} 创建隔离环境并重新安装精确锁。",
            {"actual": actual, "expected": expected},
        )
    return Check(
        "python_version",
        "passed",
        True,
        f"Python {actual} 符合项目版本契约。",
        details={"actual": actual, "expected": expected},
    )


def _check_platform(system: str, machine: str) -> Check:
    normalized_machine = machine.casefold()
    supported = system in SUPPORTED_SYSTEMS and normalized_machine in SUPPORTED_MACHINES
    if supported:
        return Check(
            "platform_compatibility",
            "passed",
            False,
            f"{system} {machine} 位于当前内部验证矩阵。",
            details={"system": system, "machine": machine},
        )
    return Check(
        "platform_compatibility",
        "warning",
        False,
        f"{system} {machine} 不在当前内部验证矩阵。",
        "在目标环境重新执行知识包探针和完整质量验证，不要沿用既有兼容结论。",
        {"system": system, "machine": machine},
    )


def _check_dependencies(
    project_root: Path,
    profile: str,
    installed_version: Callable[[str], str],
) -> Check:
    input_name = "requirements-runtime.in" if profile == "runtime" else "requirements-parser.in"
    lock_name = "requirements-runtime.txt" if profile == "runtime" else "requirements-parser.txt"
    try:
        direct = _direct_requirements(project_root / input_name)
        locked = _locked_versions(project_root / lock_name)
    except OSError as exc:
        return Check(
            "locked_dependencies",
            "failed",
            True,
            f"无法读取依赖契约：{exc}",
            f"恢复 {input_name} 与 {lock_name} 后重试。",
        )

    missing_from_lock = sorted(direct - locked.keys())
    missing: list[str] = []
    mismatched: list[dict[str, str]] = []
    installed: list[dict[str, str]] = []
    for name in sorted(direct):
        try:
            actual = installed_version(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
            continue
        expected = locked.get(name, "")
        installed.append({"name": name, "version": actual})
        if expected and actual != expected:
            mismatched.append({"name": name, "actual": actual, "expected": expected})

    if missing_from_lock or missing or mismatched:
        return Check(
            "locked_dependencies",
            "failed",
            True,
            "精确锁直接依赖缺失或版本不一致。",
            f"执行 python -m pip install --require-hashes -r {lock_name}。",
            {
                "checked_count": len(direct),
                "missing": missing,
                "mismatched": mismatched,
                "missing_from_lock": missing_from_lock,
            },
        )
    return Check(
        "locked_dependencies",
        "passed",
        True,
        f"{len(direct)} 个直接依赖与 {lock_name} 一致。",
        details={"checked_count": len(direct), "installed": installed},
    )


def _check_configuration(
    project_root: Path,
    environment: Mapping[str, str],
    config_probe: Callable[[Path, Mapping[str, str]], tuple[bool, list[str]]],
) -> Check:
    try:
        valid, issues = config_probe(project_root, environment)
    except (OSError, subprocess.SubprocessError) as exc:
        return Check(
            "application_configuration",
            "failed",
            True,
            f"应用配置校验无法执行：{exc}",
            "确认项目文件与 Python 环境完整后重试。",
        )
    if not valid:
        return Check(
            "application_configuration",
            "failed",
            True,
            "应用配置不满足启动约束。",
            "按 issues 修正 .env 或部署环境变量后重试。",
            {"issues": issues},
        )
    return Check("application_configuration", "passed", True, "应用配置通过真实启动前校验。")


def _check_credentials(profile: str, environment: Mapping[str, str]) -> list[Check]:
    required_names = (
        ["ZHIPUAI_API_KEY"] if profile == "build" else ["ZHIPUAI_API_KEY", "MIMO_API_KEY"]
    )
    missing = [name for name in required_names if not environment.get(name, "").strip()]
    if missing:
        credential_check = Check(
            "required_credentials",
            "failed",
            True,
            "缺少当前配置所需的模型凭据。",
            "从秘密管理系统注入缺失变量后重试。",
            {"required": required_names, "missing": missing},
        )
    else:
        credential_check = Check(
            "required_credentials",
            "passed",
            True,
            "当前配置所需模型凭据均已注入。",
            details={"required": required_names, "present_count": len(required_names)},
        )
    checks = [credential_check]
    if profile == "build" and not environment.get("MIMO_API_KEY", "").strip():
        checks.append(
            Check(
                "ai_review_credential",
                "warning",
                False,
                "未注入 MIMO_API_KEY，知识构建可运行，但 AI 校对候选不可生成。",
                "需要 AI 校对时再从秘密管理系统注入 MIMO_API_KEY。",
            )
        )
    return checks


def _check_static_assets(project_root: Path, environment: Mapping[str, str]) -> Check:
    static_dir = _resolve_project_path(project_root, environment.get("STATIC_DIR"), "frontend/dist")
    index_path = static_dir / "index.html"
    if not index_path.is_file() or index_path.stat().st_size <= 0:
        return Check(
            "frontend_assets",
            "failed",
            True,
            "未找到可用的前端生产入口 frontend/dist/index.html。",
            "在 frontend 目录执行 npm ci 与 npm run build，或正确设置 STATIC_DIR。",
        )
    return Check(
        "frontend_assets",
        "passed",
        True,
        "前端生产入口存在且非空。",
        details={"index_size_bytes": index_path.stat().st_size},
    )


def _check_runtime_assets(project_root: Path, environment: Mapping[str, str]) -> list[Check]:
    data_dir = _resolve_project_path(project_root, environment.get("DATA_DIR"), "data")
    db_fallback = _resolve_project_path(project_root, environment.get("DB_DIR"), "db")
    pointer_path = data_dir / "active_db.json"
    manifest_path = data_dir / "manifest.json"
    try:
        manifest = read_active_manifest(pointer_path, manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        manifest = {}
        manifest_error = str(exc)
    else:
        manifest_error = ""

    chunk_count = _nonnegative_int(manifest.get("chunk_count")) if manifest else 0
    data_version = str(manifest.get("data_version_hash") or "") if manifest else ""
    if manifest and chunk_count > 0 and data_version:
        manifest_check = Check(
            "active_manifest",
            "passed",
            True,
            "活动 manifest 包含可用知识版本。",
            details={
                "document_count": _nonnegative_int(
                    manifest.get("document_count")
                    or (
                        len(manifest.get("documents"))
                        if isinstance(manifest.get("documents"), list)
                        else 0
                    )
                ),
                "chunk_count": chunk_count,
                "has_data_version": True,
            },
        )
    else:
        message = "活动 manifest 缺失或不完整。"
        if manifest_error:
            message = "活动 manifest 无法读取。"
        manifest_check = Check(
            "active_manifest",
            "failed",
            True,
            message,
            "导入已验证运行知识包，或在构建环境完成候选激活。",
            {"error": manifest_error} if manifest_error else None,
        )

    try:
        database_dir = active_db_dir(pointer_path) if pointer_path.exists() else db_fallback
        database_nonempty = database_dir.is_dir() and any(database_dir.iterdir())
    except (OSError, ValueError, json.JSONDecodeError):
        database_nonempty = False
    database_check = Check(
        "active_database",
        "passed" if database_nonempty else "failed",
        True,
        "活动数据库目录存在且非空。" if database_nonempty else "活动数据库目录缺失或为空。",
        "导入已验证运行知识包，或检查 DATA_DIR/DB_DIR 与 active_db.json。"
        if not database_nonempty
        else "",
    )

    metadata_path = _resolve_project_path(
        project_root,
        environment.get("SOURCE_METADATA_PATH"),
        data_dir / "metadata" / "specs.json",
    )
    try:
        metadata_payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata_valid = isinstance(metadata_payload, (dict, list)) and bool(metadata_payload)
    except (OSError, json.JSONDecodeError):
        metadata_valid = False
    metadata_check = Check(
        "source_metadata",
        "passed" if metadata_valid else "failed",
        True,
        "规范来源元数据存在且可解析。"
        if metadata_valid
        else "规范来源元数据缺失、为空或不是有效 JSON。",
        "恢复 data/metadata/specs.json，或正确设置 SOURCE_METADATA_PATH。"
        if not metadata_valid
        else "",
    )
    return [manifest_check, database_check, metadata_check]


def _check_build_inputs(project_root: Path, environment: Mapping[str, str]) -> list[Check]:
    data_dir = _resolve_project_path(project_root, environment.get("DATA_DIR"), "data")
    raw_dir = data_dir / "raw"
    pdf_count = (
        sum(1 for path in raw_dir.glob("*.pdf") if path.is_file()) if raw_dir.is_dir() else 0
    )
    source_check = Check(
        "source_pdfs",
        "passed" if pdf_count else "failed",
        True,
        f"发现 {pdf_count} 份 PDF 输入。" if pdf_count else "数据源目录中没有 PDF 输入。",
        "将 PDF 放入 DATA_DIR/raw，或正确设置 DATA_DIR。" if not pdf_count else "",
        {"pdf_count": pdf_count},
    )

    metadata_dir = data_dir / "metadata"
    metadata_ready = metadata_dir.is_dir() and os.access(metadata_dir, os.R_OK)
    metadata_check = Check(
        "build_metadata_directory",
        "passed" if metadata_ready else "failed",
        True,
        "知识生产元数据目录可读。" if metadata_ready else "知识生产元数据目录缺失或不可读。",
        "创建并维护 DATA_DIR/metadata/specs.json 后重试。" if not metadata_ready else "",
    )

    target_names = ("processed", "images", "mineru", "audit", "corrections")
    unavailable = [
        name
        for name in target_names
        if not (data_dir / name).is_dir() or not os.access(data_dir / name, os.W_OK)
    ]
    targets_check = Check(
        "build_output_directories",
        "passed" if not unavailable else "failed",
        True,
        "知识生产输出目录均已存在且可写。"
        if not unavailable
        else "部分知识生产输出目录缺失或不可写。",
        "按部署手册预先创建输出目录并授予当前进程写权限；自检不会自动创建。" if unavailable else "",
        {"checked": list(target_names), "unavailable": unavailable},
    )
    return [source_check, metadata_check, targets_check]


def _default_parser_probe() -> dict[str, Any]:
    probe = probe_mineru_cli()
    return probe.to_dict()


def _check_parser(parser_probe: Callable[[], Mapping[str, Any]]) -> Check:
    try:
        payload = dict(parser_probe())
    except (ParserUnavailableError, OSError, subprocess.SubprocessError) as exc:
        return Check(
            "pdf_parser",
            "failed",
            True,
            f"PDF 解析器不可用或不兼容：{exc}",
            "按 requirements-parser.txt 安装并保持严格兼容策略。",
        )
    verified = payload.get("verified") is True and payload.get("compatibility") == "verified"
    return Check(
        "pdf_parser",
        "passed" if verified else "failed",
        True,
        (
            f"PDF 解析器 {payload.get('implementation')} {payload.get('version')} 已验证。"
            if verified
            else "PDF 解析器不在已验证兼容矩阵。"
        ),
        "使用 magic-pdf 1.3.12 与 strict 策略。" if not verified else "",
        {
            "implementation": str(payload.get("implementation") or ""),
            "version": str(payload.get("version") or ""),
            "compatibility": str(payload.get("compatibility") or ""),
            "verified": bool(payload.get("verified")),
        },
    )


def run_doctor(
    *,
    profile: str = "runtime",
    project_root: Path | None = None,
    environment: Mapping[str, str] | None = None,
    version_info: tuple[int, int, int] | None = None,
    system: str | None = None,
    machine: str | None = None,
    installed_version: Callable[[str], str] = metadata.version,
    config_probe: Callable[
        [Path, Mapping[str, str]], tuple[bool, list[str]]
    ] = _default_config_probe,
    parser_probe: Callable[[], Mapping[str, Any]] = _default_parser_probe,
) -> dict[str, Any]:
    if profile not in SUPPORTED_PROFILES:
        raise ValueError(f"profile 必须是以下值之一：{', '.join(sorted(SUPPORTED_PROFILES))}")
    root = (project_root or Path(__file__).resolve().parents[2]).resolve()
    env = dict(os.environ if environment is None else environment)
    current_version = version_info or (
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    )
    current_system = system or platform.system()
    current_machine = machine or platform.machine()

    checks = [
        _check_python(root, current_version),
        _check_platform(current_system, current_machine),
        _check_dependencies(root, profile, installed_version),
        _check_configuration(root, env, config_probe),
        *_check_credentials(profile, env),
    ]
    if profile == "runtime":
        checks.append(_check_static_assets(root, env))
        checks.extend(_check_runtime_assets(root, env))
    else:
        checks.extend(_check_build_inputs(root, env))
        checks.append(_check_parser(parser_probe))

    failed_required = sum(1 for check in checks if check.required and check.status == "failed")
    summary = {
        "total": len(checks),
        "passed": sum(1 for check in checks if check.status == "passed"),
        "warnings": sum(1 for check in checks if check.status == "warning"),
        "failed": sum(1 for check in checks if check.status == "failed"),
        "failed_required": failed_required,
    }
    ok = failed_required == 0
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": ok,
        "status": "ready" if ok else "not_ready",
        "profile": profile,
        "checked_at": datetime.now(UTC).isoformat(),
        "platform": {
            "python": f"{current_version[0]}.{current_version[1]}.{current_version[2]}",
            "system": current_system,
            "machine": current_machine,
        },
        "summary": summary,
        "checks": [check.to_dict() for check in checks],
    }


def render_text(report: Mapping[str, Any]) -> str:
    labels = {"passed": "通过", "warning": "警告", "failed": "失败"}
    summary = report["summary"]
    lines = [
        "结构设计规范知识库环境自检",
        f"配置：{report['profile']}",
        f"结果：{'可继续' if report['ok'] else '未就绪'}",
        (f"汇总：{summary['passed']} 通过 / {summary['warnings']} 警告 / {summary['failed']} 失败"),
        "",
    ]
    for check in report["checks"]:
        lines.append(
            f"[{labels.get(check['status'], check['status'])}] {check['id']}：{check['message']}"
        )
        remediation = check.get("remediation")
        if remediation:
            lines.append(f"  修复：{remediation}")
    lines.extend(
        [
            "",
            "说明：环境自检通过不等于 API /ready 或发布质量门禁通过。",
        ]
    )
    return "\n".join(lines)
