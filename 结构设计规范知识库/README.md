# 结构设计规范知识库

本项目是一个基于RAG（检索增强生成）技术的本地知识库解决方案，专门用于查询结构设计规范。它通过将PDF格式的规范文档处理成向量数据库，并结合本地大语言模型（LLM），提供一个兼容OpenAI API标准的智能问答接口。

## ✨ 功能特性

- **自动化数据处理**: 提供从PDF扫描件到结构化文本的完整自动化处理流水线（OCR、清洗、切分）。
- **智能检索增强**: 利用高质量的文本嵌入模型，精准检索与用户问题最相关的规范条文。
- **本地化LLM支持**: 集成[Ollama](https://ollama.com/)，让您可以使用本地运行的大语言模型（如Llama 3, Qwen）生成答案，确保数据私密性。
- **标准化API**: 提供兼容OpenAI的`/v1/chat/completions`接口，可无缝对接[Chatbox](https://chatbox.app/)、[LobeChat](https://github.com/lobehub/lobe-chat)等多种客户端。
- **流式响应**: 支持打字机效果的流式API响应，提升用户体验。

## 🚀 架构概览

```
+-----------+        +-------------------------+        +-----------------+
|           |        |                         |        |                 |
|  Chatbox  |  <---> |  RAG API 服务 (FastAPI) |  <---> |  Ollama (LLM)   |
| (或其他UI) |        |      (src/main.py)      |        | (e.g., Qwen)    |
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

建议在Python 3.8+ 环境下运行。在项目根目录打开终端，执行以下命令：

```bash
pip install -r requirements.txt
```

### 2. 设置智谱AI API Key

本项目使用智谱AI的`embedding-2`模型来生成高质量的文本向量。请在您的终端中设置环境变量 `ZHIPUAI_API_KEY`。

**macOS / Linux:**
```bash
export ZHIPUAI_API_KEY="您的智谱AI API密钥"
```

**Windows (CMD):**
```bash
set ZHIPUAI_API_KEY="您的智谱AI API密钥"
```

### 3. 安装并运行Ollama

请根据[Ollama官方文档](https://ollama.com/)的指引，下载并安装Ollama。安装后，请从模型库中拉取一个适合中文问答的模型，推荐`qwen:14b-chat`。

```bash
ollama pull qwen:14b-chat
```

确保Ollama服务正在后台运行。

## 📖 如何运行

请按照以下步骤启动并使用知识库。

### 第一步：运行数据流水线 (首次运行时执行)

此步骤会将您的PDF文档处理并加载到向量数据库中。**如果您已经生成过数据库，可以跳过此步。**

1.  **放入PDF文件**: 将您的PDF规范文件（可以是一或多个）复制到 `data/raw` 目录下。
    - **文件命名规范**: 为了保证元数据处理的准确性，请遵循 `[规范编号]_[规范名称]_[版本].pdf` 的格式。
    - **例如**: `GB 50010-2010_混凝土结构设计规范_2015版.pdf`

2.  **执行流水线脚本**: 在项目根目录，依次运行以下脚本。

    ```bash
    python src/pipeline/process_documents.py
    python src/pipeline/step_04_load_to_db.py
    ```

    执行完毕后，您的知识库就已经构建完成了。

### 第二步：启动RAG API服务

在项目根目录，运行`main.py`来启动后端的API服务。

```bash
python src/main.py
```

服务默认运行在 `http://localhost:8000`。当您看到Uvicorn成功启动的日志时，表示API已准备就绪。

### 第三步：配置客户端并开始使用

以 **Chatbox** 为例：

1.  打开Chatbox客户端。
2.  进入设置，在`模型`设置中，将`模型提供商`选为`Ollama`。
3.  将 **Ollama API 地址** 设置为我们刚刚启动的RAG服务的地址：`http://localhost:8000`。
4.  在模型列表中，填入您在Ollama中下载并希望使用的模型名称，例如 `qwen:14b-chat`。
5.  保存设置，开始提问！

现在，您的所有提问都会经由本地知识库检索增强后，再由本地大模型回答。

## 📚 API文档

当API服务运行时，您可以访问 [http://localhost:8000/docs](http://localhost:8000/docs) 查看由FastAPI自动生成的交互式API文档。

## 🧭 项目文档

- [技术方案](./TECHNICAL_PLAN.md)：当前系统架构、核心流程和基础实现方案。
- [产品化实施方案](./PRODUCTIZATION_PLAN.md)：从可运行原型升级为成熟产品的阶段路线、验收标准和近期执行清单。
- [RAG 技术方案演进记录](./RAG_OPTIMIZATION.md)：检索、多模态、PDF 解析和质量优化过程中的决策记录。

## 🧱 当前工程结构

API 服务已按产品化阶段一拆分为分层结构：

- `src/app/main.py`：FastAPI 应用创建、路由注册和静态文件挂载。
- `src/app/core/`：配置读取与日志初始化。
- `src/app/api/`：聊天、模型列表、健康检查和图片服务接口。
- `src/app/retrieval/`：ChromaDB、ZhipuAI Embedding、BM25 和条文号混合检索。
- `src/app/rag/`：检索上下文、图片引用和 MiMo payload 组装。
- `src/app/llm/`：MiMo 非流式和流式调用。

旧入口 `src.main:app` 仍保留兼容；新部署建议使用 `src.app.main:app`。

## 🏗️ 知识库构建

阶段二已提供统一 pipeline CLI。以下命令均在项目根目录执行：

```bash
# 只查看将处理哪些 PDF，不写入 processed/images/db
python -m src.pipeline build --dry-run

# 全量重建知识库：清理旧 processed/images/db，重新处理 PDF、渲染图片、向量化入库并写 manifest
python -m src.pipeline rebuild --source data/raw

# 查看最近一次构建状态
python -m src.pipeline status
```

构建产物：

- `data/processed/*.json`：PDF 元素提取结果。
- `data/processed/*_chunks.json`：标准化 chunk，包含规范编号、名称、版本、条文号、页码、图片、chunk id 等字段。
- `data/images/*.png`：PDF 页面截图。
- `db/`：ChromaDB 向量库。
- `data/manifest.json`：最近一次构建清单，包含文档 hash、chunk 数、图片数、embedding 模型、集合名和 `data_version_hash`。

`data/processed/`、`data/images/`、`db/`、`data/manifest.json` 是生成产物，默认不提交 Git。

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
MAX_REQUEST_BYTES=1048576
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=30
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
CORS_ALLOW_CREDENTIALS=false
```

开启鉴权后，`/v1/chat/completions`、`/chat/completions` 和 `/images/*` 需要：

```http
Authorization: Bearer <API_KEY>
```

或：

```http
X-API-Key: <API_KEY>
```

`/health` 只表示进程存活，Docker healthcheck 使用它即可；`/ready` 表示依赖是否满足真实问答条件，适合部署前检查。

## 🖥️ 产品控制台

项目内置静态控制台位于 `/static/index.html`，根路径 `/` 会自动跳转到该页面。

阶段五采用分工模式：

- Open WebUI：主聊天入口，适合日常多会话问答。
- 项目控制台：知识库状态、文档清单、评估集状态、轻量问答测试、来源图片预览。

控制台读取以下只读接口：

```text
GET /ready
GET /metrics
GET /knowledge/documents
GET /evaluation/status
```

如果开启 `API_AUTH_ENABLED=true`，控制台中的轻量问答和图片访问需要填写 API Key；Key 只保存在当前浏览器的 localStorage。

## 📁 项目结构

```
. 
├── data/                # 数据目录
│   ├── raw/             # 存放原始PDF文件
│   ├── processed/       # 存放清洗后的TXT文件
│   └── chunks/          # 存放切分后的JSON文件
├── db/                  # 存放ChromaDB数据库文件
├── logs/                # (预留) 存放日志文件
├── src/                 # 源代码目录
│   ├── pipeline/        # 数据处理流水线脚本
│   └── main.py          # FastAPI主程序
├── .gitignore           
├── GEMINI.md            # 项目开发规范
├── README.md            # 本文档
└── requirements.txt     # Python依赖
```
