# 结构设计规范知识库

本项目是面向结构设计规范的 RAG（检索增强生成）知识库。它将 PDF 规范处理为可追溯的知识资产，结合权威性排序、结构化表检索和 MiMo 模型生成，提供兼容 OpenAI API 的问答接口与管理控制台。

[![Structural Spec KB CI](https://github.com/xiaochongshanww/Portfolio/actions/workflows/structural-spec-kb-ci.yml/badge.svg)](https://github.com/xiaochongshanww/Portfolio/actions/workflows/structural-spec-kb-ci.yml)

## ✨ 功能特性

- **自动化数据处理**: 提供从PDF扫描件到结构化文本的完整自动化处理流水线（OCR、清洗、切分）。
- **智能检索增强**: 利用高质量的文本嵌入模型，精准检索与用户问题最相关的规范条文。
- **来源可追溯回答**: 使用 MiMo OpenAI-compatible API 生成答案，并返回规范、条文/表格、页码和页面截图证据。
- **标准化API**: 提供兼容OpenAI的`/v1/chat/completions`接口，可无缝对接[Chatbox](https://chatbox.app/)、[LobeChat](https://github.com/lobehub/lobe-chat)等多种客户端。
- **流式响应**: 支持打字机效果的流式API响应，提升用户体验。
- **受保护版本生命周期**: 候选版本通过门禁后事务化激活，历史版本可在控制台按限时计划审阅、固定和清理，全程保留审计记录。

## 🚀 架构概览

```
+-----------+        +-------------------------+        +-----------------+
|           |        |                         |        |                 |
| Open WebUI|  <---> |  RAG API 服务 (FastAPI) |  <---> | MiMo API        |
| Vue 控制台 |        |   (src.app.main:app)   |        | (LLM / Vision)  |
|           |        |                         |        |                 |
+-----------+        +-------------------------+        +-----------------+
                           ^
                           |
                           v
+--------------------------------------------------------------------+
|                                                                    |
|  知识库 (Knowledge Base)                                             |
|  +------------------------+      +-------------------------------+ |
|  | ZhipuAI Embedding Model|  <-> | ChromaDB (Vector Database)    | |
|  +------------------------+      +-------------------------------+ |
|                                                                    |
+--------------------------------------------------------------------+

```

## ⚙️ 环境准备

在开始之前，请确保您已完成以下环境准备工作。

### 1. 安装项目依赖

建议在 Python 3.11 环境下运行。仅运行 API 或导入已验证知识包时使用轻量运行锁；运行自动化测试时使用开发锁：

```bash
pip install --require-hashes -r requirements-runtime.txt
pip install --require-hashes -r requirements-dev.txt
```

只有从原始 PDF 生产知识资产的独立环境才安装重型解析器锁：

```bash
pip install --require-hashes -r requirements-parser.txt
python -m src.pipeline parser-status
```

`requirements-runtime.in`、`requirements-dev.in` 与 `requirements-parser.in` 是三类环境的直接依赖维护入口，对应 `.txt` 文件是带包哈希的 Python 3.11 跨平台精确锁。解析器锁当前固定活动知识资产实际使用过的 `magic-pdf[full]==1.3.12`，不代表 MinerU 2.x/3.x 已兼容。`dependency-lock.json` 固定 Python 版本、`uv` 版本和依赖时间截点；不要手工编辑锁文件。检查或有意升级依赖时执行：

```bash
python -m pip install -r requirements-tools.txt
python scripts/lock_dependencies.py --check

# 修改 .in，并同步更新 dependency-lock.json 的 exclude_newer 后：
python scripts/lock_dependencies.py --write
python scripts/lock_dependencies.py --check
```

GitHub Actions 外部执行代码也属于依赖。提交 workflow 变更前必须验证所有外部 action 都固定到完整提交 SHA、保留可读版本注释，并达到项目核验的运行时代际：

```bash
python scripts/validate_ci_actions.py
```

`.github/dependabot.yml` 每周为这些固定引用提出分组更新；更新仍须人工审阅并通过完整 CI，不自动合并。

提交配置示例变更前必须验证 dotenv 语法、重复键、敏感占位和应用启动配置：

```powershell
python scripts/validate_configuration_example.py
docker compose --env-file .env.example config --quiet
```

第一条命令在隔离环境中用 `.env.example` 执行真实应用配置预检，输出不含配置值的 JSON；第二条命令验证同一示例能完成 Compose 变量替换与结构渲染。真实部署仍需从秘密管理系统注入 Key，不能把示例文件改成凭据文件。

安装依赖并填写实际环境配置后，先运行统一只读自检。默认检查轻量问答运行环境；只有需要从 PDF 构建知识资产时才使用 `build` 配置：

```bash
python -m src.doctor
python -m src.doctor --profile build

# 自动化系统使用稳定 JSON；必需检查失败时退出码为 1
python -m src.doctor --profile runtime --format json
```

自检不会创建目录、修改知识资产、启动服务或调用模型，也不会回显密钥。它通过只代表启动前静态条件成立；API 启动后仍须检查 `/ready`，发布仍须执行完整质量验证。

CI 会从空临时目录重新解析并逐字比较三份锁，同时在 Ubuntu 和 Windows 上按哈希安装开发锁并运行完整测试。只有直接依赖、锁配置、对应锁文件和验证证据同时更新，依赖升级才算完成。

### 2. 配置模型 API Key

本项目使用智谱 `embedding-2` 生成向量，并使用 MiMo 生成回答和多模态校对。复制示例环境变量后填写 `ZHIPUAI_API_KEY` 和 `MIMO_API_KEY`。

**Windows PowerShell:**
```bash
Copy-Item .env.example .env
```

然后编辑 `.env`。不要提交真实密钥；公网部署还必须设置 `API_AUTH_ENABLED=true`、`API_KEYS` 和独立的 `ASSET_SIGNING_KEY`。完整配置见 [配置参考](docs/reference/配置参考.md)。

## 📖 如何运行

请按照以下步骤启动并使用知识库。

### 第一步：运行数据流水线 (首次运行时执行)

此步骤会将您的PDF文档处理并加载到向量数据库中。**如果您已经生成过数据库，可以跳过此步。**

1.  **放入PDF文件**: 将您的PDF规范文件（可以是一或多个）复制到 `data/raw` 目录下。
    - **文件命名规范**: 为了保证元数据处理的准确性，请遵循 `[规范编号]_[规范名称]_[版本].pdf` 的格式。
    - **例如**: `GB 50010-2010_混凝土结构设计规范_2015版.pdf`

2.  **执行统一构建命令**: 在项目根目录运行全量构建。默认使用 MinerU 解析 PDF，并写入 ChromaDB。

    ```bash
    python -m src.pipeline rebuild --source data/raw
    ```

    执行完毕后，您的知识库就已经构建完成了。

### 第二步：启动RAG API服务

在项目根目录，运行`main.py`来启动后端的API服务。

```bash
python src/main.py
```

服务默认运行在 `http://localhost:8000`。当您看到Uvicorn成功启动的日志时，表示API已准备就绪。

如果你拿到的是维护者已构建的运行知识包，可以跳过 PDF 解析、MinerU 和向量化：

```bash
python -m src.pipeline package-validate --package knowledge-runtime.zip
python -m src.pipeline package-probe --package knowledge-runtime.zip
python -m src.pipeline package-import --package knowledge-runtime.zip
python -m uvicorn src.app.main:app --host 127.0.0.1 --port 8000
```

知识包默认导入 `.env` 中 `DATA_DIR` 指向的运行数据根；显式使用 `--data-dir` 时，API 启动前必须把 `DATA_DIR` 设置为同一目录。知识包默认不包含原始 PDF；此时系统不会提供无法访问的动态页面截图链接。完整格式、兼容与内容权利边界见 [知识包格式规范](./docs/reference/知识包格式规范.md)。

维护者导出知识包前必须运行 `python scripts/verify_quality.py`。当前 v4 导出会复核数据版本、评估集哈希和报告年龄，携带来源访问策略，并把兼容性、能力和质量元数据绑定到包标识；失败时默认阻断，紧急豁免必须记录责任人和原因。`package-validate` 只证明格式与哈希完整，目标环境还应运行 `package-probe` 隔离导入并实际打开 Chroma。详见 [知识包格式规范](./docs/reference/知识包格式规范.md) 与 [ADR 0004](./docs/adr/0004-知识包采用受控兼容矩阵与运行探针.md)。

运行包升级与回退必须在维护窗口使用完整 ZIP：保留上一版包及 SHA-256，停止 API 后以 `--replace` 导入，重启并核对包标识与数据版本；回退时重新导入上一版包，不手工编辑活动指针。完整步骤见 [部署运行手册](./docs/operations/部署运行手册.md) 与 [ADR 0009](./docs/adr/0009-运行知识恢复采用受控知识包重部署.md)。

知识包不包含全部运行证据。主机级备份应在停止 API 的维护窗口创建完整 `DATA_DIR` 快照，并把 ZIP 存放在数据根之外：

```bash
python -m src.pipeline backup-create --output runtime-data-backup.zip --maintenance-window
python -m src.pipeline backup-validate --backup runtime-data-backup.zip
```

灾难恢复使用 `backup-restore`，替换非空数据根需显式 `--replace`。快照可能包含原始 PDF、任务和审计，格式不加密且不代表允许对外分发；详见[运行数据快照格式规范](./docs/reference/运行数据快照格式规范.md)。

### 第三步：配置客户端并开始使用

以 Open WebUI 或其他 OpenAI-compatible 客户端为例：

1. 配置 OpenAI-compatible API 基地址为 `http://localhost:8000/v1`。
2. 使用 `GET /v1/models` 返回的模型标识，默认是 `mimo-v2.5`。
3. 开启鉴权时，填写 `API_KEYS` 中配置的 Key。
4. 保存设置，开始提问。

所有提问会先经知识库检索增强，再由模型生成带来源依据的回答。

## 📚 API文档

当API服务运行时，您可以访问 [http://localhost:8000/docs](http://localhost:8000/docs) 查看由FastAPI自动生成的交互式API文档。

## 🧭 项目文档

- [文档中心](./docs/文档中心.md)：当前架构、部署、质量、内容治理和发布的唯一导航入口。
- [系统架构概览](./docs/architecture/系统架构概览.md)：已验证的组件、数据流和运行边界。
- [系统详细设计](./docs/architecture/系统详细设计.md)：组件接口、数据生命周期、部署、安全与关键时序。
- [部署运行手册](./docs/operations/部署运行手册.md)：当前支持的启动方式、生产要求和已知限制。
- [产品方向与边界](./docs/product/产品方向与边界.md)：当前定位、已确认能力、未承诺能力和交付决策边界。
- [AI 校对修正层实施方案](./docs/quality/AI校对修正层实施方案.md)：MinerU 解析后的规则审计、AI 候选和人工批准修正流程。
- [知识库维护与质量运营](./docs/operations/知识库维护与质量运营.md)：复杂表审核、发布保护、评估和日常运维的标准工作流。
- [历史文档说明](./docs/archive/历史文档说明.md)：早期技术方案、实施计划、演进记录和环境交接材料的统一索引。

## 🧱 当前工程结构

API 服务已按分层结构组织：

- `src/app/main.py`：FastAPI 应用创建、路由注册和静态文件挂载。
- `src/app/core/`：配置读取与日志初始化。
- `src/app/api/`：聊天、模型列表、健康检查和图片服务接口。
- `src/app/retrieval/`：ChromaDB、ZhipuAI Embedding、BM25 和条文号混合检索。
- `src/app/rag/`：检索上下文、图片引用和 MiMo payload 组装。
- `src/app/llm/`：MiMo 非流式和流式调用。

旧入口 `src.main:app` 仍保留兼容；新部署建议使用 `src.app.main:app`。当前架构事实以 [系统架构概览](./docs/architecture/系统架构概览.md) 与 [系统详细设计](./docs/architecture/系统详细设计.md) 为准。

## 🏗️ 知识库构建

阶段二已提供统一 pipeline CLI。PDF 解析当前围绕 MinerU 构建，默认后端为 `mineru`；`pymupdf` 仅作为需要人工显式选择的替代后端。以下命令均在项目根目录执行：

```bash
# 只查看将处理哪些 PDF，不写入 processed/images/mineru/db
python -m src.pipeline build --dry-run

# 命令行基础重建；生产控制台重建会隔离候选运行资产、执行预激活门禁后再切换活动指针
python -m src.pipeline rebuild --source data/raw

# 独立检查外部解析器实现、版本和兼容状态，不处理 PDF
python -m src.pipeline parser-status

# 临时使用旧 PyMuPDF 解析后端
python -m src.pipeline rebuild --source data/raw --parser-backend pymupdf

# 查看最近一次构建状态
python -m src.pipeline status

# 对 processed 元素执行规则审计
python -m src.pipeline audit --processed-dir data/processed

# 生成多模态校对报告；配置 MIMO_API_KEY 后写入 correction candidates
python -m src.pipeline review --doc GB50009-2012 --pages 40-45 --source data/raw --processed-dir data/processed

# 将人工标记为 approved 的候选修正提升为构建会应用的 approved corrections
python -m src.pipeline promote-corrections --doc GB50009-2012
```

项目后端名保持为 `mineru`，但当前唯一通过活动资产验证的外部实现是 `magic-pdf 1.3.12`。重建会在清理候选产物前检查 CLI；缺失、版本无法识别或未验证版本在默认严格策略下都会阻断。多模态 review 复用 MiMo 配置；未设置 `MIMO_API_KEY` 时只生成 `not_configured` 报告，不调用外部模型。可通过环境变量调整：

```bash
export PDF_PARSER_BACKEND=mineru
export MINERU_BIN=magic-pdf
export MINERU_ARGS=""
export MINERU_COMPATIBILITY_POLICY=strict
export MIMO_API_KEY="..."
export AI_REVIEW_MODEL="mimo-v2.5"
```

`allow-unverified` 只用于隔离迁移试验，结果会在 manifest 中标记为未验证，不构成生产兼容承诺。解析器版本或输出 schema 升级必须重新完成复杂表、公式、人工校对和候选激活评估。

构建产物：

- `data/processed/*.json`：PDF 元素提取结果。
- `data/processed/*_chunks.json`：标准化 chunk，包含规范编号、名称、版本、条文号、页码、图片、chunk id 等字段。
- `data/processed/build_quality.json`：构建质量报告，统计 element/chunk/table/formula/figure 数、空文本比例和缺失产物。
- `data/audit/reports/`：规则审计和 AI 校对报告。
- `data/corrections/approved/`：人工批准后的修正文件，rebuild 默认应用。
- `data/corrections/candidates/`：AI 生成的待审修正候选，默认不入库。
- `data/mineru/<doc_id>/raw/`：MinerU 原始解析产物，包括 `content_list`、Markdown、middle/model JSON 和媒体文件。
- `data/mineru/<doc_id>/artifacts.json`：单文档产物索引，记录 `kind/path/sha256/size_bytes/required/status`，以及解析器实现、版本、路径、策略和兼容状态。
- `data/images/`：从 MinerU 产物复制出的表格、公式、图片等媒体文件；PyMuPDF fallback 下为页面截图。
- `db/`：ChromaDB 向量库。
- `data/manifest.json`：最近一次构建清单，包含文档 hash、chunk hash、MinerU 产物 hash、chunk 数、图片数、embedding 模型、集合名、解析后端、解析器环境证据和 `data_version_hash`。

MinerU 标准流程以 `content_list` 作为唯一主入库输入；Markdown 用于人工审阅，middle/model JSON 用于后续版面定位、质量回归和审计。`content_list` 和 Markdown 缺失时构建失败，不写成功 manifest；middle/model/media 缺失会进入 manifest 和质量报告。

### AI 校对与修正层

MinerU 结果不被视为 100% 真值。构建流程增加了可审计修正层：

```text
MinerU content_list
 -> standard elements
 -> rules audit
 -> apply data/corrections/approved/
 -> chunks
 -> ChromaDB
```

修正文件建议放在 `data/corrections/approved/<pdf_stem>.json`，结构如下：

```json
{
  "corrections": [
    {
      "id": "fix-page-42-table",
      "action": "replace_text",
      "target": {"element_index": 15, "field": "text"},
      "value": "修正后的文本或表格 Markdown"
    }
  ]
}
```

支持的修正动作：`replace_text`、`set_field`、`delete_element`、`insert_after`、`merge_next`。AI 校对只生成 `candidates`，不会自动进入知识库；只有 `approved` 会在 rebuild 时应用。可使用 `--no-corrections` 临时关闭修正层。

候选修正必须先把 `review_status` 改为 `approved`，再运行 `promote-corrections`。该命令默认跳过 pending 候选。

`data/processed/`、`data/images/`、`data/mineru/`、`data/audit/`、`data/corrections/candidates/`、`db/`、`data/manifest.json` 是生成产物，默认不提交 Git。`data/corrections/approved/` 是否提交取决于是否要把人工校对结果纳入版本管理。

### 规范元数据

系统会优先从 PDF 文件名解析元数据，例如：

```text
GB 50011-2010_建筑抗震设计规范_2016年版.pdf
```

解析得到：

```json
{
  "code": "GB 50011-2010",
  "name": "建筑抗震设计规范",
  "version": "2016年版"
}
```

如需补充别名、生效日期、状态或备注，可编辑 `data/metadata/specs.json`，以 `source_file` 匹配覆盖自动解析结果。

## 🎯 检索质量评估

阶段三提供了标准化检索结果、查询解析、可插拔 reranker 接口和轻量评估 CLI。

```bash
# 运行检索评估，不调用 MiMo，只测试 retrieval
python -m src.evaluation run --top-k 5
```

评估集位于 `data/evaluation/queries.jsonl`，每行包含：

```json
{"id":"case-id","query":"问题","expected_sources":["规范名或编号"],"expected_clause":"8.2.1","expected_keywords":["关键词"],"type":"clause"}
```

输出会包含 source hit、clause hit、keyword hit 和失败样例。若知识库尚未构建或检索服务未初始化，会返回明确错误。

完整验证前先执行无模型调用、无质量报告写入的前置条件预检：

```powershell
python scripts/verify_quality.py --manage-api --preflight-only --api-base http://127.0.0.1:8017
```

预检只检查凭据来源、`/ready`、`/admin/status` 和托管进程回收，失败时用机器可读原因退出非零。它可能更新被 Git 忽略的托管 API 启动日志，但不会运行测试、评估或门禁，也不会覆盖任何 `*_latest` 质量报告。预检通过不代表质量通过。

前置条件通过后，再执行完整的无人值守质量验证：

```powershell
python scripts/verify_quality.py --manage-api --api-base http://127.0.0.1:8017
```

`--manage-api` 会在空闲的本机回环端口启动 API、等待健康检查、执行验证并可靠回收进程；模型配置和 API 鉴权配置从当前受控环境继承，不进入命令行。该入口会运行后端测试、前端生产构建、常规评估、结构化专项评估、24条回答级盲测和自动质量门禁。连接已经运行的 API 时省略 `--manage-api`。报告和托管 API 日志保存在 `data/audit/reports/`；当前执行口径见 [RAG 系统卡](./docs/quality/检索增强生成系统卡.md)、[回答盲测集阅读版](./docs/quality/回答级盲测集阅读版.md) 与 [运维文档](./docs/operations/知识库维护与质量运营.md)，早期实施计划统一收录在[历史文档说明](./docs/archive/历史文档说明.md)中。

`data/audit/` 不提交到 Git。质量验证后，无论结果通过还是失败，都应生成并检查可提交的脱敏状态快照，使系统卡如实反映仓库当前证据：

```powershell
python scripts/snapshot_quality_evidence.py --write
python scripts/snapshot_quality_evidence.py
```

快照只保留报告时间、状态、失败检查、相对路径、SHA-256 和评估集数量，不包含问题、回答、错误详情、秘密或本机绝对路径。`--write` 会先把同一脱敏快照幂等归档到 `docs/quality/质量证据历史/`，重建 `质量证据历史索引.json`，最后更新当前状态；CI 会验证历史指纹、索引、当前快照、评估集和系统卡。在受控本机存在源报告时，同一校验命令还会核对源报告哈希。该历史提供 Git 内部追溯，不是数字签名或外部可信存证。

## 🛡️ 服务成熟化

阶段四增加了服务健康、就绪、鉴权、限流和基础观测能力。

```bash
# 进程存活检查
curl http://localhost:8000/health

# 依赖就绪检查：ChromaDB、manifest、API key、BM25 等
curl http://localhost:8000/ready

# JSON 指标
curl http://localhost:8000/metrics
```

关键配置：

```env
API_AUTH_ENABLED=false
API_KEYS=
ASSET_SIGNING_KEY=
ASSET_URL_TTL_SECONDS=3600
MAX_REQUEST_BYTES=1048576
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=30
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
CORS_ALLOW_CREDENTIALS=false
LOG_LEVEL=INFO
LOG_FORMAT=json
```

开启鉴权后，`/v1/chat/completions` 和 `/chat/completions` 需要：

```http
Authorization: Bearer <API_KEY>
```

或：

```http
X-API-Key: <API_KEY>
```

`/images/*` 和 `/page-images/*` 还会执行每份来源的展示策略。受保护图片既可使用上述 Header，也可使用问答自动生成的短期签名 URL；长期 API Key 不会写入图片链接。

`/health` 只表示进程存活，Docker healthcheck 使用它即可；`/ready` 表示依赖是否满足真实问答条件，就绪返回 HTTP 200，未就绪返回 HTTP 503 并列出机器可读失败原因。`/metrics` 是当前 API 进程的 JSON 快照，重启后清零，不是跨实例聚合指标。每个响应都携带 `X-Request-ID`，可与 JSON 事件日志和后台任务日志关联。

## 🖥️ 产品控制台

项目控制台已重构为 Vue 3 + Tailwind CSS 前端工程，源码位于 `frontend/`。后端默认挂载 `frontend/dist` 到 `/static`，根路径 `/` 会自动跳转到 `/static/index.html`。

本地开发：

```bash
cd frontend
npm install
npm run dev
```

生产构建：

```bash
cd frontend
npm run build
```

Docker 镜像会在多阶段构建中自动执行前端生产构建：

```bash
docker compose config -q
docker compose up --build -d open-webui
docker compose ps --all
docker compose logs --no-color openwebui-preflight
```

启用 API 鉴权时，`.env` 中的 `OPENWEBUI_API_KEY` 必须与 `API_KEYS` 中的一项一致。一次性 `openwebui-preflight` 会在 OpenWebUI 启动前验证真实连接；显示 `Exited (0)` 是成功终态。标准 Compose 以环境变量托管 OpenWebUI 连接，旧数据卷中的连接配置不会覆盖 `.env`，完整启动与轮换步骤见[部署运行手册](./docs/operations/部署运行手册.md)。

控制台采用分工模式：

- Open WebUI：主聊天入口，适合日常多会话问答。
- 项目控制台：知识库状态、文档清单、构建任务、审计、评估、AI 校对、人工批准修正和轻量问答测试。

控制台主要页面：

- 概览：查看服务就绪、chunk、图片、文档清单和运行指标。
- 构建任务：从网页触发 Dry Run、重建、规则审计、AI 校对候选生成和评估任务，并查看任务日志。
- 版本管理：查看活动/历史版本、空间占用和保护原因，人工固定回退点，先生成清理计划再二次确认执行。
- 校对工作台：全屏三栏布局，左侧选择文档和候选，中间查看原 PDF 页面，右侧对比解析文本、AI 证据并编辑最终修正文。
- 评估：查看评估集分布和最近评估报告。
- 问答验证：用于快速检查 RAG API 链路，日常多轮聊天仍建议使用 Open WebUI。

控制台通过 `/admin/*` 后台接口封装原命令行流程。构建、审计、评估和 AI 校对会创建单机后台任务，任务状态以原子替换方式写入 `data/jobs/*.json`，过程日志写入 `data/jobs/*.jsonl`。运行任务记录执行器、心跳和最近进度；API 重启时，旧进程遗留的排队/运行任务会被标记为“已中断”，不会自动重跑。任务页每 5 秒刷新状态和活动任务日志，并区分“执行器仍有心跳但长时间无进展”与“心跳过期”。当前执行器只支持单 API 进程、单工作线程。

常用后台接口：

```text
GET /ready
GET /metrics
GET /knowledge/documents
GET /evaluation/status
GET /admin/status
GET /admin/jobs
GET /admin/jobs/{job_id}
GET /admin/jobs/{job_id}/logs
POST /admin/jobs/dry-run
POST /admin/jobs/rebuild
POST /admin/jobs/audit
POST /admin/jobs/evaluate
POST /admin/jobs/review
GET /admin/corrections/candidates
GET /admin/corrections/candidates/{doc}
POST /admin/corrections/approved/{doc}
GET /admin/elements/{doc}/{element_index}
```

校对工作台不要求人工直接编辑 JSON。推荐流程是：查看候选、对照当前解析元素、在“最终修正文”中写入完整可替换文本或 Markdown 表格、保存为 approved correction，再执行重建。`value` 为 `needs_correction`、包含“需人工校对”或只是描述“更正某项”的候选不应直接保存为 approved。

如果开启 `API_AUTH_ENABLED=true`，控制台中的轻量问答、校对与管理操作需要填写 API Key；Key 只保存在当前浏览器的 localStorage。问答正文中的受保护图片由后端生成短期签名，不要求浏览器把长期 Key 写入图片 URL。

## 📁 项目结构

```
.
├── data/                # 数据目录
│   ├── raw/             # 原始 PDF（受内容治理约束）
│   ├── processed/       # 解析后元素与 chunk
│   ├── images/          # 页面与元素图片资产
│   └── corrections/     # 人工批准的修正
├── db/                  # 存放ChromaDB数据库文件
├── docs/                # 当前文档体系与历史说明
├── frontend/            # Vue 3 + Tailwind 控制台
├── src/                 # API、检索、RAG、LLM 与 pipeline
├── tests/               # 自动化测试
├── README.md            # 快速入口
├── dependency-lock.json # 锁生成器、Python 版本与时间截点契约
├── requirements-tools.txt   # 固定版本的锁生成工具
├── requirements-runtime.in  # 轻量问答运行直接依赖
├── requirements-runtime.txt # 轻量问答运行精确锁
├── requirements-dev.in      # 自动化测试直接依赖
├── requirements-dev.txt     # CI 与自动化测试精确锁
├── requirements-parser.in   # PDF 知识生产直接依赖
└── requirements-parser.txt  # PDF 知识生产精确锁
```
