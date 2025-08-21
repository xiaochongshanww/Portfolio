import os
import json
import logging
import httpx
import time
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union
import chromadb
from zhipuai import ZhipuAI
from dotenv import load_dotenv

# ---
# 0. 加载环境变量和配置
# ---
load_dotenv()

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# FastAPI 应用实例
app = FastAPI(
    title="结构设计规范知识库 RAG API",
    description="一个基于本地知识库的问答API，兼容OpenAI的请求格式。",
    version="1.0.0",
)

# ---
# 1. 初始化客户端
# ---

# 将客户端初始化放在一个依赖项函数中，FastAPI会自动处理
def get_clients():
    """获取ZhipuAI和ChromaDB的客户端实例。"""
    try:
        zhipuai_api_key = os.environ.get("ZHIPUAI_API_KEY")
        if not zhipuai_api_key:
            raise ValueError("未找到环境变量 ZHIPUAI_API_KEY")
        zhipu_client = ZhipuAI(api_key=zhipuai_api_key)
        
        db_dir = os.path.join(os.getcwd(), 'db')
        collection_name = "design_specs"
        db_client = chromadb.PersistentClient(path=db_dir)
        collection = db_client.get_collection(name=collection_name)
        
        logging.info("所有客户端初始化成功。")
        return {"zhipu": zhipu_client, "chroma": collection}
    except Exception as e:
        logging.error(f"客户端初始化失败: {e}", exc_info=True)
        return None

# ---
# 2. 定义API数据模型 (兼容OpenAI)
# ---

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    # 其他OpenAI兼容参数可以按需添加
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = 1.0

# ---
# 3. RAG核心逻辑
# ---

async def rag_stream(request: ChatCompletionRequest):
    """RAG的核心流程，以流式响应的方式实现。
    此版本使用 /api/generate 接口以兼容旧版Ollama。
    """
    clients = get_clients()
    if not clients:
        error_message = {"error": "服务器客户端初始化失败，请检查日志。"}
        yield f"data: {json.dumps(error_message)}\n\n"
        return

    zhipu_client = clients["zhipu"]
    chroma_collection = clients["chroma"]

    # 1. 提取用户最新的问题
    user_query = request.messages[-1].content
    logging.info(f"收到用户问题: {user_query}")

    # 2. 向量化用户问题
    try:
        query_embedding = zhipu_client.embeddings.create(
            model="embedding-2",
            input=[user_query]
        ).data[0].embedding
        logging.info("用户问题向量化成功。")
    except Exception as e:
        logging.error(f"向量化用户问题失败: {e}", exc_info=True)
        error_message = {"error": "向量化用户问题失败。"}
        yield f"data: {json.dumps(error_message)}\n\n"
        return

    # 3. 在ChromaDB中检索相关知识
    try:
        retrieved_docs = chroma_collection.query(
            query_embeddings=[query_embedding],
            n_results=10  # 返回最相关的5个文本块
        )
        logging.info(f"从数据库中检索到 {len(retrieved_docs['documents'][0])} 个相关文档。")
    except Exception as e:
        logging.error(f"从数据库检索失败: {e}", exc_info=True)
        error_message = {"error": "从数据库检索失败。"}
        yield f"data: {json.dumps(error_message)}\n\n"
        return

    # 4. 构建Prompt
    context = "\n\n---\n\n".join(retrieved_docs['documents'][0])
    prompt_template = f"""请基于以下已知信息，详细、全面且专业地回答用户的问题。如果无法从中得到答案，请说 \"根据已知信息无法回答该问题\"。

已知信息:
---
{context}
---

用户的问题:
{user_query}
"""
    logging.info(f"构建的Prompt:\n{prompt_template}")

    # 5. 调用本地Ollama大模型 (/api/generate 接口)
    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    # ollama_model = request.model # 从请求中获取模型名称
    ollama_model = 'deepseek-r1:8b'
    ollama_api_url = f"{ollama_host}/api/generate" # 使用 /api/generate 接口

    # 使用 /api/generate 的 payload 格式
    ollama_payload = {
        "model": ollama_model,
        "prompt": prompt_template,
        "stream": True
    }

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            async with client.stream("POST", ollama_api_url, json=ollama_payload) as response:
                logging.info(f"成功连接Ollama服务({ollama_api_url})，状态码: {response.status_code}")
                response.raise_for_status() # 如果状态码不是2xx，则抛出异常
                
                # 流式处理返回的数据
                async for line in response.aiter_lines():
                    if line.strip():
                        # Ollama /api/generate 的流式输出是JSON字符串，每行一个
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        
                        # 兼容OpenAI的流式响应格式
                        openai_chunk = {
                            "id": f"chatcmpl-ollama-{ollama_model}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": chunk['model'],
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {
                                        "content": token
                                    },
                                    "finish_reason": "stop" if chunk.get('done') else None
                                }
                            ]
                        }
                        yield f"data: {json.dumps(openai_chunk)}\n\n"
                        if chunk.get('done'):
                            break
        logging.info("Ollama流式响应结束。")
    except httpx.RequestError as e:
        logging.error(f"连接Ollama失败: {e}", exc_info=True)
        error_message = {"error": f"无法连接到Ollama服务于 {ollama_host}。请确保Ollama正在运行。"}
        yield f"data: {json.dumps(error_message)}\n\n"
    except Exception as e:
        logging.error(f"调用Ollama大模型时发生未知错误: {e}", exc_info=True)
        error_message = {"error": "调用Ollama大模型时发生未知错误。"}
        yield f"data: {json.dumps(error_message)}\n\n"
    
    # 发送流结束标志
    yield "data: [DONE]\n\n"

# ---
# 4. API端点
# ---

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    处理聊天补全请求，兼容OpenAI API。
    """
    return StreamingResponse(rag_stream(request), media_type="text/event-stream")

# ---
# 5. 应用启动
# ---

if __name__ == "__main__":
    # 使用uvicorn运行FastAPI应用
    # 您可以在命令行中运行: uvicorn src.main:app --reload
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
