import os, json, logging, time, base64, re, httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import chromadb
from zhipuai import ZhipuAI
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "12"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.65"))
MIMO_API_KEY = os.getenv("MIMO_API_KEY", "")
MIMO_BASE_URL = os.getenv("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1")
MIMO_MODEL = os.getenv("MIMO_MODEL", "mimo-v2-omni")
COLLECTION_NAME = "design_specs"
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db')
IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'images')
IMG_BASE_URL = os.getenv("IMG_BASE_URL", "/images")

zhipu_client: Optional[ZhipuAI] = None
chroma_collection = None
bm25_index: Optional[BM25Okapi] = None
bm25_texts: list[str] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global zhipu_client, chroma_collection, bm25_index, bm25_texts
    try:
        api_key = os.environ.get("ZHIPUAI_API_KEY")
        if api_key:
            zhipu_client = ZhipuAI(api_key=api_key)
            logging.info("ZhipuAI 初始化成功")
    except Exception as e:
        logging.error(f"ZhipuAI 初始化失败: {e}")

    try:
        os.makedirs(DB_DIR, exist_ok=True)
        db_client = chromadb.PersistentClient(path=DB_DIR)
        chroma_collection = db_client.get_or_create_collection(name=COLLECTION_NAME)
        cnt = chroma_collection.count()
        logging.info(f"ChromaDB: {cnt} 条")

        # 构建 BM25 关键词索引
        if cnt > 0:
            all_data = chroma_collection.get()
            all_texts = [d or "" for d in all_data["documents"]]
            # 中文搜索：用字符 trigram（效果好于 jieba 分词）
            def tokenize_chinese(text: str) -> list[str]:
                t = re.sub(r'[^一-鿿\w]', ' ', text.lower())
                words = t.split()
                chars = list(''.join(words))
                trigrams = [''.join(chars[i:i+3]) for i in range(len(chars)-2)]
                return words + trigrams

            tokenized = [tokenize_chinese(t) for t in all_texts]
            bm25_index = BM25Okapi(tokenized)
            bm25_texts = all_texts
            logging.info(f"BM25 索引构建完成: {len(bm25_texts)} 条")
    except Exception as e:
        logging.error(f"ChromaDB/BM25 初始化失败: {e}")
    yield


app = FastAPI(title="结构设计规范知识库 RAG API (多模态)", version="3.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = MIMO_MODEL
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = 1.0


# ── 工具函数 ──

def load_page_images(source: str, pages: list[int]) -> list[str]:
    if not os.path.isdir(IMG_DIR):
        return []
    name_part = os.path.splitext(source)[0]
    images = []
    for p in pages:
        fp = os.path.join(IMG_DIR, f"{name_part}_p{p:04d}.png")
        if os.path.exists(fp):
            with open(fp, "rb") as f:
                images.append(f"data:image/png;base64,{base64.b64encode(f.read()).decode()}")
    return images


def hybrid_search(query: str, top_k: int):
    global zhipu_client, chroma_collection, bm25_index

    all_data = chroma_collection.get()
    id_to_doc = dict(zip(all_data["ids"], all_data["documents"]))
    id_to_meta = dict(zip(all_data["ids"], all_data["metadatas"]))
    results_pool = {}  # doc_id -> (doc, meta, distance)
    seen_ids = set()

    # 1. 向量检索
    try:
        resp = zhipu_client.embeddings.create(model="embedding-2", input=[query])
        emb = resp.data[0].embedding
        results = chroma_collection.query(query_embeddings=[emb], n_results=top_k * 5)
        for doc_id, dist in zip(results["ids"][0], results["distances"][0]):
            if doc_id in id_to_doc and doc_id not in seen_ids:
                results_pool[doc_id] = (id_to_doc[doc_id], id_to_meta.get(doc_id, {}), dist)
                seen_ids.add(doc_id)
    except Exception as e:
        logging.error(f"向量检索失败: {e}")

    # 2. 条文号直接查找（查询中包含条文号时，强制命中）
    clause_nums = re.findall(r'\d+\.\d+\.?\d*', query)
    if clause_nums:
        for i, meta in enumerate(all_data["metadatas"]):
            title = meta.get("title", "")
            for cn in clause_nums:
                if title.startswith(cn) or title.startswith(f"{cn} "):
                    doc_id = all_data["ids"][i]
                    if doc_id not in seen_ids:
                        results_pool[doc_id] = (id_to_doc[doc_id], meta, 0.1)  # 极高优先级
                        seen_ids.add(doc_id)
                        logging.info(f"条文号精准匹配: {cn} → 块{i}")
                    break

    # 3. BM25 检索（补充关键词匹配结果）
    if bm25_index:
        t = re.sub(r'[^一-鿿\w]', ' ', query.lower())
        words = t.split()
        chars = list(''.join(words))
        trigrams = [''.join(chars[i:i+3]) for i in range(len(chars)-2)]
        query_tokens = words + trigrams
        bm25_scores = bm25_index.get_scores(query_tokens)
        top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k * 10]
        for idx in top_indices:
            doc_id = all_data["ids"][idx]
            if bm25_scores[idx] > 0 and doc_id not in seen_ids:
                bm25_dist = 0.3 if bm25_scores[idx] > 5 else 0.45
                results_pool[doc_id] = (id_to_doc[doc_id], id_to_meta.get(doc_id, {}), bm25_dist)
                seen_ids.add(doc_id)

    # 3. 按距离排序
    sorted_results = sorted(results_pool.values(), key=lambda x: x[2])
    return sorted_results[:top_k]


# ── RAG 核心 ──

async def rag_query(request: ChatCompletionRequest):
    global chroma_collection, zhipu_client
    if not chroma_collection or not zhipu_client:
        return {"error": "服务未就绪", "code": 500}

    current_query = request.messages[-1].content
    if len(request.messages) > 1:
        history = [m.content for m in request.messages[:-1] if m.role == "user"]
        enhanced_query = f"{history[-1]} {current_query}" if history else current_query
    else:
        enhanced_query = current_query

    logging.info(f"检索: {enhanced_query[:120]}")

    # 混合检索
    results = hybrid_search(enhanced_query, RAG_TOP_K)

    if not results:
        return {"error": "知识库中未找到相关条目", "code": 404}

    logging.info(f"检索到 {len(results)} 条")

    # 加载图片（只加载距离达标的结果）
    imgs_to_send = []
    seen_imgs = set()
    context_parts = []

    for doc, meta, dist in results:
        context_parts.append(doc)
        # 距离 < 阈值 才发图片（距离越小越相关）
        if dist < RAG_MIN_SCORE and meta.get("pages"):
            pages_str = meta.get("pages", "")
            source = meta.get("source", "")
            if pages_str and source:
                pages = [int(p) for p in pages_str.split(",") if p.strip().isdigit()]
                for img in load_page_images(source, pages):
                    if img not in seen_imgs:
                        seen_imgs.add(img)
                        imgs_to_send.append(img)

    logging.info(f"图片 {len(imgs_to_send)} 页, 文本 {len(context_parts)} 段")

    # 生成图片引用列表（供 LLM 在回答中引用）
    img_refs = []
    img_list = []
    for doc, meta, dist in results:
        source = meta.get("source", "")
        pages_str = meta.get("pages", "")
        if pages_str and source:
            name_part = os.path.splitext(source)[0]
            pages = [int(p) for p in pages_str.split(",") if p.strip().isdigit()]
            for p in pages:
                fn = f"{name_part}_p{p:04d}.png"
                img_refs.append(fn)
                img_list.append(f"- 第{p}页: `{fn}` → ![]({IMG_BASE_URL}/{fn})")
    img_list_str = "\n".join(img_list)

    # 构建消息
    system_prompt = """你是一位建筑结构规范问答助手，专门根据提供的规范检索文本和规范页面截图回答问题。

请严格遵守以下规则：
0. 优先从"检索文本"中查找答案，文本中的表格数据即使格式混乱也要仔细解析，不要只看截图。
1. 只根据用户提供的检索文本和页面截图回答，不要凭常识或外部知识补充。
2. 回答必须引用具体依据，包括规范名称、条文号、表号、章节、公式或页码；如果材料中没有这些信息，应明确说明未找到。
3. 涉及数值时必须给出单位，并说明该数值来自哪个表、哪一行、哪一列。如果检索文本中包含表格数据，必须从中提取并列出数值。
4. 涉及公式时必须写出公式，解释各参数含义，并说明参数来源。
5. 涉及"是否需要""是否必须""能否"等判断题时，必须说明适用条件，不能只给简单结论。
6. 涉及多个规范时，应分别列出各规范依据，再给出综合结论。
7. 如果检索文本和截图不足以回答，必须回答"当前材料中未找到明确依据"，并说明缺少什么信息。
8. 如果截图和检索文本存在冲突，应指出冲突，不要强行合并为一个确定结论。
9. 不要输出推理过程，只输出最终答案。
10. 回答末尾必须引用相关的规范截图，格式为：`![第X页](图片地址/规范文件名)`

输出格式固定如下：
【结论】
用简洁语言直接回答问题。
【依据】
- 规范名称：
- 条文号 / 表号 / 章节：
- 关键原文或数据：
- 单位：
【说明】
说明适用条件、限制、是否还缺少信息。

如果找不到依据，输出：
【结论】
当前材料中未找到明确依据，无法可靠回答。
【依据】
未检索到足够的规范条文、表格或公式依据。
【说明】
建议补充的规范、章节、页面或工程条件。"""

    context = "\n\n---\n\n".join(context_parts[:20])

    user_text = f"""用户问题：
{current_query}

检索文本：
{context}

页面截图：
已随消息附上。以下为截图列表，你可以在回答末尾用 Markdown 格式引用它们：
{img_list_str}

请根据检索文本和截图回答问题。"""

    content_parts = [{"type": "text", "text": user_text}]
    for img in imgs_to_send:
        content_parts.append({"type": "image_url", "image_url": {"url": img}})

    mimo_messages = [{"role": "system", "content": system_prompt}]
    for msg in request.messages[:-1]:
        mimo_messages.append({"role": msg.role, "content": msg.content})
    mimo_messages.append({"role": "user", "content": content_parts})

    payload = {
        "model": request.model,
        "messages": mimo_messages,
        "stream": request.stream,
        "temperature": request.temperature,
        "top_p": request.top_p,
    }
    return payload, imgs_to_send


async def generate_non_stream(request: ChatCompletionRequest):
    result = await rag_query(request)
    if isinstance(result, dict) and "error" in result:
        return JSONResponse(status_code=result["code"], content=result)

    payload, _ = result
    headers = {"Authorization": f"Bearer {MIMO_API_KEY}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(f"{MIMO_BASE_URL}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return {
                "id": data.get("id", ""), "object": "chat.completion", "created": int(time.time()),
                "model": data.get("model", request.model),
                "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                "usage": data.get("usage", {}),
            }
    except Exception as e:
        logging.error(f"MiMo 调用失败: {e}", exc_info=True)
        return JSONResponse(status_code=502, content={"error": str(e)})


async def rag_stream(request: ChatCompletionRequest):
    result = await rag_query(request)
    if isinstance(result, dict) and "error" in result:
        yield f"data: {json.dumps(result)}\n\n"
        yield "data: [DONE]\n\n"
        return
    payload, _ = result
    headers = {"Authorization": f"Bearer {MIMO_API_KEY}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            async with client.stream("POST", f"{MIMO_BASE_URL}/chat/completions", json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        yield f"{line}\n\n"
    except Exception as e:
        logging.error(f"MiMo 流式失败: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    yield "data: [DONE]\n\n"


# ── API 端点 ──

@app.get("/health")
async def health():
    details = {"chroma_count": -1, "mimo": bool(MIMO_API_KEY), "bm25": bm25_index is not None, "rag_top_k": RAG_TOP_K, "rag_min_score": RAG_MIN_SCORE}
    if chroma_collection:
        try:
            details["chroma_count"] = chroma_collection.count()
        except Exception:
            pass
    return {"status": "ok", "version": app.version, "details": details}


@app.get("/images/{filename:path}")
async def serve_image(filename: str):
    """返回规范页面截图。支持 URL 编码文件名。"""
    from urllib.parse import unquote
    decoded = unquote(filename)
    # 尝试解码后的文件名
    img_path = os.path.join(IMG_DIR, decoded)
    if os.path.exists(img_path):
        return FileResponse(img_path, media_type="image/png")
    # 尝试原始文件名
    img_path = os.path.join(IMG_DIR, filename)
    if os.path.exists(img_path):
        return FileResponse(img_path, media_type="image/png")
    return JSONResponse(status_code=404, content={"error": f"not found: {filename}"})


@app.get("/v1/models")
@app.get("/models")
async def list_models():
    return {"object": "list", "data": [
        {"id": MIMO_MODEL, "object": "model", "created": int(time.time()), "owned_by": "llm"},
    ]}


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if request.stream:
        return StreamingResponse(rag_stream(request), media_type="text/event-stream")
    return await generate_non_stream(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
