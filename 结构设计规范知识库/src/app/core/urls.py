from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def normalize_http_base_url(value: str, *, field_name: str = "URL") -> str:
    raw = value.strip()
    if not raw:
        raise ValueError(f"{field_name} 不能为空")
    try:
        parsed = urlsplit(raw)
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(f"{field_name} 不是有效 URL：{exc}") from exc
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError(f"{field_name} 只允许 http 或 https")
    if not parsed.hostname:
        raise ValueError(f"{field_name} 必须包含主机名")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{field_name} 不能包含用户名或密码")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{field_name} 不能包含查询参数或片段")
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, path, "", ""))
