# 测试客户端 HTTPX2 迁移实施清单

> 状态：实施中
> 维护角色：工程负责人
> 文档更新：2026-08-12
> 代码/流程核对：2026-08-12，Starlette TestClient 的依赖边界与弃用失败语义已确定
> 完整运行验证：本地 595 项后端测试、17 项前端测试及完整工程门禁通过；远程 CI 待执行
> 验证证据：[验证记录](../releases/测试客户端HTTPX2迁移验证记录.md)、`requirements-dev.in`、`pyproject.toml`、`tests/test_testclient_dependency.py`
> 复核周期：每项完成后更新；Starlette、FastAPI、HTTPX 或 HTTPX2 主版本变化时复核

## 背景

当前锁定的 Starlette 1.4.1 在 `starlette.testclient` 中优先使用 HTTPX2；开发环境未安装 HTTPX2 时会回退到旧 HTTPX，并产生 `StarletteDeprecationWarning`。完整测试虽通过，但该回退已不再是受支持的长期路径。运行时代码仍直接使用 HTTPX 调用模型与评估 API，本轮不能把两种依赖职责混为一谈。

## 目标

让 FastAPI/Starlette TestClient 显式使用 HTTPX2，同时保持生产运行时 HTTPX 客户端不变。依赖必须进入可复现开发锁，且一旦环境再次回退到旧 HTTPX，测试应立即失败而不是只输出可忽略警告。

## 实施清单

- [x] 1. 明确依赖与兼容边界
  - HTTPX2 只作为开发/测试直接依赖，不进入运行或 PDF 解析直接依赖。
  - 运行时代码继续使用现有 HTTPX，不在本轮迁移外部供应商客户端。
  - Starlette 的旧 HTTPX 回退警告升级为测试错误。

- [x] 2. 建立测试先行的依赖契约
  - 检查开发输入声明 HTTPX2 主版本范围，并验证运行与解析输入没有重复声明。
  - 检查 pytest 固定拒绝 `StarletteDeprecationWarning`。
  - 检查测试环境实际可导入 HTTPX2。

- [x] 3. 更新可复现依赖锁
  - 更新 `requirements-dev.in` 并使用固定 `uv` 与既有时间截点重建三份锁。
  - 验证只有开发锁新增测试客户端依赖闭包，运行与解析锁无无关漂移。
  - 用开发锁安装后的环境复验 TestClient 不再产生弃用警告。

- [ ] 4. 完成工程闭环
  - 后端完整测试在弃用警告升级为错误后通过。
  - 静态质量、依赖锁、前端、容器、配置与契约门禁通过。
  - 形成验证记录；提交、推送并通过远程十项 CI 后才标记完成。
  - 本地完整门禁与验证记录已完成；远程 CI 待执行。

## 边界

- 本轮不把运行时 HTTPX 请求迁移为 HTTPX2；两者可在开发环境并存。
- 本轮不放宽任何警告、不添加全局忽略，也不依赖开发者机器上的隐式包。
- 本轮不借依赖调整升级其他直接依赖，锁差异必须可解释。
