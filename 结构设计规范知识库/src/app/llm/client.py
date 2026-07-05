import json
import logging
import time
from collections.abc import AsyncIterator

import httpx
from fastapi.responses import JSONResponse

from ..core.config import settings
from ..core.errors import ErrorCode, error_response, stream_error
from ..core.metrics import metrics
from ..rag.service import build_mimo_payload
from ..rag.citations import normalize_answer_citations
from ..schemas.chat import ChatCompletionRequest


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.mimo_api_key}", "Content-Type": "application/json"}


async def generate_non_stream(request: ChatCompletionRequest):
    result = await build_mimo_payload(request)
    if isinstance(result, dict) and "error" in result:
        metrics.increment_error(result["error"]["code"], "/v1/chat/completions")
        return JSONResponse(status_code=result.get("status_code", 500), content={"error": result["error"]})

    payload, _images, trace = result
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(
                f"{settings.mimo_base_url}/chat/completions",
                json=payload,
                headers=_headers(),
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            content = normalize_answer_citations(content, trace)
            output = {
                "id": data.get("id", ""),
                "object": "chat.completion",
                "created": int(time.time()),
                "model": data.get("model", request.model),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": data.get("usage", {}),
            }
            if request.include_rag_trace:
                output["rag_trace"] = trace
            return output
    except Exception as exc:
        logging.error("MiMo 调用失败: %s", exc, exc_info=True)
        metrics.increment_error(ErrorCode.LLM_REQUEST_FAILED, "/v1/chat/completions")
        return error_response(502, ErrorCode.LLM_REQUEST_FAILED, f"LLM 调用失败: {exc}")


async def rag_stream(request: ChatCompletionRequest) -> AsyncIterator[str]:
    result = await build_mimo_payload(request)
    if isinstance(result, dict) and "error" in result:
        metrics.increment_error(result["error"]["code"], "/v1/chat/completions")
        yield f"data: {json.dumps({'error': result['error']}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        return

    payload, _images, trace = result
    try:
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        response_id = ""
        response_model = request.model
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            async with client.stream(
                "POST",
                f"{settings.mimo_base_url}/chat/completions",
                json=payload,
                headers=_headers(),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        chunk = json.loads(line[6:])
                        response_id = chunk.get("id", response_id)
                        response_model = chunk.get("model", response_model)
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        if delta.get("content"):
                            content_parts.append(str(delta["content"]))
                        if delta.get("reasoning_content"):
                            reasoning_parts.append(str(delta["reasoning_content"]))

        normalized = normalize_answer_citations("".join(content_parts), trace)
        chunk = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": response_model,
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                        "content": normalized,
                        **(
                            {"reasoning_content": "".join(reasoning_parts)}
                            if reasoning_parts
                            else {}
                        ),
                    },
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        finish = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": response_model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(finish, ensure_ascii=False)}\n\n"
    except Exception as exc:
        logging.error("MiMo 流式失败: %s", exc)
        metrics.increment_error(ErrorCode.LLM_STREAM_FAILED, "/v1/chat/completions")
        yield stream_error(ErrorCode.LLM_STREAM_FAILED, f"LLM 流式调用失败: {exc}")
    yield "data: [DONE]\n\n"
