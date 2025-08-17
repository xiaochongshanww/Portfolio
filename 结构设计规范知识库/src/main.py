
import os
import json
import logging
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

import chromadb
from zhipuai import ZhipuAI

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- FastAPI 应用实例 ---
app = FastAPI(
    title="结构设计规范知识库 RAG API",
    description="一个使用RAG模型与本地知识库交互的API，兼容OpenAI标准。",
    version="1.0.0"
)

# --- 全局配置与客户端初始化 ---

# 路径配置
CWD = os.getcwd()
DB_DIR = os.path.join(CWD, 'db')
COLLECTION_NAME = "design_specs"

# Ollama 配置
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_API_URL = f"{OLLAMA_HOST}/api/chat"

# 初始化HTTP客户端
http_client = httpx.AsyncClient(timeout=30.0)

# 初始化ZhipuAI客户端
try:
    ZHIPUAI_API_KEY = os.environ.get("ZHIPUAI_API_KEY")
    if not ZHIPUAI_API_KEY:
        raise ValueError("未找到环境变量 ZHIPUAI_API_KEY")
    zhipu_client = ZhipuAI(api_key=ZHIPUAI_API_KEY)
    logging.info("智谱AI客户端初始化成功。")
except Exception as e:
    logging.error(f"初始化智谱AI客户端失败: {e}")
    zhipu_client = None

# 初始化ChromaDB客户端
try:
    db_client = chromadb.PersistentClient(path=DB_DIR)
    collection = db_client.get_collection(name=COLLECTION_NAME)
    logging.info(f"ChromaDB客户端初始化成功，已连接到集合 '{COLLECTION_NAME}'。")
except Exception as e:
    logging.error(f"初始化ChromaDB失败或无法连接到集合: {e}")
    db_client = None
    collection = None

# --- Pydantic 数据模型 (兼容OpenAI) ---
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False

# --- RAG 核心逻辑 ---

async def retrieve_context(query: str, n_results: int = 5) -> str:
    """根据用户查询，从ChromaDB检索相关上下文。"""
    if not collection or not zhipu_client:
        return "知识库未初始化，无法检索。"
    try:
        response = zhipu_client.embeddings.create(model="embedding-2", input=[query])
        query_embedding = response.data[0].embedding
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        context = "\n---\n".join([doc for doc in results['documents'][0]])
        logging.info(f"检索到上下文: \n{context}")
        return context
    except Exception as e:
        logging.error(f"检索上下文时出错: {e}")
        return "检索上下文时出错。"

PROMPT_TEMPLATE = """
你是一个专业的、严谨的结构设计规范知识问答助手。
请严格根据下面提供的【上下文信息】，并结合你的专业知识，来回答用户的问题。
如果【上下文信息】与问题无关或者没有提供足够的信息，请明确告知用户“根据现有知识库信息无法回答”，不要编造答案。

【上下文信息】:
{context}

【用户问题】:
{question}
"""

# --- API Endpoint ---

@app.on_event("startup")
async def startup_event():
    # 可以在这里添加更多的启动检查
    if not zhipu_client or not collection:
        logging.warning("一个或多个核心服务未初始化，API可能无法正常工作。")

@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """兼容OpenAI的聊天完成接口。"""
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages 列表不能为空")

    user_query = request.messages[-1].content
    
    # 1. 检索上下文
    context = await retrieve_context(user_query)
    
    # 2. 构建Prompt
    final_prompt = PROMPT_TEMPLATE.format(context=context, question=user_query)
    
    # 3. 构建发送到Ollama的请求体
    ollama_messages = [
        {"role": "system", "content": final_prompt},
    ]
    ollama_payload = {
        "model": request.model,
        "messages": ollama_messages,
        "stream": request.stream
    }

    # 4. 流式或非流式请求Ollama
    try:
        if request.stream:
            async def stream_generator():
                async with http_client.stream("POST", OLLAMA_API_URL, json=ollama_payload) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logging.error(f"请求Ollama失败: {error_text.decode()}")
                        yield f"data: {json.dumps({'error': 'Failed to connect to Ollama'})}\n\n"
                        return
                    
                    async for chunk in response.aiter_bytes():
                        # Ollama的流式输出是JSON行，我们需要转发
                        # 这里我们直接转发原始chunk，因为Chatbox等客户端可以解析它
                        # 如果需要转为OpenAI格式，则需要解析每一行JSON并重构成OpenAI的SSE格式
                        yield chunk
            return StreamingResponse(stream_generator(), media_type="application/x-ndjson")
        else:
            response = await http_client.post(OLLAMA_API_URL, json=ollama_payload)
            response.raise_for_status()
            return response.json()

    except httpx.RequestError as e:
        logging.error(f"请求Ollama时发生网络错误: {e}")
        raise HTTPException(status_code=503, detail=f"无法连接到Ollama服务: {e}")
    except Exception as e:
        logging.error(f"处理聊天请求时发生未知错误: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@app.get("/")
def read_root():
    return {"message": "欢迎使用结构设计规范知识库API。请访问 /docs 查看API文档。"}

# --- Uvicorn 启动入口 ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
