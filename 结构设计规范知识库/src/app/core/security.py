import hashlib
import hmac
import time
from ipaddress import ip_address
from urllib.parse import unquote

from fastapi import Request

from .config import settings
from .content_access import asset_scope_from_path


PUBLIC_PATHS = {"/", "/health", "/ready", "/metrics", "/models", "/v1/models"}


def is_protected_path(path: str) -> bool:
    return (
        path.endswith("/chat/completions")
        or path.startswith("/corrections/")
        or path.startswith("/admin/")
        or path.startswith("/images/")
        or path.startswith("/page-images/")
    )


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
    scope = asset_scope_from_path(request.url.path)
    if scope in {"public", "disabled"}:
        return True
    key = extract_api_key(request)
    return bool(key and key in settings.api_keys) or (scope == "authenticated" and verify_signed_asset_request(request))


def _canonical_asset_path(path: str) -> str:
    decoded = unquote(path)
    return decoded if decoded.startswith("/") else f"/{decoded}"


def _asset_signature(path: str, expires: int) -> str:
    message = f"GET\n{_canonical_asset_path(path)}\n{expires}".encode("utf-8")
    return hmac.new(settings.asset_signing_key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def sign_asset_url(path: str, *, expires: int | None = None, now: int | None = None) -> str:
    if not settings.asset_signing_key:
        raise RuntimeError("ASSET_SIGNING_KEY 未配置")
    current = int(time.time() if now is None else now)
    valid_until = expires if expires is not None else current + settings.asset_url_ttl_seconds
    separator = "&" if "?" in path else "?"
    signature = _asset_signature(path.split("?", 1)[0], valid_until)
    return f"{path}{separator}expires={valid_until}&signature={signature}"


def verify_signed_asset_request(request: Request, *, now: int | None = None) -> bool:
    expires_value = request.query_params.get("expires", "")
    supplied = request.query_params.get("signature", "")
    try:
        expires = int(expires_value)
    except ValueError:
        return False
    current = int(time.time() if now is None else now)
    if expires < current or expires > current + settings.asset_url_ttl_seconds:
        return False
    expected = _asset_signature(request.url.path, expires)
    return bool(supplied and hmac.compare_digest(supplied, expected))


def is_asset_request_allowed(request: Request, scope: str) -> bool:
    if scope == "disabled":
        return False
    if scope == "public":
        return True
    if settings.api_auth_enabled:
        key = extract_api_key(request)
        return bool(key and key in settings.api_keys) or verify_signed_asset_request(request)
    return is_trusted_local_request(request)


def is_trusted_local_request(request: Request) -> bool:
    if request.headers.get("forwarded") or request.headers.get("x-forwarded-for"):
        return False
    host = request.client.host if request.client else ""
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False
