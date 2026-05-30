import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..core.config import settings
from ..llm.client import generate_non_stream, rag_stream
from ..schemas.chat import ChatCompletionRequest

router = APIRouter()


@router.get("/v1/models")
@router.get("/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": settings.mimo_model,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "llm",
            },
        ],
    }


@router.post("/v1/chat/completions")
@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if request.stream:
        return StreamingResponse(rag_stream(request), media_type="text/event-stream")
    return await generate_non_stream(request)

