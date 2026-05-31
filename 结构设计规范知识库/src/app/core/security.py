from fastapi import Request

from .config import settings


PUBLIC_PATHS = {"/", "/health", "/ready", "/metrics", "/models", "/v1/models"}


def is_protected_path(path: str) -> bool:
    return path.endswith("/chat/completions") or path.startswith("/images/") or path.startswith("/corrections/")


def extract_api_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return request.headers.get("x-api-key", "").strip()


def is_authorized(request: Request) -> bool:
    if not settings.api_auth_enabled:
        return True
    if request.url.path in PUBLIC_PATHS or not is_protected_path(request.url.path):
        return True
    key = extract_api_key(request)
    return bool(key and key in settings.api_keys)
