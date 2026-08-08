import re
from pathlib import Path


MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
ROOT_MARKDOWN_ALLOWLIST = {Path("README.md")}
REQUIRED_METADATA = (
    "状态：",
    "维护角色：",
    "文档更新：",
    "完整运行验证：",
    "验证证据：",
    "复核周期：",
)
CHECK_METADATA_RE = re.compile(r"^> [^\n]*核对：", re.MULTILINE)


def _project_markdown_files() -> list[Path]:
    return [Path("README.md"), *Path("docs").rglob("*.md")]


def _local_markdown_targets(markdown_file: Path) -> list[Path]:
    targets: list[Path] = []
    text = markdown_file.read_text(encoding="utf-8")
    for raw_target in MARKDOWN_LINK_RE.findall(text):
        target = raw_target.strip().split("#", 1)[0].strip().strip("<>")
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (markdown_file.parent / target).resolve()
        if resolved.suffix.lower() == ".md":
            targets.append(resolved)
    return targets


def test_project_markdown_has_no_broken_local_links():
    markdown_files = _project_markdown_files()
    missing: list[str] = []

    for markdown_file in markdown_files:
        text = markdown_file.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = raw_target.strip().split("#", 1)[0].strip().strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (markdown_file.parent / target).resolve()
            if not resolved.exists():
                missing.append(f"{markdown_file}: {raw_target}")

    assert missing == []


def test_root_markdown_files_are_explicit_entry_points_only():
    root_markdown_files = set(Path(".").glob("*.md"))

    assert root_markdown_files == ROOT_MARKDOWN_ALLOWLIST


def test_documentation_files_have_governance_metadata():
    missing: list[str] = []

    for markdown_file in Path("docs").rglob("*.md"):
        header = "\n".join(
            markdown_file.read_text(encoding="utf-8").splitlines()[:30]
        )
        absent = [field for field in REQUIRED_METADATA if field not in header]
        if not CHECK_METADATA_RE.search(header):
            absent.append("代码/流程核对：")
        if absent:
            missing.append(f"{markdown_file}: {', '.join(absent)}")

    assert missing == []


def test_all_documentation_is_reachable_from_document_center():
    project_root = Path(".").resolve()
    entry_point = (project_root / "docs" / "文档中心.md").resolve()
    required = {path.resolve() for path in Path("docs").rglob("*.md")}
    visited: set[Path] = set()
    pending = [entry_point]

    while pending:
        current = pending.pop()
        if current in visited or not current.exists():
            continue
        visited.add(current)
        for target in _local_markdown_targets(current):
            if target == project_root / "README.md" or target in required:
                pending.append(target)

    unreachable = sorted(str(path.relative_to(project_root)) for path in required - visited)

    assert unreachable == []


def test_quality_verification_target_contract_is_documented():
    env_example = Path(".env.example").read_text(encoding="utf-8")
    config_reference = Path("docs/reference/配置参考.md").read_text(encoding="utf-8")
    api_reference = Path("docs/reference/接口参考.md").read_text(encoding="utf-8")
    operations = Path("docs/operations/知识库维护与质量运营.md").read_text(encoding="utf-8")
    decision = Path("docs/adr/0011-质量验证采用显式目标与执行失败语义.md")
    checklist = Path("docs/architecture/质量验证目标与失败语义实施清单.md")

    assert "ANSWER_EVALUATION_API_BASE=http://127.0.0.1:8000" in env_example
    assert "ANSWER_EVALUATION_API_BASE" in config_reference
    assert "评估执行失败" in api_reference
    assert "--api-base http://127.0.0.1:8017" in operations
    assert decision.is_file()
    assert checklist.is_file()


def test_quality_verification_assets_and_credentials_are_documented():
    env_example = Path(".env.example").read_text(encoding="utf-8")
    config_reference = Path("docs/reference/配置参考.md").read_text(encoding="utf-8")
    api_reference = Path("docs/reference/接口参考.md").read_text(encoding="utf-8")
    operations = Path("docs/operations/知识库维护与质量运营.md").read_text(encoding="utf-8")
    decision = Path("docs/adr/0012-质量验证采用内置评估资产与显式凭据.md")
    checklist = Path("docs/architecture/质量验证资产与凭据实施清单.md")

    assert "QUALITY_API_KEY=" in env_example
    assert "QUALITY_API_KEY_FILE" in env_example
    assert "--api-key-file" in config_reference
    assert "--no-api-key" in config_reference
    assert "evaluation_set=regular|structured" in api_reference
    assert "HTTP 422" in api_reference
    assert "--no-api-key" in operations
    assert "evaluation_set_id" in operations
    assert decision.is_file()
    assert checklist.is_file()


def test_runtime_backup_and_disaster_recovery_contract_is_documented():
    readme = Path("README.md").read_text(encoding="utf-8")
    operations = Path("docs/operations/部署运行手册.md").read_text(encoding="utf-8")
    format_reference = Path("docs/reference/运行数据快照格式规范.md").read_text(encoding="utf-8")
    release_checklist = Path("docs/releases/发布检查单.md").read_text(encoding="utf-8")
    decision = Path("docs/adr/0013-运行数据采用离线完整快照与事务恢复.md")
    checklist = Path("docs/architecture/运行数据快照与灾难恢复实施清单.md")

    for command in ("backup-create", "backup-validate", "backup-restore"):
        assert command in format_reference
    assert "--maintenance-window" in readme
    assert "--replace" in operations
    assert "旧数据" in operations
    assert "不加密" in format_reference
    assert "backup_id" in release_checklist
    assert decision.is_file()
    assert checklist.is_file()


def test_openwebui_authenticated_connection_contract_is_documented():
    env_example = Path(".env.example").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    operations = Path("docs/operations/部署运行手册.md").read_text(encoding="utf-8")
    config_reference = Path("docs/reference/配置参考.md").read_text(encoding="utf-8")
    release_checklist = Path("docs/releases/发布检查单.md").read_text(encoding="utf-8")
    decision = Path("docs/adr/0014-OpenWebUI连接采用环境托管与启动探测.md")
    checklist = Path("docs/architecture/OpenWebUI鉴权连接实施清单.md")

    assert "OPENWEBUI_AUTH=true" in env_example
    assert "openwebui-preflight" in readme
    assert "Exited (0)" in operations
    assert "两阶段轮换" in operations
    assert "不需要删除 `open-webui-data`" in operations
    assert "ENABLE_PERSISTENT_CONFIG=false" in config_reference
    assert "python -m src.app.core.openwebui_probe" in config_reference
    assert "OpenWebUI `/health` 和 `/api/models`" in release_checklist
    assert decision.is_file()
    assert checklist.is_file()
