# ADR 0018：CI 外部 Action 采用不可变引用与自动维护

> 状态：已接受
> 维护角色：工程负责人
> 文档更新：2026-08-09
> 代码/流程核对：2026-08-09，已核对唯一生效 workflow、官方 action 标签、提交与运行时元数据
> 完整运行验证：本地 381 项后端测试、完整工程门禁及 14 个外部引用校验通过；[CI #67](https://github.com/xiaochongshanww/Portfolio/actions/runs/31290399694) 十项任务全部通过且无运行时弃用警告
> 验证证据：[实施清单](../architecture/CI外部Action供应链实施清单.md)、[验证记录](../releases/CI外部Action供应链验证记录.md)、提交 `3b43d22`、[CI #67](https://github.com/xiaochongshanww/Portfolio/actions/runs/31290399694)
> 复核周期：GitHub Actions 引用、Runner 运行时或 Dependabot 策略变化时
> 决策日期：2026-08-09

## 背景

CI #65 虽然全部通过，但 `actions/upload-artifact@v4` 和 `actions/download-artifact@v4` 产生 Node.js 20 弃用警告。现有 workflow 还使用 `@v6`、`@v7` 等可变主版本标签；上游可以移动标签，使同一仓库提交在不同时间执行不同代码。单纯升级主版本只能暂时消除警告，不能建立可审查、可维护的供应链契约。

## 决策

1. 所有外部 GitHub Action 使用完整的 40 位小写提交 SHA，不接受分支、标签、短 SHA 或表达式引用；本地 action 与 `docker://` action 不受此规则约束。
2. 每个固定引用在同行保留 `vX.Y.Z` 注释，供人工审阅和 Dependabot 维护。注释只提供可读版本，实际执行身份仍由 SHA 决定。
3. 项目验证的最低 Node.js 24 代际为：`checkout` v6、`setup-python` v6、`setup-node` v7、`upload-artifact` v6、`download-artifact` v7。低于该代际的引用由本地校验器失败关闭。
4. `scripts/validate_ci_actions.py` 离线扫描全部 workflow，检查不可变引用、版本注释和最低代际；该命令进入 dependency-lock CI 任务及自动化测试。
5. `.github/dependabot.yml` 每周按组检查 GitHub Actions 更新。自动 PR 仍必须通过完整 CI 和人工审阅，不自动合并。
6. 上游标签与 action 元数据只在升级评审时联网核验；CI 日常验证不依赖 GitHub API，避免速率限制或网络结果改变本地结论。

## 已核验基线

| Action | 固定版本 | 固定提交 | 运行时 |
| --- | --- | --- | --- |
| `actions/checkout` | v6.1.0 | `d23441a48e516b6c34aea4fa41551a30e30af803` | Node.js 24 |
| `actions/setup-python` | v6.3.0 | `ece7cb06caefa5fff74198d8649806c4678c61a1` | Node.js 24 |
| `actions/setup-node` | v7.0.0 | `820762786026740c76f36085b0efc47a31fe5020` | Node.js 24 |
| `actions/upload-artifact` | v6.0.0 | `b7c566a772e6b6bfb58ed0dc250532a479d7789f` | Node.js 24 |
| `actions/download-artifact` | v7.0.0 | `37930b1c2abaa49bbe596cd826c3c89aef350131` | Node.js 24 |

提交来自各 action 官方 Git 仓库对应标签，运行时来自该提交的 `action.yml`。后续升级必须重新核对并以新 CI 证据替代此基线。

## 备选方案

- 继续引用可变主版本标签：维护简单，但不能保证同一提交重复执行同一 action 代码，因此拒绝。
- 只升级 artifact action：可以消除当前警告，但无法阻止其他 action 回退为可变引用，因此拒绝。
- 禁止自动更新：短期稳定，但容易再次积累运行时弃用和安全修复欠账，因此拒绝。
- 直接自动合并 Dependabot PR：减少人工操作，但 action 可能改变缓存、凭据、制品或权限语义，风险超过收益，因此拒绝。

## 兼容性与边界

- 完整 SHA 降低标签漂移风险，但不能替代上游仓库信任、GitHub 平台安全或升级审阅。
- 最低主版本是项目当前验证的通用 CI 规则，不针对业务问题；新增 action 默认仍须完整 SHA 和版本注释，但只有进入最低代际表后才检查其 Node.js 运行时。
- 校验器不联网证明 SHA 与注释版本一致；对应关系由 Dependabot 更新和人工升级评审保证，远程 CI 证明所选提交能执行本项目工作流。
- 本决策不改变 Python、npm、容器或知识资产的既有依赖锁策略。

## 验收条件

- 生效 workflow 中不存在可变外部 action 引用。
- artifact 生产与跨平台消费使用 Node.js 24 代际并通过真实远程矩阵。
- 本地校验器覆盖可变引用、缺失注释、旧运行时、本地 action 和容器 action。
- Dependabot 能识别 GitHub Actions 生态并按周提出受控更新。
- 文档、专项测试、全量工程门禁和远程 CI 证据齐全。
