import logging
from typing import Any

from ..core.config import settings
from ..core.errors import ErrorCode, error_payload
from ..retrieval.hybrid_search import retrieval_state
from ..schemas.chat import ChatCompletionRequest
from .images import load_page_images
from .prompt import SYSTEM_PROMPT
from .context import format_result_context


def _parse_pages(pages_str: str) -> list[int]:
    return [int(page) for page in pages_str.split(",") if page.strip().isdigit()]


def _enhance_query(request: ChatCompletionRequest) -> str:
    current_query = request.messages[-1].content
    if len(request.messages) <= 1:
        return current_query

    history = [message.content for message in request.messages[:-1] if message.role == "user"]
    return f"{history[-1]} {current_query}" if history else current_query


async def build_mimo_payload(request: ChatCompletionRequest) -> tuple[dict[str, Any], list[str]] | dict[str, Any]:
    if not retrieval_state.ready:
        return error_payload(ErrorCode.KNOWLEDGE_BASE_NOT_READY, "知识库尚未就绪") | {"status_code": 503}

    current_query = request.messages[-1].content
    enhanced_query = _enhance_query(request)
    logging.info("检索: %s", enhanced_query[:120])

    results = retrieval_state.hybrid_search(enhanced_query, settings.rag_top_k)
    if not results:
        return error_payload(ErrorCode.NO_RETRIEVAL_RESULTS, "知识库中未找到相关条目") | {"status_code": 404}

    logging.info("检索到 %s 条", len(results))

    imgs_to_send: list[str] = []
    seen_imgs: set[str] = set()
    context_parts: list[str] = []

    for result in results:
        meta = result.meta
        context_parts.append(format_result_context(result))
        distance = result.meta.get("_distance", 0.1 if result.clause_match else 0.45 if result.bm25_score else 1.0)
        if distance < settings.rag_min_score and meta.get("pages"):
            pages_str = meta.get("pages", "")
            source = meta.get("source", "")
            if pages_str and source:
                for image in load_page_images(source, _parse_pages(pages_str)):
                    if image not in seen_imgs:
                        seen_imgs.add(image)
                        imgs_to_send.append(image)

    logging.info("图片 %s 页, 文本 %s 段", len(imgs_to_send), len(context_parts))

    image_list = []
    for result in results:
        meta = result.meta
        source = meta.get("source", "")
        pages_str = meta.get("pages", "")
        if pages_str and source:
            name_part = source.rsplit(".", 1)[0]
            for page in _parse_pages(pages_str):
                filename = f"{name_part}_p{page:04d}.png"
                image_list.append(f"- 第{page}页: `{filename}` -> ![]({settings.img_base_url}/{filename})")

    context = "\n\n---\n\n".join(context_parts[:20])
    user_text = f"""用户问题：
{current_query}

检索文本：
{context}

页面截图：
已随消息附上。以下为截图列表，你可以在回答末尾用 Markdown 格式引用它们：
{chr(10).join(image_list)}

请根据检索文本和截图回答问题。"""

    content_parts: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
    for image in imgs_to_send:
        content_parts.append({"type": "image_url", "image_url": {"url": image}})

    mimo_messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for message in request.messages[:-1]:
        mimo_messages.append({"role": message.role, "content": message.content})
    mimo_messages.append({"role": "user", "content": content_parts})

    payload = {
        "model": request.model,
        "messages": mimo_messages,
        "stream": request.stream,
        "temperature": request.temperature,
        "top_p": request.top_p,
    }
    return payload, imgs_to_send
