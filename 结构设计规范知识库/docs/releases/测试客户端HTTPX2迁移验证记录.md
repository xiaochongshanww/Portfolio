# 测试客户端 HTTPX2 迁移验证记录

> 状态：本地已验证，远程待验证
> 维护角色：工程负责人
> 文档更新：2026-08-12
> 代码/流程核对：2026-08-12，开发依赖、锁差异、pytest 警告门禁和运行时边界已核对
> 完整运行验证：本地 595 项后端测试、17 项前端测试及完整工程门禁通过；远程 CI 待执行
> 验证证据：[实施清单](../architecture/测试客户端HTTPX2迁移实施清单.md)、`requirements-dev.in`、`requirements-dev.txt`、`pyproject.toml`、`tests/test_testclient_dependency.py`
> 复核周期：I-044 收口或 Starlette、FastAPI、HTTPX、HTTPX2 主版本变化时

## 验证目标

证明 Starlette TestClient 不再依赖已弃用的旧 HTTPX 回退，同时不改变生产运行时使用 HTTPX 调用外部服务的行为。开发环境必须从精确哈希锁获得 HTTPX2，回退警告必须成为测试失败，不能靠本机隐式安装或全局忽略维持绿色。

## 基线与测试先行

锁定的 Starlette 1.4.1 在没有 HTTPX2 时从 `starlette.testclient` 回退到 HTTPX 0.28.1，并在测试收集阶段产生 `StarletteDeprecationWarning`。Starlette 的 [TestClient 文档](https://www.starlette.io/testclient/) 已声明 HTTPX2 是当前后端，旧 HTTPX 仅为弃用兼容路径。

实施前新增三项契约测试并确认全部失败：开发输入缺少 HTTPX2、pytest 未配置该警告为错误、隔离测试环境无法导入 HTTPX2。失败与基线一一对应，随后才修改依赖和配置。

## 依赖结果

- `requirements-dev.in` 新增 `httpx2>=2,<3`，表达测试客户端主版本兼容范围；
- 固定 `uv 0.12.3` 与既有 `exclude_newer` 时间截点重建三份锁，只有 `requirements-dev.txt` 变化；
- 开发锁解析为 HTTPX2 2.9.1、HTTP Core 2 2.9.1 与 Truststore 0.10.4，并保留运行时代码所需的 HTTPX 0.28.1；
- 运行锁与 PDF 解析锁没有 HTTPX2、HTTP Core 2 或 Truststore 漂移；
- `pyproject.toml` 将 `StarletteDeprecationWarning` 升级为错误，未来缺失 HTTPX2 时测试在收集阶段失败。

既有时间截点已经包含所需版本，因此本轮没有抬高依赖解析时间边界，也没有顺带升级其他直接依赖。

## 本地完整门禁

| 门禁 | 结果 |
| --- | --- |
| 测试先行契约 | 实施前 3 项按预期失败；实施后 3 项通过 |
| TestClient 代表路径 | 新契约与可观测性共 12 项通过，无弃用警告 |
| 后端与文档 | 595 项通过，1 项按平台/环境设计跳过；警告汇总为空 |
| Python 静态质量 | Ruff 检查通过；`src scripts tests` 共 161 个文件格式通过 |
| 依赖锁 | 运行、开发、解析三份锁重新解析一致；只有开发锁新增 HTTPX2 闭包 |
| API、配置与质量证据 | OpenAPI 45 个管理操作、`.env.example` 51 个键及质量快照验证通过；发布质量仍为 `not_passed` |
| 前端 | npm 高危审计 0；4 个测试文件共 17 项测试、API 契约、类型检查和生产构建通过 |
| 工程策略 | 18 个外部 Action、4 个外部镜像、容器安全策略和 Compose 渲染通过 |

## 结论边界

本地证据证明 TestClient 已使用 HTTPX2 且弃用回退被自动阻断。远程 CI 通过前 I-044 保持实施中；本轮不迁移生产 HTTPX 调用，不宣称 HTTPX2 已适用于模型供应商或其他运行时请求，也不改变发布质量结论。
