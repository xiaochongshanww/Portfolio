# CI 外部 Action 供应链验证记录

> 状态：已完成
> 维护角色：工程负责人
> 文档更新：2026-08-09
> 代码/流程核对：2026-08-09
> 完整运行验证：本地 381 项后端测试、完整工程门禁及 14 个外部引用校验通过；[CI #67](https://github.com/xiaochongshanww/Portfolio/actions/runs/31290399694) 十项任务全部通过且无运行时弃用警告
> 验证证据：[实施清单](../architecture/CI外部Action供应链实施清单.md)、[ADR 0018](../adr/0018-CI外部Action采用不可变引用与自动维护.md)、`tests/test_ci_actions.py`
> 复核周期：I-028 收口或 CI action 基线变化时

## 验证范围

本记录验证 GitHub Actions 外部执行代码是否具有不可变身份、可读版本、项目核验的 Node.js 24 运行时代际和持续更新入口。它不替代上游 action 的安全审计，也不证明 GitHub 平台或第三方供应链绝对可信。

## 本地结果

| 检查 | 结果 |
| --- | --- |
| 生效 workflow | 1 份 |
| 外部 action 引用 | 14 处，全部为 40 位小写提交 SHA |
| 版本注释 | 14 处均存在 `vX.Y.Z` 注释 |
| 运行时代际 | 5 类官方 action 均达到项目核验的 Node.js 24 最低代际 |
| 专项测试 | `5 passed` |
| Dependabot | `github-actions` 生态、仓库根目录、weekly 分组更新已配置 |

专项测试覆盖仓库真实 workflow、可变引用、缺失注释、旧代际、本地 action 和容器 action。校验器输出 ASCII 安全 JSON，失败时提供 workflow、行号、稳定错误码和非秘密原因。

## 上游核对

2026-08-09 使用各官方 Git 仓库标签引用和对应提交的 `action.yml` 交叉核对 ADR 0018 中的提交与 Node.js 运行时。当前选择保持 checkout/setup 既有主版本，仅将 artifact action 提升到消除 Node.js 20 警告所需的最低已核验代际，以缩小行为变更范围。

## 工程门禁

| 门禁 | 结果 |
| --- | --- |
| 后端全量测试 | `381 passed, 1 skipped` |
| 前端组件、类型、安全审计与构建 | 9 项测试通过；类型检查通过；high 级审计 0 漏洞；生产构建通过 |
| 三套 Python 依赖锁 | runtime、dev、parser 均无漂移 |
| 配置示例、Compose 与质量证据 | 46 个键、6 个空敏感键、实际配置预检、Compose 渲染及脱敏快照校验通过 |
| 远程 CI | [CI #67](https://github.com/xiaochongshanww/Portfolio/actions/runs/31290399694) 十项任务全部通过，提交 `3b43d22` |

远程矩阵使用固定 SHA 的 action 分别在 Linux 和 Windows 生成真实 Chroma 知识包，并完成 Windows→Linux、Linux→Windows 双向导入、探测和 API 冷启动。运行产出两份制品，全部任务成功；摘要没有 `Annotations`，相较 CI #66 的 4 条 Node.js 20 警告已清零。

## 收口检查

- [x] 实现与专项测试完成。
- [x] 本地全量门禁通过并记录结果。
- [x] 实现提交推送且远程 CI 全部通过。
- [x] 远程运行不再出现 Node.js 20 action 弃用警告。
- [x] 路线图、文档中心和实施清单标记为完成。
