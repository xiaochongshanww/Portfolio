# Python 静态质量门禁验证记录

> 状态：已完成
> 维护角色：工程负责人
> 文档更新：2026-08-09
> 代码/流程核对：2026-08-09，配置、依赖锁、零存量迁移、CI 命令和契约测试已核对
> 完整运行验证：本地 400 项后端测试、9 项前端测试及完整工程门禁通过；[CI #74](https://github.com/xiaochongshanww/Portfolio/actions/runs/31293167043) 十项任务全部通过
> 验证证据：[实施清单](../architecture/Python静态质量门禁实施清单.md)、[ADR 0020](../adr/0020-Python代码采用固定Ruff静态质量门禁.md)、提交 `e498a49`、[CI #74](https://github.com/xiaochongshanww/Portfolio/actions/runs/31293167043)
> 复核周期：I-030 收口或 Python/Ruff/CI 规则变化时

## 验证范围

I-030 为 `src`、`scripts`、`tests` 建立固定版本的静态检查与格式门禁。验证目标包括：

1. Ruff 只进入开发精确锁，不扩大运行或 PDF 解析环境；
2. 规则、Python 目标、行宽、行尾和检查目录集中配置且没有全局豁免；
3. Windows/Linux CI 使用与本地相同的 lint 和 format check 命令；
4. 首次迁移清除全部存量问题，行为性修改经过专项和全量测试；
5. 工具链契约可由测试反向校验，防止门禁被静默移除。

## 基线与迁移

首次只读扫描覆盖 133 个既有 Python 文件，在 `E4/E7/E9/F/I/B/UP` 下发现 109 项：80 项导入排序、10 项未显式声明 `zip()` 长度语义、8 项旧导入位置、4 项未使用导入、4 项旧式 `Optional`、2 项冗余 UTF-8 编码参数和 1 项旧式泛型。

迁移采用 Ruff 安全修复、人工语义判断和统一格式器三步完成：

- 4 个未使用导入被移除，类型、集合抽象和 UTC 写法按 Python 3.11 等价现代化；
- 10 处 `zip()` 全部使用 `strict=True`，因为 Chroma 的 ID/文档/元数据、向量 ID/距离、评估用例/结果均要求一一对应；新增评估数量不一致测试证明损坏状态会失败而非静默截断；
- 116 个文件经格式器迁移，`.gitattributes` 将 134 个当前 Python 文件统一为 LF；最终没有文件删除，也没有项目级 `ignore` 或 `per-file-ignores`。

## 本地验证

| 门禁 | 结果 |
| --- | --- |
| Ruff lint | `All checks passed` |
| Ruff format | 134 个文件均已格式化 |
| 后端与文档 | `400 passed, 1 skipped`；唯一跳过为既有平台条件项 |
| 前端 | 2 个测试文件、9 项测试通过；`vue-tsc --noEmit` 通过 |
| npm 安全与构建 | high 级审计 0 漏洞；Vite 生产构建通过 |
| Python 精确锁 | runtime、development、parser 三份锁无漂移；只有 development 新增 Ruff |
| 配置与 Compose | 46 个键、6 个空敏感键、真实配置预检及 Compose 渲染通过 |
| 质量证据 | 脱敏快照与历史索引一致；`release_quality_status=not_passed` 保持真实状态 |
| CI Action | 14 个外部引用均为完整 SHA 且满足最低运行时代际 |
| 差异与行尾 | `git diff --check` 通过；134 个 Python 文件均为 LF |

## 远程验证

[CI #74](https://github.com/xiaochongshanww/Portfolio/actions/runs/31293167043) 对实现提交 `e498a49` 执行了完整矩阵，十项任务全部为 `success`：

| 任务组 | 结果 |
| --- | --- |
| 依赖与后端 | Dependency lock、Windows 后端、Linux 后端通过；两个后端均执行 Ruff lint、format check 和 400 项测试 |
| 前端与容器 | 前端测试/类型/审计/构建、API 容器冒烟通过 |
| OpenWebUI | 受保护连接真实集成通过 |
| 知识包 | Windows/Linux 两个平台产包及 Linux→Windows、Windows→Linux 两条消费链通过 |

远程任务不会注入真实模型凭据，也不改变当前质量证据的 `release_quality_status=not_passed`。

## 当前结论

- [x] 固定工具版本、集中配置和零存量迁移已完成。
- [x] 本地静态、后端、前端、锁、配置、Compose、证据和供应链门禁已通过。
- [x] 远程完整矩阵通过并记录不可变运行链接。
- [x] 远程证据完成后同步实施清单、ADR、路线图和生效文档状态。
