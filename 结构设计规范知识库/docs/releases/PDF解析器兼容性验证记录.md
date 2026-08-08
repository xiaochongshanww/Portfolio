# PDF 解析器兼容性验证记录

> 状态：生效
> 维护角色：工程负责人  
> 文档更新：2026-08-08  
> 代码/流程核对：2026-08-08  
> 完整运行验证：本地代码、锁、真实 CLI 和前端门禁通过；远程 CI #34 的 9 个任务全部成功
> 验证证据：`tests/test_mineru_compatibility.py`、`requirements-parser.txt`、[Structural Spec KB CI #34](https://github.com/xiaochongshanww/Portfolio/actions/runs/31259467233)
> 复核周期：解析器实现、版本、依赖锁、支持平台或输出 schema 变化时  
> 关联路线图：I-017  
> 关联决策：[ADR 0010](../adr/0010-PDF解析器采用显式兼容契约.md)

## 结论边界

本轮验证“重建能否在写入前识别并阻断未经验证的外部解析器”，以及知识生产依赖是否形成独立可复现锁。它不执行真实扫描 PDF 全量 OCR，不宣布 MinerU 2.x/3.x 兼容，也不重新证明当前活动知识库的回答质量。

当前活动六份规范的产物索引均记录 `magic-pdf, version 1.3.12`。因此支持矩阵暂时只有这一项；项目后端名 `mineru` 只是内部稳定标识。上游当前安装与 CLI 形态已变化，升级必须走隔离迁移和质量评估，不能由无版本依赖自动进入生产。

## 实现证据

| 断言 | 证据 |
| --- | --- |
| 默认失败关闭 | `strict` 拒绝 CLI 缺失、超时、非零退出、无法识别版本和 `mineru 3.4.4` |
| 写入前阻断 | 构建预检先于 `clean_generated_outputs`；单文档探测先于原产物目录删除 |
| 受控试验 | `allow-unverified` 仅放行可识别版本，并保留 warning、policy、compatibility 与 verified=false |
| 可审计构建 | 根 manifest 的 `build_params.parser_environment` 与单文档 `artifacts.json.metadata.parser_cli` 记录实际证据 |
| 环境隔离 | 运行、开发、知识生产分别使用三个输入和哈希锁；API 镜像仍只安装运行锁 |
| 依赖兼容 | 知识生产锁选择 `magic-pdf 1.3.12` 要求的 `PyMuPDF 1.24.14`，不把运行锁的 `1.28.2` 强行混入 |

## 本地验证

真实已安装 CLI 探测：

```text
python -m src.pipeline parser-status
implementation: magic-pdf
version: 1.3.12
policy: strict
compatibility: verified
verified: true
```

自动化门禁：

```text
python -m pytest -q
253 passed, 6 warnings

python scripts/lock_dependencies.py --check
ok: requirements-runtime.txt
ok: requirements-dev.txt
ok: requirements-parser.txt

npm test
Test Files 1 passed; Tests 6 passed
npm run typecheck
success
npm audit --audit-level=high
found 0 vulnerabilities
npm run build
success

python -m src.app.core.config
configuration: ok
docker compose config -q
success
```

本机 Docker Desktop Linux engine 未运行，因此本地 `docker build` 未执行成功；容器门禁由远程 CI 补齐。本轮曾启动隔离 API 尝试完整知识质量脚本，结构化 12 项通过，但常规评估因检索服务未就绪、回答评估因既有默认端口回连失败而未通过。该结果不计作 I-017 通过证据，也不归因于解析器代码；后续应单独修复质量验证器的端口传递与就绪诊断。

## 依赖与许可证边界

`requirements-parser.txt` 固定 `magic-pdf[full]==1.3.12` 的完整解析环境并携带分发包 SHA-256。锁文件约 335 KiB，只用于知识生产主机，不进入运行镜像。包元数据声明 AGPL-3.0；技术验证不替代开源许可证、模型权重许可、原始 PDF 权利或商业服务合规评审。

参考上游：[magic-pdf PyPI](https://pypi.org/project/magic-pdf/)、[MinerU Quick Start](https://opendatalab.github.io/MinerU/quick_start/)、[MinerU CLI 文档](https://github.com/opendatalab/MinerU/blob/master/docs/en/usage/cli_tools.md)。

## 远程证据

CI #34 在提交 `0566cd7` 上完成 9 个任务：

| 任务 | 结果 | 证明范围 |
| --- | --- | --- |
| Dependency lock | success | Linux 从空目录重新生成运行、开发和知识生产三份锁，无漂移 |
| Backend tests（Ubuntu/Windows） | success | 两个平台按开发哈希锁安装并各通过 253 项测试 |
| Frontend tests and build | success | 组件测试、类型检查、安全审计和生产构建通过 |
| Container smoke test | success | Linux 运行镜像构建、API 健康检查和静态控制台通过，未安装重型解析器 |
| Package producer（Ubuntu/Windows） | success | 两个平台真实 Chroma 产包与 A→B→A 恢复探针通过 |
| Package portability（双向） | success | Windows→Linux、Linux→Windows 的包校验、Chroma 探测和 API 冷启动通过 |

上述证据关闭 I-017 的工程兼容目标。真实扫描 PDF 的全量 OCR 性能、解析器新主版本迁移和在线回答质量仍按各自质量流程独立验证。
