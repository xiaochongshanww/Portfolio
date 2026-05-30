import json
from enum import StrEnum
from typing import Any

from .request_context import get_request_id


class ErrorCode(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    KNOWLEDGE_BASE_NOT_READY = "KNOWLEDGE_BASE_NOT_READY"
    NO_RETRIEVAL_RESULTS = "NO_RETRIEVAL_RESULTS"
    LLM_REQUEST_FAILED = "LLM_REQUEST_FAILED"
    LLM_STREAM_FAILED = "LLM_STREAM_FAILED"
    IMAGE_NOT_FOUND = "IMAGE_NOT_FOUND"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def error_payload(code: ErrorCode | str, message: str, request_id: str | None = None) -> dict[str, Any]:
    return {"error": {"code": str(code), "message": message, "request_id": request_id or get_request_id()}}


def error_response(status_code: int, code: ErrorCode | str, message: str):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=status_code, content=error_payload(code, message))


def stream_error(code: ErrorCode | str, message: str) -> str:
    return f"data: {json.dumps(error_payload(code, message), ensure_ascii=False)}\n\n"
