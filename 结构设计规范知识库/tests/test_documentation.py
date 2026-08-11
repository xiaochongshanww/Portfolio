import json
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
        header = "\n".join(markdown_file.read_text(encoding="utf-8").splitlines()[:30])
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


def test_admin_api_contract_generation_is_documented():
    readme = Path("README.md").read_text(encoding="utf-8")
    api_reference = Path("docs/reference/接口参考.md").read_text(encoding="utf-8")
    contract = Path("docs/reference/管理API与前端类型契约规范.md").read_text(encoding="utf-8")
    detailed_design = Path("docs/architecture/系统详细设计.md").read_text(encoding="utf-8")

    for text in (readme, api_reference, contract):
        assert "python scripts/export_openapi.py" in text
        assert "npm run api:generate" in text
    assert "npm run api:check" in readme
    assert "npm run api:check" in contract
    assert "Pydantic" in detailed_design
    assert "frontend/openapi.json" in detailed_design


def test_managed_quality_api_lifecycle_is_documented():
    readme = Path("README.md").read_text(encoding="utf-8")
    config_reference = Path("docs/reference/配置参考.md").read_text(encoding="utf-8")
    operations = Path("docs/operations/知识库维护与质量运营.md").read_text(encoding="utf-8")
    detailed_design = Path("docs/architecture/系统详细设计.md").read_text(encoding="utf-8")
    decision = Path("docs/adr/0015-无人值守质量验证采用受控本地API生命周期.md")
    checklist = Path("docs/architecture/质量验证托管API生命周期实施清单.md")

    command = "python scripts/verify_quality.py --manage-api --api-base http://127.0.0.1:8017"
    assert command in readme
    assert "--api-start-timeout-seconds" in config_reference
    assert "managed_quality_api_latest.log" in operations
    assert "一命令质量验证" in detailed_design
    assert decision.is_file()
    assert checklist.is_file()


def test_configuration_example_validation_is_documented():
    readme = Path("README.md").read_text(encoding="utf-8")
    config_reference = Path("docs/reference/配置参考.md").read_text(encoding="utf-8")
    operations = Path("docs/operations/部署运行手册.md").read_text(encoding="utf-8")
    governance = Path("docs/文档治理规则.md").read_text(encoding="utf-8")
    detailed_design = Path("docs/architecture/系统详细设计.md").read_text(encoding="utf-8")
    release_checklist = Path("docs/releases/发布检查单.md").read_text(encoding="utf-8")
    implementation = Path("docs/architecture/配置示例可执行验证实施清单.md")
    command = "python scripts/validate_configuration_example.py"
    compose_command = "docker compose --env-file .env.example config --quiet"

    assert command in readme
    assert command in config_reference
    assert command.replace("/", "\\") in operations
    assert "tests/test_configuration_example.py" in governance
    assert "Windows/Linux 后端 CI" in detailed_design
    assert compose_command in release_checklist
    assert implementation.is_file()


def test_active_architecture_and_release_entry_points_are_current():
    overview = Path("docs/architecture/系统架构概览.md").read_text(encoding="utf-8")
    detailed_design = Path("docs/architecture/系统详细设计.md").read_text(encoding="utf-8")
    deployment = Path("docs/operations/部署运行手册.md").read_text(encoding="utf-8")
    release_checklist = Path("docs/releases/发布检查单.md").read_text(encoding="utf-8")
    decisions = sorted(Path("docs/adr").glob("[0-9][0-9][0-9][0-9]-*.md"))

    assert decisions
    active_architecture = overview + detailed_design
    assert all(decision.name in active_architecture for decision in decisions)
    assert decisions[-1].name in overview
    assert "scripts/validate_configuration_example.py" in overview
    assert "openwebui-preflight" in overview

    managed_command = (
        "python scripts/verify_quality.py --manage-api --api-base http://127.0.0.1:8017"
    )
    assert managed_command in deployment
    assert managed_command in release_checklist


def test_compose_pull_resilience_is_documented():
    readme = Path("README.md").read_text(encoding="utf-8")
    deployment = Path("docs/operations/部署运行手册.md").read_text(encoding="utf-8")
    detailed_design = Path("docs/architecture/系统详细设计.md").read_text(encoding="utf-8")
    release_checklist = Path("docs/releases/发布检查单.md").read_text(encoding="utf-8")

    pull_command = "python scripts/pull_compose_images.py open-webui"
    start_contract = "--pull never"
    assert pull_command in readme
    assert pull_command in deployment
    assert start_contract in readme
    assert start_contract in deployment
    assert "scripts/pull_compose_images.py" in detailed_design
    assert "python scripts/pull_compose_images.py <service>" in release_checklist


def test_rag_system_card_matches_latest_quality_evidence():
    system_card = Path("docs/quality/检索增强生成系统卡.md").read_text(encoding="utf-8")
    snapshot = json.loads(Path("docs/quality/质量证据状态.json").read_text(encoding="utf-8"))
    verification = snapshot["reports"]["verification"]
    quality_gate = snapshot["reports"]["quality_gate"]

    assert f"`verification.generated_at={verification['generated_at']}`" in system_card
    assert f"`verification.passed={str(verification['passed']).lower()}`" in system_card
    assert f"`quality_gate.generated_at={quality_gate['generated_at']}`" in system_card
    assert f"`quality_gate.passed={str(quality_gate['passed']).lower()}`" in system_card
    failed_checks = ",".join(snapshot["quality_gate_failed_checks"])
    assert f"`quality_gate.failed_checks={failed_checks}`" in system_card

    for name, evaluation_set in snapshot["evaluation_sets"].items():
        marker = f"`evaluation_set.{name}.case_count={evaluation_set['case_count']}`"
        assert marker in system_card

    if snapshot["release_quality_status"] != "passed":
        assert "当前没有可用于发布的完整通过证据" in system_card

    snapshot_command = "python scripts/snapshot_quality_evidence.py"
    for documentation_path in (
        Path("README.md"),
        Path("docs/operations/知识库维护与质量运营.md"),
        Path("docs/releases/发布检查单.md"),
    ):
        documentation = documentation_path.read_text(encoding="utf-8")
        assert snapshot_command in documentation


def test_quality_evidence_history_contract_is_documented():
    readme = Path("README.md").read_text(encoding="utf-8")
    system_card = Path("docs/quality/检索增强生成系统卡.md").read_text(encoding="utf-8")
    detailed_design = Path("docs/architecture/系统详细设计.md").read_text(encoding="utf-8")
    operations = Path("docs/operations/知识库维护与质量运营.md").read_text(encoding="utf-8")
    release_checklist = Path("docs/releases/发布检查单.md").read_text(encoding="utf-8")
    decision = Path("docs/adr/0016-脱敏质量证据采用不可变历史归档.md")
    checklist = Path("docs/architecture/质量证据历史归档实施清单.md")
    history_index = Path("docs/quality/质量证据历史索引.json")

    assert "质量证据历史" in readme
    assert "确定性索引" in system_card
    assert "不可变历史" in detailed_design
    assert "归档结构与文件名指纹" in operations
    assert "当前快照已进入不可变历史" in release_checklist
    assert "外部信任根" in decision.read_text(encoding="utf-8")
    assert decision.is_file()
    assert checklist.is_file()
    assert history_index.is_file()


def test_quality_preflight_contract_is_documented():
    readme = Path("README.md").read_text(encoding="utf-8")
    config_reference = Path("docs/reference/配置参考.md").read_text(encoding="utf-8")
    operations = Path("docs/operations/知识库维护与质量运营.md").read_text(encoding="utf-8")
    detailed_design = Path("docs/architecture/系统详细设计.md").read_text(encoding="utf-8")
    release_checklist = Path("docs/releases/发布检查单.md").read_text(encoding="utf-8")
    decision = Path("docs/adr/0017-质量验证采用无副作用前置条件预检.md")
    checklist = Path("docs/architecture/质量验证无副作用预检实施清单.md")
    command = (
        "python scripts/verify_quality.py --manage-api --preflight-only "
        "--api-base http://127.0.0.1:8017"
    )

    assert command in readme
    assert "不运行测试、评估、门禁或写入质量报告" in config_reference
    assert command in operations
    assert "不写任何质量 `latest` 报告" in detailed_design
    assert "--preflight-only" in release_checklist
    assert "不能解释为模型内容质量失败" in decision.read_text(encoding="utf-8")
    assert decision.is_file()
    assert checklist.is_file()


def test_ci_action_supply_chain_contract_is_documented():
    readme = Path("README.md").read_text(encoding="utf-8")
    governance = Path("docs/文档治理规则.md").read_text(encoding="utf-8")
    detailed_design = Path("docs/architecture/系统详细设计.md").read_text(encoding="utf-8")
    release_checklist = Path("docs/releases/发布检查单.md").read_text(encoding="utf-8")
    decision = Path("docs/adr/0018-CI外部Action采用不可变引用与自动维护.md")
    checklist = Path("docs/architecture/CI外部Action供应链实施清单.md")
    dependabot = Path("../.github/dependabot.yml")
    command = "python scripts/validate_ci_actions.py"

    assert command in readme
    assert command in governance
    assert command in release_checklist
    assert "完整提交 SHA" in detailed_design
    assert "不自动合并" in decision.read_text(encoding="utf-8")
    assert decision.is_file()
    assert checklist.is_file()
    assert dependabot.is_file()


def test_container_image_identity_contract_is_documented():
    readme = Path("README.md").read_text(encoding="utf-8")
    operations = Path("docs/operations/部署运行手册.md").read_text(encoding="utf-8")
    detailed_design = Path("docs/architecture/系统详细设计.md").read_text(encoding="utf-8")
    release_checklist = Path("docs/releases/发布检查单.md").read_text(encoding="utf-8")
    decision = Path("docs/adr/0022-外部容器镜像采用标签与多架构摘要双重固定.md")
    implementation = Path("docs/architecture/容器镜像不可变身份与更新治理实施清单.md")
    verification = Path("docs/releases/容器镜像不可变身份与更新治理验证记录.md")
    command = "python scripts/validate_container_images.py"

    assert command in readme
    assert command in operations
    assert f"{command} --check-remote" in operations
    assert command in release_checklist
    assert "docker compose config --format json" in detailed_design
    assert "漏洞" in decision.read_text(encoding="utf-8")
    assert decision.is_file()
    assert implementation.is_file()
    assert verification.is_file()


def test_container_security_contract_is_documented():
    readme = Path("README.md").read_text(encoding="utf-8")
    operations = Path("docs/operations/部署运行手册.md").read_text(encoding="utf-8")
    detailed_design = Path("docs/architecture/系统详细设计.md").read_text(encoding="utf-8")
    release_checklist = Path("docs/releases/发布检查单.md").read_text(encoding="utf-8")
    decision = Path("docs/adr/0023-运行容器采用SBOM与时效化漏洞门禁.md")
    implementation = Path("docs/architecture/运行容器SBOM与漏洞门禁实施清单.md")
    verification = Path("docs/releases/运行容器SBOM与漏洞门禁验证记录.md")
    command = "python scripts/validate_container_security.py"

    assert command in readme
    assert command in operations
    assert f"{command} --check-remote" in operations
    assert command in release_checklist
    assert "SPDX JSON" in detailed_design
    assert "HIGH/CRITICAL" in decision.read_text(encoding="utf-8")
    assert decision.is_file()
    assert implementation.is_file()
    assert verification.is_file()


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
