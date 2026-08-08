# Python 依赖可复现性验证记录

> 状态：生效
> 维护角色：工程负责人
> 文档更新：2026-08-08
> 代码/流程核对：2026-08-08
> 完整运行验证：本地与远程 Windows/Linux/Docker 均完成
> 验证证据：提交 `298f10e`、跨平台修复提交 `003edce`、`dependency-lock.json`、`scripts/lock_dependencies.py`、`tests/test_delivery_contract.py`、[Structural Spec KB CI #14](https://github.com/xiaochongshanww/Portfolio/actions/runs/31247350564)
> 复核周期：Python、直接依赖、锁生成器、基础镜像或支持平台变化时

## 验证范围

本记录覆盖路线图 I-008 的 Python 运行锁和开发锁。后续 I-017 已将当时尚未锁定的重型 PDF 知识生产环境拆分到 `requirements-parser.txt`；其兼容结论和验证证据以 [PDF 解析器兼容性实施清单](../architecture/PDF解析器兼容性实施清单.md) 为准。

## 锁契约

| 项目 | 当前规则 |
| --- | --- |
| 直接依赖 | 只在 `requirements-runtime.in` 和 `requirements-dev.in` 维护 |
| 解析环境 | Python 3.11、`uv==0.12.3` |
| 时间边界 | 只选择 `2026-08-08T00:00:00Z` 之前发布的候选 |
| 平台范围 | `--universal` 生成 Windows/Linux 等平台共用锁 |
| 完整性 | 每个锁定分发包都记录 SHA-256，安装强制 `--require-hashes` |
| 漂移检查 | 在空临时目录重新解析并逐字比较，不受现有输出文件偏好影响 |
| 升级语义 | 生成显式使用 `--upgrade`，确保 `--write` 与 `--check` 选择一致 |

## 本地证据

```text
python scripts/lock_dependencies.py --write
updated: requirements-runtime.txt
updated: requirements-dev.txt

python scripts/lock_dependencies.py --check
ok: requirements-runtime.txt
ok: requirements-dev.txt

python -m pip install --require-hashes -r requirements-runtime.txt
Successfully installed 87 packages

python -c "import fastapi, chromadb, fitz, zhipuai, rank_bm25"
clean-install-imports: ok
python: 3.11.3
fastapi: 0.141.1
chromadb: 1.5.9

python -m pytest tests/test_delivery_contract.py -q
5 passed
```

上述安装在新建的 Windows 虚拟环境中执行，未复用项目现有 site-packages；安装器为标准 `pip`，所有分发包均按锁内 SHA-256 校验。

## 远程证据

CI #14 在提交 `003edce` 上完成以下验证：

| Job | 结果 | 证明范围 |
| --- | --- | --- |
| Dependency lock | success | Ubuntu 使用 `uv==0.12.3` 从空临时目录重新解析，两份锁文件无漂移 |
| Backend tests (ubuntu-latest) | success | Linux 按哈希安装开发锁，191 项测试通过 |
| Backend tests (windows-latest) | success | Windows 按同一份哈希锁安装开发依赖，191 项测试通过 |
| Frontend build | success | 前端生产构建未受交付契约变化影响 |
| Container smoke test | success | Linux Docker 按哈希安装运行锁，API 健康检查与控制台静态页通过 |

CI #13 首次引入矩阵时，Windows 已完成哈希安装，但进程级配置预检测试受终端中文转义影响而失败。提交 `003edce` 将预检输出改为 ASCII 安全 JSON 后，CI #14 复验通过；该过程证明失败来自跨平台输出契约，而非锁文件缺少 Windows 分发包。

## 保留限制

1. 通用锁覆盖平台标记，但不保证所有未来 CPU 架构都有可用 wheel；新增架构必须扩展 CI。
2. Python 只固定到 3.11 主次版本，补丁版本由目标环境或基础镜像提供；改变补丁版本仍需重新运行矩阵。
3. I-008 当时未覆盖知识生产环境；该历史限制由 I-017 的独立输入、哈希锁和解析器兼容契约承接，不能反向扩大 I-008 的验证范围。
4. 上游包即使哈希固定，仍需在升级评审中检查许可证、安全公告和行为变化。
