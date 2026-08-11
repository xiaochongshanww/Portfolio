# 管理 API 与前端类型契约规范

> 状态：生效
> 维护角色：工程负责人
> 文档更新：2026-08-12
> 代码核对：2026-08-12（44 个管理操作、快照、生成类型/客户端/SDK 与隔离 ASGI 场景已核对）
> 完整运行验证：I-040 本地 583 项后端测试、14 项前端测试、工程门禁与真实浏览器验证通过；远程证据待补
> 验证证据：[I-038 验证记录](../releases/管理API与前端类型契约验证记录.md)、[I-039 验证记录](../releases/管理API运行时契约覆盖验证记录.md)、[I-040 验证记录](../releases/管理API前端生成客户端验证记录.md)、[ADR 0028](../adr/0028-管理API采用响应模型与生成类型契约.md)、[ADR 0029](../adr/0029-管理API采用清单驱动的运行时契约测试.md)、[ADR 0030](../adr/0030-前端管理调用采用OpenAPI生成客户端.md)
> 复核周期：管理 API、OpenAPI 或前端生成器变化时

## 1. 权威来源

FastAPI 路由、请求模型和响应模型是接口语义的权威来源。提交到仓库的 OpenAPI JSON 是该来源的确定性快照，生成的 TypeScript 声明只能由快照产生。三者不得独立手工维护。

## 2. 响应边界

- JSON 操作的 HTTP 200 响应必须引用具名 schema，不能是空对象。
- 稳定顶层字段必须显式建模并标记实际必需性。
- 默认响应禁止未建模顶层字段。只有 `ManifestResponse`、`CandidateDetailResponse`、`ManualDetailResponse`、`ManualDraftResponse`、`StructuringSuggestionResponse`、`ApprovedCorrectionsResponse` 和 `ElementResponse` 七个原始载荷边界允许顶层扩展。
- 评估报告、任务输出、manifest 文档项、候选项和解析元素集合等动态对象应优先位于具名属性内，并以 `unknown`/JSON 对象表达。
- 二进制页面响应使用 `image/png`；错误仍使用 FastAPI 标准 JSON 错误结构。

## 3. 生成与校验

生成流程必须可在干净 Windows/Linux 开发环境重复执行，输出采用 UTF-8、LF 和确定性排序。只读校验比较规范化内容，不因绝对路径、时间、运行数据或环境密钥产生差异。

前端生成文件包含“禁止手工编辑”的来源说明。CI 重新导出和生成后执行 Git 差异检查，未提交契约变化直接失败。

权威文件与命令如下：

| 环节 | 文件或命令 | 约束 |
| --- | --- | --- |
| 后端模型 | `src/app/schemas/admin.py`、`src/app/api/admin.py` | 路由必须声明实际响应模型或二进制媒体类型 |
| 导出并写入 | `python scripts/export_openapi.py --write` | 原子写入 `frontend/openapi.json` |
| 只读校验 | `python scripts/export_openapi.py` | 快照缺失、漂移、空 JSON schema、重复 operation id 或页面媒体类型错误时失败 |
| 生成前端契约 | `cd frontend && npm run api:generate` | 使用精确锁定的 `@hey-api/openapi-ts`，输出类型、Fetch client 与逐操作 SDK 到 `src/generated/api/` |
| 校验生成结果 | `cd frontend && npm run api:check` | 重生成后检查 Git 索引差异与未跟踪生成文件，并拒绝旧管理包装器和运行时 `/admin` URL 字面量；CI 必须在干净检出中执行 |
| 管理操作适配 | `frontend/src/admin-api.ts` | 只重导出生成操作的语义别名；不得重新声明方法、路径、请求体或响应类型 |
| 共享运行边界 | `frontend/src/api.ts` | 配置同源基址、API Key、统一错误、401 事件和二进制对象 URL；非管理调用继续使用专用实现 |
| 展示视图类型 | `frontend/src/contracts.ts` | 只保留生成类型重导出与控制台只读视图，不承担管理路径映射 |

快照只能在 `requirements-runtime.txt` 锁定的 `fastapi`、`pydantic` 与 `pydantic-core` 版本下生成。导出器会在构建文档前核对三者，环境不一致时失败关闭；开发者应先安装哈希锁依赖，不能用全局环境覆盖快照。

正常变更顺序是：修改后端模型与路由、写入 OpenAPI 快照、生成 TypeScript、审阅契约差异、运行后端与前端门禁、提交全部生成文件。不能只修改生成文件，也不能用 `any` 或宽泛类型断言绕开失败。

## 4. 运行时契约覆盖

`tests/test_admin_runtime_contract.py` 维护管理操作的隔离 ASGI 成功场景。场景清单以 OpenAPI operation id 为键，并同时登记方法、模板路径、实际请求路径、请求正文和预期媒体类型。

运行时门禁必须满足以下不变量：

- OpenAPI 中每个 `/admin` 操作恰好有一个场景，不允许遗漏、重复或登记不存在的操作。
- 场景方法、模板路径和媒体类型必须与当前 OpenAPI 一致。
- 每个场景必须返回 HTTP 200；JSON 结果通过对应 Pydantic 响应模型，PNG 结果具有 `image/png` 和 PNG 文件签名。
- 文件读写只发生在 pytest 临时目录；任务提交、检索加载、模型、解析器和外部网络使用确定性替身。
- 代表数据不能全部为空，任务、版本、评估、校对、结构化和元素边界至少具有一个非空样例。
- 严格响应缺少必需字段或携带未声明字段时，外部可见结果必须失败关闭为 HTTP 500，而不是返回部分成功载荷。

该门禁证明代表状态下的传输一致性，不证明所有生产数据组合、业务状态转换或内容质量正确。完整决策见 [ADR 0029](../adr/0029-管理API采用清单驱动的运行时契约测试.md)。

## 5. 前端使用

管理组件必须调用 `admin-api.ts` 暴露的生成操作别名，并以结构化 `path`、`query`、`body` 传参。组件和通用执行器不得拼接 `/admin` URL，也不得恢复 `AdminGetPath` 等条件类型。API Key 与候选 Key 优先级、401 鉴权事件、JSON/文本错误转换和 Blob 页面截图统一由生成 client 拦截器及共享适配器处理。

JSON 请求函数不提供 `any` 默认类型。真正开放的 JSON 值使用 `unknown` 或生成的 JSON 类型，并在访问前缩小类型。非管理端健康、指标、知识文档和聊天流式调用不属于本轮迁移边界，可以继续使用各自专用实现。

## 6. 兼容边界

新增可选字段通常向后兼容；删除字段、把必需字段改为可选、修改枚举或类型均应视为需要审阅的接口变化。契约通过不代表业务语义、权限或内容质量通过。

## 7. 失败语义

- 响应模型缺少必需字段时，由 FastAPI 响应校验显式失败，不把不完整载荷交给控制台。
- 快照生成环境与运行依赖锁不一致时，导出器报告实际/锁定框架版本并拒绝生成。
- OpenAPI 与应用不一致时，后端快照校验失败，并提示重新导出；校验模式不修改文件。
- TypeScript 与 OpenAPI 不一致时，生成漂移门禁失败；组件访问不存在或类型不匹配的字段时，`vue-tsc` 失败。
- 七个显式开放响应及报告、草稿内部动态字段仍需在读取点缩小 `unknown`；生成类型只证明传输边界，不证明开放对象内部业务语义。
