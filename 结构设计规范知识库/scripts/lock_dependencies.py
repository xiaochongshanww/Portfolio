from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "dependency-lock.json"
UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class LockConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class LockTarget:
    input: str
    output: str


@dataclass(frozen=True)
class LockConfiguration:
    python_version: str
    uv_version: str
    exclude_newer: str
    generate_hashes: bool
    locks: tuple[LockTarget, ...]


def _safe_root_filename(value: Any, field: str) -> str:
    name = str(value or "").strip()
    path = Path(name)
    if not name or path.is_absolute() or len(path.parts) != 1 or path.name != name:
        raise LockConfigurationError(f"{field} 必须是项目根目录中的文件名")
    return name


def load_configuration(path: Path = CONFIG_PATH) -> LockConfiguration:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LockConfigurationError(f"无法读取依赖锁配置: {exc}") from exc

    if payload.get("schema_version") != 1:
        raise LockConfigurationError("dependency-lock.json schema_version 必须是 1")

    python_version = str(payload.get("python_version") or "").strip()
    if not re.fullmatch(r"\d+\.\d+", python_version):
        raise LockConfigurationError("python_version 必须使用 major.minor 格式")

    uv_version = str(payload.get("uv_version") or "").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", uv_version):
        raise LockConfigurationError("uv_version 必须使用完整的 major.minor.patch 版本")

    exclude_newer = str(payload.get("exclude_newer") or "").strip()
    if not UTC_TIMESTAMP_RE.fullmatch(exclude_newer):
        raise LockConfigurationError("exclude_newer 必须是 UTC 秒级时间，例如 2026-08-08T00:00:00Z")

    if payload.get("generate_hashes") is not True:
        raise LockConfigurationError("generate_hashes 必须为 true")

    raw_locks = payload.get("locks")
    if not isinstance(raw_locks, list) or not raw_locks:
        raise LockConfigurationError("locks 必须是非空数组")

    locks: list[LockTarget] = []
    seen_outputs: set[str] = set()
    for index, item in enumerate(raw_locks):
        if not isinstance(item, dict):
            raise LockConfigurationError(f"locks[{index}] 必须是对象")
        input_name = _safe_root_filename(item.get("input"), f"locks[{index}].input")
        output_name = _safe_root_filename(item.get("output"), f"locks[{index}].output")
        if input_name == output_name:
            raise LockConfigurationError(f"locks[{index}] 的输入和输出不能相同")
        if output_name in seen_outputs:
            raise LockConfigurationError(f"重复的锁文件输出: {output_name}")
        if not (PROJECT_ROOT / input_name).is_file():
            raise LockConfigurationError(f"锁输入不存在: {input_name}")
        seen_outputs.add(output_name)
        locks.append(LockTarget(input=input_name, output=output_name))

    return LockConfiguration(
        python_version=python_version,
        uv_version=uv_version,
        exclude_newer=exclude_newer,
        generate_hashes=True,
        locks=tuple(locks),
    )


def verify_uv_version(expected: str) -> None:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "uv", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            "未找到锁定版本的 uv；先执行 python -m pip install -r requirements-tools.txt"
        ) from exc
    actual = result.stdout.strip().split()
    if len(actual) < 2 or actual[0] != "uv" or actual[1] != expected:
        rendered = result.stdout.strip() or result.stderr.strip() or "unknown"
        raise RuntimeError(f"uv 版本不一致，要求 {expected}，实际 {rendered}")


def compile_locks(config: LockConfiguration, directory: Path) -> None:
    for target in config.locks:
        command = [
            sys.executable,
            "-m",
            "uv",
            "pip",
            "compile",
            "--universal",
            "--python-version",
            config.python_version,
            "--exclude-newer",
            config.exclude_newer,
            "--generate-hashes",
            "--upgrade",
            target.input,
            "-o",
            target.output,
        ]
        result = subprocess.run(command, cwd=directory, capture_output=True, text=True)
        if result.returncode != 0:
            details = (result.stderr or result.stdout).strip()
            raise RuntimeError(f"uv 生成 {target.output} 失败:\n{details}")


def write_locks(config: LockConfiguration) -> None:
    compile_locks(config, PROJECT_ROOT)
    for target in config.locks:
        print(f"updated: {target.output}")


def check_locks(config: LockConfiguration) -> bool:
    with tempfile.TemporaryDirectory(prefix="structural-kb-locks-") as raw_temp:
        temp_dir = Path(raw_temp)
        for target in config.locks:
            shutil.copy2(PROJECT_ROOT / target.input, temp_dir / target.input)
        compile_locks(config, temp_dir)

        clean = True
        for target in config.locks:
            expected_path = PROJECT_ROOT / target.output
            generated_path = temp_dir / target.output
            expected = expected_path.read_text(encoding="utf-8") if expected_path.is_file() else ""
            generated = generated_path.read_text(encoding="utf-8")
            if expected == generated:
                print(f"ok: {target.output}")
                continue
            clean = False
            print(f"stale: {target.output}", file=sys.stderr)
            diff = difflib.unified_diff(
                expected.splitlines(),
                generated.splitlines(),
                fromfile=target.output,
                tofile=f"generated/{target.output}",
                lineterm="",
                n=2,
            )
            for line in diff:
                print(line, file=sys.stderr)
        return clean


def main() -> int:
    parser = argparse.ArgumentParser(description="生成或校验 Python 通用依赖锁")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="在临时目录重新解析并比较锁文件")
    mode.add_argument("--write", action="store_true", help="按当前配置更新项目锁文件")
    args = parser.parse_args()

    try:
        config = load_configuration()
        verify_uv_version(config.uv_version)
        if args.write:
            write_locks(config)
            return 0
        return 0 if check_locks(config) else 1
    except (LockConfigurationError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"dependency lock error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
