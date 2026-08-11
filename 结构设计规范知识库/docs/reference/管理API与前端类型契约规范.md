# 管理 API 与前端类型契约规范

> 状态：生效
> 维护角色：工程负责人
> 文档更新：2026-08-12
> 代码核对：2026-08-12（44 个管理操作、快照导出与前端生成链已核对）
> 完整运行验证：I-038 本地 533 项后端测试与完整前端/工程门禁通过；远程 CI 待完成
> 验证证据：[实施清单](../architecture/管理API与前端类型契约实施清单.md)、[验证记录](../releases/管理API与前端类型契约验证记录.md)、[ADR 0028](../adr/0028-管理API采用响应模型与生成类型契约.md)
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
| 生成前端类型 | `cd frontend && npm run api:generate` | 使用精确锁定的 `@hey-api/openapi-ts`，输出到 `src/generated/api/` |
| 校验生成结果 | `cd frontend && npm run api:check` | 重生成后检查工作树差异和未跟踪生成文件；CI 必须在干净检出中执行 |
| 前端适配边界 | `frontend/src/contracts.ts` | 将 OpenAPI 路径映射为管理请求帮助函数和必要的只读视图类型 |

快照只能在 `requirements-runtime.txt` 锁定的 `fastapi`、`pydantic` 与 `pydantic-core` 版本下生成。导出器会在构建文档前核对三者，环境不一致时失败关闭；开发者应先安装哈希锁依赖，不能用全局环境覆盖快照。

正常变更顺序是：修改后端模型与路由、写入 OpenAPI 快照、生成 TypeScript、审阅契约差异、运行后端与前端门禁、提交全部生成文件。不能只修改生成文件，也不能用 `any` 或宽泛类型断言绕开失败。

## 4. 前端使用

JSON 请求函数不提供 `any` 默认类型。组件必须从生成契约导入对应操作的请求/响应类型；真正开放的 JSON 值使用 `unknown` 或生成的 JSON 类型，并在访问前缩小类型。

## 5. 兼容边界

新增可选字段通常向后兼容；删除字段、把必需字段改为可选、修改枚举或类型均应视为需要审阅的接口变化。契约通过不代表业务语义、权限或内容质量通过。

## 6. 失败语义

- 响应模型缺少必需字段时，由 FastAPI 响应校验显式失败，不把不完整载荷交给控制台。
- 快照生成环境与运行依赖锁不一致时，导出器报告实际/锁定框架版本并拒绝生成。
- OpenAPI 与应用不一致时，后端快照校验失败，并提示重新导出；校验模式不修改文件。
- TypeScript 与 OpenAPI 不一致时，生成漂移门禁失败；组件访问不存在或类型不匹配的字段时，`vue-tsc` 失败。
- 七个显式开放响应及报告、草稿内部动态字段仍需在读取点缩小 `unknown`；生成类型只证明传输边界，不证明开放对象内部业务语义。
