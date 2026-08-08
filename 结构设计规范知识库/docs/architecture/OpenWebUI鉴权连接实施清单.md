# OpenWebUI 鉴权连接实施清单

> 状态：实施中
> 维护角色：工程与运维负责人
> 文档更新：2026-08-09
> 代码/流程核对：2026-08-09，连接探针、Compose 启动依赖和本地隔离进程矩阵已完成
> 完整运行验证：部分完成，本地 10 项探针测试和 Compose 配置解析通过；真实 OpenWebUI 联调等待远程 CI
> 验证证据：[ADR 0014](../adr/0014-OpenWebUI连接采用环境托管与启动探测.md)
> 复核周期：每个实施项完成时及迭代收口时
> 迭代编号：I-021
> 完成规则：每项只有在实现、测试或运行证据存在后才可标记完成

## 决策与契约

- [x] 定位漏填 Key 导致 API 启动而 OpenWebUI 401 的部分启动缺口（证据：[ADR 0014](../adr/0014-OpenWebUI连接采用环境托管与启动探测.md)）。
- [x] 核对 v0.9.5 连接变量与 `PersistentConfig` 优先级，确定标准部署采用环境托管模式（证据：[ADR 0014](../adr/0014-OpenWebUI连接采用环境托管与启动探测.md)）。
- [x] 定义探针成功、鉴权关闭、Key 缺失/错配、目标未鉴权和传输失败的机器可读语义（证据：`src/app/core/openwebui_probe.py`、`tests/test_openwebui_probe.py`）。

## 实现

- [x] 实现不泄露秘密的 OpenWebUI 连接探针，覆盖静态凭据关系和真实 HTTP 鉴权链路（证据：`src/app/core/openwebui_probe.py`）。
- [x] Compose 使用复数连接变量和环境托管配置，新增一次性 preflight 服务（证据：`docker-compose.yml`）。
- [x] OpenWebUI 等待 API 健康与 preflight 成功，失败时不进入部分启动状态（证据：`docker-compose.yml`、`tests/test_delivery_contract.py`）。
- [x] 提供 Key 轮换、旧持久化连接迁移和故障诊断步骤（证据：[部署运行手册](../operations/部署运行手册.md)第 4.1、4.2 和 8 节）。

## 自动化验证

- [x] 单元测试覆盖 URL 规范化、环境解析、状态码、响应结构和秘密脱敏（证据：`tests/test_openwebui_probe.py`，10 项测试通过）。
- [x] 隔离 API 进程矩阵覆盖鉴权关闭、正确 Key、缺失 Key、错配 Key 和目标鉴权状态不符（证据：`tests/test_openwebui_probe.py`）。
- [x] Compose 契约测试覆盖镜像固定、复数变量、环境托管、preflight 依赖和持久卷（证据：`tests/test_delivery_contract.py`）。
- [ ] 远程 CI 使用合成 Key 启动真实 OpenWebUI，并通过其模型接口发现 `mimo-v2-omni`。
- [x] 全量后端测试通过（证据：2026-08-09 本地 `318 passed, 1 skipped`）。
- [x] 前端组件测试、类型检查、安全审计和生产构建通过（证据：npm 10.9.8 干净安装后 9 项组件测试、`vue-tsc`、零漏洞审计与 Vite 构建通过）。
- [ ] 远程 CI 全部任务通过并记录运行链接。

## 收口

- [ ] 更新系统详细设计、部署运行手册、配置参考、发布检查单、路线图和文档中心。
- [ ] 生成 I-021 验证记录，列出提交、进程矩阵、Compose 证据、远程 CI 和能力边界。
- [ ] 证据齐全后将本清单和路线图状态改为“已完成”。
