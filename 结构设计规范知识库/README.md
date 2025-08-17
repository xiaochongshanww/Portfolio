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
    python src/pipeline/step_01_extract.py
    python src/pipeline/step_02_clean.py
    python src/pipeline/step_03_split.py
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