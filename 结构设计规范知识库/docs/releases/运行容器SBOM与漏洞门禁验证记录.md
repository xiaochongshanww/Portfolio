# 运行容器 SBOM 与漏洞门禁验证记录

> 状态：已完成
>
> 维护角色：工程负责人
>
> 文档更新：2026-08-09
>
> 代码/流程核对：扫描器锁、策略校验、workflow、artifact 和例外边界已核对
>
> 完整运行验证：本地 459 项后端测试、9 项前端测试、完整工程门禁和真实上游发行版漂移校验通过；[CI #87](https://github.com/xiaochongshanww/Portfolio/actions/runs/31299823123) 十项任务与真实镜像扫描通过
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
- 首次远程真实扫描 [CI #86](https://github.com/xiaochongshanww/Portfolio/actions/runs/31298835837) 已成功生成并上传 SBOM 与完整报告，门禁按设计发现 4 条具有修复版本的 HIGH 发现：`PyJWT 2.8.0` 两条、`jaraco.context 5.3.0` 一条、`wheel 0.45.1` 一条。
- 旧 `zhipuai 2.1.5.20250825` 将 PyJWT 限制为 `<2.9.0`，不能得到安全修复；代码已迁移到[官方长期维护 SDK](https://github.com/zai-org/z-ai-sdk-python) `zai-sdk 0.2.3` 并固定 `PyJWT 2.13.0`。最终镜像同时移除只用于构建的 pip、setuptools、wheel 和辅助包，不登记漏洞例外。
- 修复后的本地锁生成、锁漂移检查与定向测试通过；本地 Docker 构建曾在下载 `chromadb` wheel 时因 TLS record-layer 中断失败，属于外部下载瞬时故障。后续 CI #87 已在独立 GitHub Runner 完成构建、健康检查与复扫，因此未把该本地失败误判为安全结论。
- 修复提交 `5bba02e` 的 [CI #87](https://github.com/xiaochongshanww/Portfolio/actions/runs/31299823123) 十项任务全部通过；固定 Trivy `0.73.0` 对健康运行镜像完成复扫，未使用任何漏洞例外。
- `container-security-5bba02e...` artifact 已下载复核：scanner version 文件 16 bytes，SPDX JSON 355,560 bytes、176 个 package，完整漏洞 JSON 847,850 bytes、174 条发现。HIGH/CRITICAL 共 24 条，均无上游修复版本；策略阻断范围内的可修复 HIGH/CRITICAL 为 0。

## 结论边界

I-033 的工程目标已完成：最终镜像清单、完整漏洞可见性、可修复高危阻断、时效化例外和扫描器漂移维护均有本地与远程证据。完整报告仍有 24 条当前无修复版本的 HIGH/CRITICAL，须由每周扫描持续跟踪；本结论不证明零漏洞、许可证合规、镜像签名、发布者身份、内容授权或模型回答质量通过。
