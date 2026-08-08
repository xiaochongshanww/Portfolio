# OpenWebUI 鉴权连接验证记录

> 状态：生效
> 维护角色：工程与运维负责人
> 文档更新：2026-08-09
> 代码/流程核对：2026-08-09，I-021 连接探针、Compose 启动依赖、真实容器会话和文档均已核对
> 完整运行验证：2026-08-09，CI #46 的十个任务全部通过
> 验证证据：[实施清单](../architecture/OpenWebUI鉴权连接实施清单.md)、[ADR 0014](../adr/0014-OpenWebUI连接采用环境托管与启动探测.md)、[Structural Spec KB CI #46](https://github.com/xiaochongshanww/Portfolio/actions/runs/31268469521)
> 复核周期：API 鉴权、OpenWebUI 版本、Compose 拓扑、连接变量或持久化配置策略变化时

## 变更记录

- 规划提交：`43bd9ad`，定义环境托管连接、失败关闭、秘密脱敏和真实容器验收边界。
- 实现提交：`ddbd5b7`，增加连接探针、一次性 preflight、Compose 启动依赖、隔离进程矩阵和运维契约。
- CI 构建修正：`82e4c90`，应用镜像只构建一次，preflight 与 API 复用同一显式标签，避免 Compose 重复 BuildKit 会话。
- 会话验收修正：`9201305`，按 OpenWebUI v0.9.5 的已验证用户约束建立临时会话，再调用 `/api/models`。
- 远程验证：CI #46，依赖锁、Windows/Linux 后端、前端、API 容器、真实 OpenWebUI 和双向知识包兼容共十项全部成功。

## 已验证契约

1. 启用 API 鉴权时，`OPENWEBUI_API_KEY` 必须非空且属于 `API_KEYS`；缺失或错配会在 OpenWebUI 启动前失败。
2. 标准 Compose 只声明 `http://api:8000/v1` 连接，并使用 `OPENAI_API_BASE_URLS`、`OPENAI_API_KEYS` 和 `ENABLE_PERSISTENT_CONFIG=false` 让环境配置成为连接事实来源。
3. `openwebui-preflight` 在 API 健康后验证模型发现、匿名/带 Key 管理请求和 malformed chat 的鉴权顺序，不触发外部模型调用。
4. OpenWebUI 只有在 API 健康且 preflight 以退出码 0 完成后启动；部分可用状态不能越过 Compose 依赖。
5. 探针输出只包含模型标识、状态码、Key 数量和凭据来源名称，不包含 Key 原值。
6. OpenWebUI v0.9.5 的 `/api/models` 依赖已验证用户，即使 `WEBUI_AUTH=false` 也不能匿名调用；CI 先建立临时管理员会话，再携带 JWT 验证模型发现。

## 本地证据

| 门禁 | 结果 |
| --- | --- |
| OpenWebUI 探针矩阵 | 11 项测试，覆盖鉴权开关、正确/缺失/错配 Key、目标状态不符、URL 安全和默认模型 |
| 文档、交付和探针专项 | `26 passed` |
| 后端全量测试 | `318 passed, 1 skipped` |
| 前端组件测试 | 2 个测试文件、9 项测试通过 |
| 前端类型检查 | `vue-tsc --noEmit` 通过 |
| 前端依赖审计 | `npm audit --audit-level=high`，0 个漏洞 |
| 前端生产构建 | Vite 构建通过 |
| 依赖锁 | runtime、dev、parser 三套锁文件一致 |
| Compose 配置 | `docker compose config --quiet` 通过，API 与 preflight 解析为同一应用镜像 |

## 远程真实容器证据

[CI #46](https://github.com/xiaochongshanww/Portfolio/actions/runs/31268469521) 对提交 `9201305` 的十个任务均为 `success`。OpenWebUI 集成任务使用合成 Key 和临时数据卷完成以下断言：

1. 共享应用镜像构建成功，API、preflight 和 OpenWebUI 按 Compose 依赖顺序启动。
2. preflight 退出码为 0，并输出 `"ok": true`、模型 `mimo-v2-omni`、匿名受保护请求 401、带 Key 请求 200/422 和 `external_model_calls: 0`。
3. OpenWebUI `/health` 可访问；无鉴权模式的临时登录返回会话令牌。
4. 携带该令牌请求 OpenWebUI `/api/models`，结果包含 `mimo-v2-omni`，证明 OpenWebUI 已使用受保护后端连接发现模型。
5. 任务结束后 Compose 服务和临时数据卷成功清理。

CI #44 首次暴露 Runner BuildKit 会话头异常，CI #45 在改为单次镜像构建后证明 Compose 可启动，但匿名 `/api/models` 按 v0.9.5 契约返回 401。两次失败均保留为诊断过程，不作为完成证据；CI #46 的会话化验证是最终验收依据。

## 能力边界

- 本验证未调用 MiMo 或智谱外部模型，不证明供应商可用性、回答质量、吞吐量或费用控制。
- `WEBUI_AUTH=false`、默认临时管理员和临时数据卷只存在于隔离 CI；标准部署必须保持 `OPENWEBUI_AUTH=true` 并完成用户、注册和访问策略配置。
- 环境托管模式不迁移 OpenWebUI 内部 SQLite 中的旧 ConfigVar；用户、聊天和上传文件仍由命名卷保存，删除卷属于破坏性操作。
- 本验证不覆盖 TLS、反向代理、SSO/OAuth、邮件、外部域名、浏览器跨域或公网攻击面。
- Key 轮换流程已形成配置与运维契约，但每个真实环境仍须使用其密钥系统执行并保留不含秘密的轮换记录。
