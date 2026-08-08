# 结构设计规范知识库 - 技术方案

本文档详细描述了“结构设计规范知识库”项目的技术方案，该方案结合了专业的RAG（检索增强生成）流程与用户熟悉的本地化大模型工具。

## 一、 项目目标

构建一个关于结构设计规范的智能、可交互的本地知识库。用户可以通过聊天界面提出问题，系统能够基于本地的规范文档，提供准确、可溯源的回答。

## 二、 整体技术架构

系统采用模块化设计，由用户界面、RAG后端、本地大模型三部分组成，分工明确。

1.  **用户界面 (UI)**:
    *   **工具**: **Chatbox**
    *   **职责**: 作为用户交互的图形化客户端，提供提问入口和答案展示。

2.  **RAG后端 (项目核心)**:
    *   **技术**: **Python + FastAPI**
    *   **职责**: 作为系统的“大脑”和调度中心，负责处理数据、执行RAG流程，并连接UI和本地LLM。它会暴露一个与OpenAI API兼容的接口供Chatbox调用。

3.  **大语言模型 (LLM)**:
    *   **工具**: **Ollama**
    *   **职责**: 负责运行本地大语言模型（如Llama 3, Qwen等），根据RAG后端提供的上下文和问题，生成最终的自然语言回答。

## 三、 核心工作流程

1.  用户在 **Chatbox** 中输入问题。
2.  Chatbox 将问题发送到 **RAG后端 (FastAPI服务)**。
3.  RAG后端接收到问题后，执行以下RAG核心逻辑：
    a.  **问题向量化**: 使用 **Zhipu AI `embedding-2`** 模型将问题文本转换为向量。
    b.  **知识检索**: 在 **ChromaDB** 向量数据库中进行相似性搜索，找出与问题最相关的规范条文作为上下文。
    c.  **构建提示词**: 将检索到的上下文和原始问题组合成一个结构化的提示词 (Prompt)。
4.  RAG后端将构建好的提示词发送给本地运行的 **Ollama** 服务。
5.  Ollama驱动本地LLM生成回答。
6.  RAG后端接收到Ollama的回答，并以流式（Streaming）方式传回给 **Chatbox** 展示给用户。

## 四、 具体实施阶段

### 第一阶段：项目基础建设

*   **任务**:
    *   创建项目目录结构 (`data/raw`, `data/processed`, `db`, `logs`, `src`)。
    *   初始化 `requirements.txt` 文件，并列出核心依赖。
*   **核心依赖**:
    *   `fastapi`, `uvicorn`: Web框架与服务器
    *   `unstructured[local-inference]`: 核心文档处理引擎，包含本地推理所需依赖
    *   `paddlepaddle`, `paddleocr`: 高精度中文OCR引擎
    *   `PyMuPDF`: `unstructured` 使用的底层PDF处理库
    *   `chromadb`: 向量数据库
    *   `zhipuai`: Zhipu AI Embedding模型SDK
    *   `httpx`: 用于调用Ollama API
    *   `black`: 代码格式化

### 第二阶段：数据处理流水线 (全新架构)

*   **核心架构**: 我们采用业界领先的 `unstructured` + `PaddleOCR` 组合方案，彻底取代了原有的多步、手动的处理脚本。
*   **理念**:
    *   **一体化**: 使用单一、统一的脚本 `src/pipeline/process_documents.py` 完成从原始PDF到干净、结构化数据的全过程。
    *   **智能化**: 利用 `unstructured` 的 `hi_res`（高分辨率）处理策略，自动识别扫描件并调用 `PaddleOCR` 进行高精度中文识别，同时能精准解析表格、标题、段落等复杂版面。
    *   **语义化**: 输出的不再是无差别的文本块，而是带有类型（如标题、正文、列表、表格）的“语义单元”，为后续的精准检索奠定坚实基础。
*   **任务**:
    *   实现 `process_documents.py` 脚本。
    *   该脚本遍历 `data/raw` 中的所有PDF文件。
    *   对每个PDF文件，调用 `unstructured.partition` 函数，配置 `strategy="hi_res"`, `infer_table_structure=True`, 和 `languages=["chi_sim", "eng"]`。
*   **产出**: `data/processed` 目录下，为每个PDF生成一个对应的JSON文件。文件中包含了从PDF中提取出的、带有类型和元数据的结构化元素列表。

### 第三阶段：知识核心构建

*   **任务**:
    *   编写脚本，使用`zhipuai/embedding-2`模型对**第二阶段产出的结构化数据**进行向量化。
    *   将生成的向量、原始文本和元数据存入ChromaDB。
    *   配置ChromaDB将数据持久化存储在 `db/` 目录。

### 第四阶段：RAG后端与API开发

*   **任务**:
    *   使用FastAPI搭建Web服务。
    *   实现与OpenAI API兼容的 `/v1/chat/completions` 端点。
    *   在该端点中完整实现**第三节**所述的RAG核心工作流程。
    *   编写详细的部署和使用说明，指导用户如何配置Chatbox连接到本服务，以及如何运行Ollama。

---

## 可选优化：切换到本地嵌入模型

当前方案使用智谱AI的`embedding-2`模型API进行向量化，这在性能和效果上表现优异，但需要网络连接且按量收费。为了实现一个完全免费、可离线运行的方案，可以切换到在本地运行的开源嵌入模型。

### 1. 方案优势

*   **完全免费**: 开源模型和本地计算，无API调用费用。
*   **完全离线**: 模型下载完成后，整个流程无需互联网连接。
*   **数据私密**: 所有数据均在本地处理，不离开您的设备。

### 2. 技术选型

*   **核心库**: `sentence-transformers`。这是一个用于加载和使用嵌入模型的流行Python库，非常易用。
*   **推荐模型**: `BAAI/bge-large-zh-v1.5`。这是由北京智源人工智能研究院（BAAI）开发的、在中文领域表现顶尖的开源嵌入模型。

### 3. 实施步骤

这是一个对现有代码的重构，主要涉及以下三个步骤：

1.  **更新依赖**:
    *   在 `requirements.txt` 文件中，移除 `zhipuai`。
    *   添加 `sentence-transformers`。
    *   由于`sentence-transformers`需要`PyTorch`，需确认`torch`已存在于依赖中（`unstructured`已默认安装）。

2.  **重构知识库加载脚本 (`src/pipeline/step_04_load_to_db.py`)**:
    *   移除初始化智谱AI客户端的代码。
    *   在脚本开始时，增加加载本地模型的代码：`model = SentenceTransformer('BAAI/bge-large-zh-v1.5')`。
    *   修改`embed_and_load`函数，将调用智谱API的部分，替换为调用本地模型的`model.encode(texts_to_embed)`方法来生成向量。

3.  **重构API服务 (`src/main.py`)**:
    *   同样移除智谱AI客户端的初始化。
    *   在服务启动时加载本地模型，并使其在所有请求间共享（例如，通过一个全局变量或FastAPI的依赖注入）。
    *   修改`rag_stream`函数，在向量化用户问题时，也使用`model.encode(user_query)`方法。

**注意**: 首次执行改造后的脚本时，`sentence-transformers`库会自动从Hugging Face Hub下载并缓存`bge-large-zh-v1.5`模型（约2GB），需要稳定的网络连接。此过程为一次性操作。
