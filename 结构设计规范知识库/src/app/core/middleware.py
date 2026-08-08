import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .errors import ErrorCode, error_response
from .metrics import metrics
from .rate_limit import rate_limiter
from .request_context import normalize_request_id, reset_request_id, set_request_id
from .security import is_authorized, is_trusted_local_request


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


class ServiceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = normalize_request_id(request.headers.get("x-request-id"))
        request_id_token = set_request_id(request_id)
        path = request.url.path
        method = request.method
        client_ip = _client_ip(request)
        start = time.perf_counter()
        status_code = 500
        error_code = ""
        request_metric_started = False

        try:
            metrics.request_started(path)
            request_metric_started = True
            content_length = int(request.headers.get("content-length") or 0)
            if content_length > settings.max_request_bytes:
                error_code = ErrorCode.INVALID_REQUEST
                response = error_response(413, ErrorCode.INVALID_REQUEST, "请求体过大")
                return response

            if not is_authorized(request):
                error_code = ErrorCode.UNAUTHORIZED
                response = error_response(401, ErrorCode.UNAUTHORIZED, "缺少或无效的 API Key")
                return response

            if not is_trusted_local_request(request) and not rate_limiter.allow(f"{client_ip}:{path}"):
                error_code = ErrorCode.RATE_LIMITED
                response = error_response(429, ErrorCode.RATE_LIMITED, "请求过于频繁")
                return response

            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            error_code = ErrorCode.INTERNAL_ERROR
            logging.exception("request failed")
            response = error_response(500, ErrorCode.INTERNAL_ERROR, "服务内部错误")
            return response
        finally:
            try:
                duration_ms = int((time.perf_counter() - start) * 1000)
                if "response" in locals():
                    status_code = response.status_code
                    response.headers["X-Request-ID"] = request_id
                if error_code:
                    metrics.increment_error(str(error_code), path)
                if request_metric_started:
                    metrics.request_finished(path, status_code, duration_ms)
                logging.info(
                    "request_completed",
                    extra={
                        "extra_data": {
                            "request_id": request_id,
                            "method": method,
                            "path": path,
                            "status": status_code,
                            "duration_ms": duration_ms,
                            "error_code": str(error_code) if error_code else "",
                        }
                    },
                )
            finally:
                reset_request_id(request_id_token)

