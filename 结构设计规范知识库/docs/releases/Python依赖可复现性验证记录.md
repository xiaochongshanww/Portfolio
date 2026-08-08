# Python 依赖可复现性验证记录

> 状态：生效
> 维护角色：工程负责人
> 文档更新：2026-08-08
> 代码/流程核对：2026-08-08
> 完整运行验证：本地完成，远程 Windows/Linux CI 待执行
> 验证证据：`dependency-lock.json`、`scripts/lock_dependencies.py`、`tests/test_delivery_contract.py`
> 复核周期：Python、直接依赖、锁生成器、基础镜像或支持平台变化时

## 验证范围

本记录覆盖路线图 I-008 的 Python 运行锁和开发锁，不将 `requirements.txt` 中的 MinerU、Paddle 或其他重型构建环境依赖表述为已锁定交付。

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

## 待取得的远程证据

1. Ubuntu 与 Windows 均能按哈希安装 `requirements-dev.txt` 并运行全部测试。
2. Ubuntu 使用固定 `uv` 重新解析后，两个锁文件均无漂移。
3. Linux Docker 镜像能按哈希安装运行锁，并通过 API 与控制台冒烟测试。

上述证据全部完成前，路线图 I-008 保持“进行中”。

## 保留限制

1. 通用锁覆盖平台标记，但不保证所有未来 CPU 架构都有可用 wheel；新增架构必须扩展 CI。
2. Python 只固定到 3.11 主次版本，补丁版本由目标环境或基础镜像提供；改变补丁版本仍需重新运行矩阵。
3. `requirements.txt` 是完整知识生产环境的历史直接依赖清单，尚未具备同等级哈希锁。
4. 上游包即使哈希固定，仍需在升级评审中检查许可证、安全公告和行为变化。
