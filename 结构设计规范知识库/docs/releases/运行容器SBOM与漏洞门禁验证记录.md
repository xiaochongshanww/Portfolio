# 运行容器 SBOM 与漏洞门禁验证记录

> 状态：验证中
>
> 维护角色：工程负责人
>
> 文档更新：2026-08-09
>
> 代码/流程核对：扫描器锁、策略校验、workflow、artifact 和例外边界已核对
>
> 完整运行验证：本地 459 项后端测试、9 项前端测试、完整工程门禁和真实上游发行版漂移校验通过；远程真实镜像扫描待完成
>
> 验证证据：[实施清单](../architecture/运行容器SBOM与漏洞门禁实施清单.md)、[ADR 0023](../adr/0023-运行容器采用SBOM与时效化漏洞门禁.md)
>
> 复核周期：运行镜像、扫描器、数据库来源、策略或例外变化时
>
> 迭代编号：I-033

## 当前安全基线

| 项目 | 当前值 | 验证边界 |
| --- | --- | --- |
| 扫描器 | Trivy `v0.73.0` | 版本固定，不代表扫描器或数据库绝对可信 |
| 安装 Action | `aquasecurity/setup-trivy@3fb12ec12f41e471780db15c232d5dd185dcb514` | 官方事件处置后安全提交，仍按第三方代码审阅 |
| 扫描对象 | `structural-spec-kb:ci` | CI 实际构建并通过健康检查的最终运行镜像 |
| 阻断阈值 | 可修复 HIGH/CRITICAL，OS + library | 未修复项进入完整报告但不阻断 |
| 例外 | 0 项 | 全局和永久例外禁止 |
| 证据 | scanner version + SPDX JSON + 完整漏洞 JSON | CI artifact 保留 14 天，不提交仓库 |

## 已取得证据

- `python scripts/validate_container_security.py` 通过，锁、空例外基线和 workflow 扫描契约一致。
- 15 项定向测试通过，覆盖可变 Action、版本/策略漂移、远端发行版/资产摘要漂移、全局例外、过期/过长例外、治理字段、重复范围、未知字段和非阻断 workflow 回退。
- `python scripts/validate_ci_actions.py` 识别 18 个外部 Action 引用，新增 setup 与 artifact Action 均固定完整提交并保留语义版本注释。
- `python scripts/validate_container_security.py --check-remote` 已实际查询上游，固定 `v0.73.0`、不可变标记与 Linux amd64 资产 SHA-256 当前一致。
- Ruff 检查与格式、459 项后端测试（另 1 项按既有条件跳过）、Python 依赖锁、配置示例、Compose 渲染、质量证据、Action、镜像身份和容器安全策略门禁通过。
- 前端 9 项组件测试、类型检查、`npm audit --audit-level=high` 和生产构建通过，审计结果为 0 个已知高危及以上漏洞。

## 待完成证据

- GitHub Runner 上安装固定扫描器并取得实际 scanner version、非空 SPDX SBOM 和完整漏洞 JSON artifact。
- 若门禁发现可修复 HIGH/CRITICAL，完成依赖/基础镜像升级或建立满足范围和期限要求的例外。
- 远程十任务矩阵通过并回写 CI run。

## 结论边界

当前不能把 I-033 标记为完成。已实现的本地策略只证明门禁配置结构完整；尚未证明扫描器能分析真实镜像，也没有当次漏洞数据库结果。无论最终是否为零发现，本记录都不证明零漏洞、许可证合规、镜像签名、发布者身份、内容授权或模型回答质量通过。
