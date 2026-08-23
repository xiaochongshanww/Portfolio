# DeepSeek Harness 插件运行手册

> 状态：生效
> 维护角色：工程负责人
> 文档更新：2026-08-22
> 完整运行验证：已完成 Windows 本地隔离 Profile 的安装、Harness Web 启动和真实 API 检索调用
> 验证证据：`integrations/deepseek-harness/dsh-structural-kb/README.md`、`docs/architecture/DeepSeek Harness插件集成设计.md`、Harness `--dump-config` 和插件清单
> 复核周期：每次 Harness 版本、插件版本或 API 配置变更
> 代码/流程核对：2026-08-22，命令和端口以当前本地验证为准

## 前置条件

1. 先按[部署运行手册](部署运行手册.md)启动本项目 API，并确认 `GET /ready` 为 200。
2. API 必须允许本机访问集成接口；启用鉴权时准备一个属于 `API_KEYS` 的 Key。
3. 安装 Node.js 22.19 或更高版本、pnpm 11，并准备 DeepSeek Harness 源码目录。
4. 当前插件默认访问 `http://127.0.0.1:8000`；跨机器运行时需要在 Bundle 配置中改成实际 API 地址，并额外配置网络访问控制。

## 安装到隔离 Profile

在 Harness 源码根目录执行。`DSH_HOME` 只是示例隔离目录，可替换为自己的 Harness 配置目录：

```powershell
$env:DSH_HOME = "F:\my_github_repo\Portfolio\deepseek-harness-test-home"
pnpm install --frozen-lockfile
pnpm run build
pnpm dsh plugin --profile web add "F:\my_github_repo\Portfolio\结构设计规范知识库\integrations\deepseek-harness\dsh-structural-kb"
```

验证配置层已被合成：

```powershell
pnpm dsh --profile web --dump-config
```

输出中应出现 `# == dsh-structural-kb` 以及 `structural-kb` 配置行。

## 启动并检查

不要把真实 Key 写进命令行参数、Profile 文件或 Git。启动前通过当前终端环境注入：

```powershell
$env:STRUCTURAL_KB_API_KEY = "<API_KEYS 中的一项>"
pnpm dsh web --no-open --port 3180
```

浏览器打开 `http://127.0.0.1:3180`，进入“设置 -> 插件 -> 插件列表”，确认 `structural-kb` 显示“已挂载、已启用”。

## API 级验证

插件工具直接对应以下后端接口：

```powershell
$headers = @{ Authorization = "Bearer $env:STRUCTURAL_KB_API_KEY" }
Invoke-WebRequest -UseBasicParsing -Headers $headers `
  http://127.0.0.1:8000/integrations/deepseek-harness/ready

$body = @{ query = "办公楼楼面活荷载标准值"; mode = "table"; top_k = 3 } |
  ConvertTo-Json
Invoke-WebRequest -UseBasicParsing -Method Post -Headers $headers `
  -ContentType "application/json" -Body $body `
  http://127.0.0.1:8000/integrations/deepseek-harness/search
```

成功响应应包含 `data_version_hash` 和 `results`；表格问题应优先检查 `source_kind=structured_table`、`section_type=body_table`、`table_id`、`pages` 和 `excerpt`。

## 常见问题

| 现象 | 处理 |
| --- | --- |
| Harness 启动时报前端 dist 缺失 | 在 Harness 根目录先执行 `pnpm run build` |
| 插件未出现在配置层 | 重新执行 `pnpm dsh plugin --profile web add <插件目录>`，检查 Profile 的 `package.json` 是否包含依赖 |
| 插件显示已挂载但工具请求 401 | 检查 `STRUCTURAL_KB_API_KEY` 是否属于 API 服务的 `API_KEYS`，并重启 Harness |
| 工具返回 503 | 检查项目 API 的 `/ready`、活动知识版本和 Python 运行环境；不要把 503 当作无答案 |
| 页面证据返回 403 | 检查来源登记策略、`PUBLIC_ASSET_BASE_URL` 和页面资产访问配置；不要绕过服务端策略 |
| Web 端能打开但无法回答 | Harness 仍需要配置可用的 LLM Provider；插件本身不提供模型密钥或模型服务 |

## 卸载

只从 Profile 移除插件，不删除知识库数据：

```powershell
pnpm dsh plugin --profile web remove dsh-structural-kb
```

卸载后重新执行 `pnpm dsh --profile web --dump-config`，确认配置层不再包含 `structural-kb`。
