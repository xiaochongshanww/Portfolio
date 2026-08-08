# ADR 0014：OpenWebUI 连接采用环境托管与启动探测

> 状态：已接受
> 维护角色：工程与运维负责人
> 文档更新：2026-08-09
> 代码/流程核对：2026-08-09，已实现连接探针、Compose 启动依赖并通过本地隔离进程矩阵
> 完整运行验证：部分完成，真实 OpenWebUI Compose 联调等待远程 CI
> 验证证据：[实施清单](../architecture/OpenWebUI鉴权连接实施清单.md)
> 复核周期：API 鉴权、Compose 拓扑、OpenWebUI 版本或持久化配置策略变化时
> 决策日期：2026-08-08

## 背景

当前 Compose 把 `OPENWEBUI_API_KEY` 传给 OpenWebUI，并在 API 配置中检查“已提供的 Key 必须属于 `API_KEYS`”。但是该字段缺失时 API-only 服务仍应允许启动，Compose 则会把 OpenWebUI Key 回退为 `not-needed`。当 `API_AUTH_ENABLED=true` 时，这会形成“API 健康、OpenWebUI 稳定 401”的部分启动状态。

另一个风险来自持久化配置。OpenWebUI v0.9.5 将 `OPENAI_API_KEYS` 和 `OPENAI_API_BASE_URLS` 定义为 `PersistentConfig`；默认启用持久化时，数据卷中的旧连接优先于新的环境变量。仅验证 `.env` 中的 Key 匹配，不能证明 OpenWebUI 实际使用了该 Key。

依据：

- [OpenWebUI v0.9.5 配置源码](https://github.com/open-webui/open-webui/blob/v0.9.5/backend/open_webui/config.py#L1033-L1063)定义单数变量向复数变量回退并持久化连接配置；
- [官方环境变量参考](https://docs.openwebui.com/reference/env-configuration/)说明 `OPENAI_API_KEYS`、`OPENAI_API_BASE_URLS` 和 `ENABLE_PERSISTENT_CONFIG` 的语义；
- 当前 API 的 `/v1/models` 为公开发现接口，`/v1/chat/completions` 与 `/admin/*` 受同一 Bearer Key 中间件保护。

## 决策

1. 保持 `OPENWEBUI_API_KEY` 对 API-only 部署可选，不在通用 `Settings` 中强制要求它；OpenWebUI 的必填关系由 Compose 集成层负责。
2. 标准 Compose 使用 OpenWebUI v0.9.5 的复数连接变量 `OPENAI_API_BASE_URLS` 与 `OPENAI_API_KEYS`，只声明一个受控后端连接。
3. 标准 Compose 设置 `ENABLE_PERSISTENT_CONFIG=false`，让连接 URL、Key 和其他声明式配置在每次启动时以环境变量为准。OpenWebUI 用户、聊天和文件数据仍保存在命名卷；管理界面修改的 `ConfigVar` 不承诺跨重启生效。
4. 新增无外部模型调用的连接探针。探针先校验 `API_AUTH_ENABLED`、`API_KEYS` 与 `OPENWEBUI_API_KEY` 的静态关系，再经容器网络检查 `/health`、`/v1/models`、受保护管理接口和 malformed chat 请求的鉴权顺序。
5. Compose 新增一次性 preflight 服务；OpenWebUI 只有在 API 健康且连接探针成功后才能启动。启用鉴权但 Key 缺失、错配或目标未执行鉴权时，部署失败关闭，不进入半可用状态。
6. CI 使用合成 Key、临时数据卷和 `WEBUI_AUTH=false` 启动完整 Compose，调用 OpenWebUI 自身模型接口验证其能通过受保护连接发现 `mimo-v2-omni`。该设置只用于无人值守联调，不改变标准部署的 OpenWebUI 用户鉴权默认值。
7. 探针的 JSON、stdout、stderr 和异常不得包含连接 Key 或 `API_KEYS` 原值。Key 轮换必须同时更新两项、重建相关容器并重新运行同一探针。

## 兼容性

- Compose 管理的 OpenWebUI 配置从“数据卷优先”切换为“环境变量优先”；聊天、账户和上传文件仍持久化，但管理界面中的 ConfigVar 调整应迁移到 Compose 环境变量。
- API-only、直接使用内置 Vue 控制台和其他 OpenAI-compatible 客户端的部署不受 OpenWebUI Key 必填约束。
- `OPENAI_API_KEY` 和 `OPENAI_API_BASE_URL` 不再作为标准 Compose 的主要变量；OpenWebUI v0.9.5 仍保留其上游兼容回退。

## 非目标

- 本决策不实现 OpenWebUI 用户、角色、注册、OAuth/SSO 或外部反向代理的生产安全基线。
- 本决策不调用真实 MiMo/智谱模型，不证明回答质量、外部供应商可用性或公网访问链路。
- 本决策不自动迁移或修改 OpenWebUI 内部 SQLite 配置，不承诺支持 `ENABLE_PERSISTENT_CONFIG=true` 下的数据卷旧连接。
- 本决策不把连接 Key 写入镜像、Git、验证记录或命令行参数。
