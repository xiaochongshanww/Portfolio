# DeepSeek Harness 结构规范知识库插件

这是一个只读的 DeepSeek Harness Bundle。它不包含 PDF、向量库或任何密钥，只通过 HTTP 调用本项目的 FastAPI 服务。

## 提供的工具

- `structural_kb_ready`：检查知识库是否就绪。
- `search_structural_specs`：检索正文、正文表格、条文和结构化表格结果。
- `get_structural_spec_page`：获取指定来源 PDF 页面的受控证据地址。

## 配置

Bundle 默认调用 `http://127.0.0.1:8000`。可以在 Profile 的 `cordis.patch.yml` 中修改 `baseUrl`。鉴权 Key 不写入配置文件，默认从环境变量 `STRUCTURAL_KB_API_KEY` 读取；该值必须属于本项目 `API_KEYS`。

## 本地安装

在 DeepSeek Harness 源码目录执行：

```powershell
pnpm dsh plugin --profile structural-kb add "F:\my_github_repo\Portfolio\结构设计规范知识库\integrations\deepseek-harness\dsh-structural-kb"
```

启动 Harness 前先启动本项目 API：

```powershell
$env:STRUCTURAL_KB_API_KEY = "<本项目 API_KEYS 中的一项>"
pnpm dsh --profile structural-kb web --no-open
```

Harness 运行后，可以要求 Agent 查询结构设计规范。插件只开放检索和证据读取，不开放重建、审核、批准、删除或其他管理操作。
