from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

from .urls import normalize_http_base_url


DEFAULT_API_BASE = "http://api:8000/v1"
DEFAULT_EXPECTED_MODEL = "mimo-v2.5"
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


class OpenWebUIProbeError(RuntimeError):
    pass


class OpenWebUIProbeTransportError(OpenWebUIProbeError):
    pass


@dataclass(frozen=True)
class OpenWebUIProbeConfig:
    api_base: str
    api_root: str
    expected_model: str
    auth_enabled: bool
    connection_key: str = field(repr=False)
    accepted_keys: tuple[str, ...] = field(repr=False)


def _parse_bool(value: str, *, name: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise OpenWebUIProbeError(f"{name} 必须是布尔值")


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _api_root(api_base: str) -> str:
    parsed = urlsplit(api_base)
    path = parsed.path.rstrip("/")
    if not path.endswith("/v1"):
        raise OpenWebUIProbeError("OpenWebUI API 基地址必须以 /v1 结尾")
    root_path = path[: -len("/v1")]
    return urlunsplit((parsed.scheme, parsed.netloc, root_path, "", "")).rstrip("/")


def load_probe_config(
    *,
    api_base: str | None = None,
    expected_model: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> OpenWebUIProbeConfig:
    values = os.environ if environ is None else environ
    raw_base = (
        api_base
        or values.get("OPENAI_API_BASE_URLS", "").strip()
        or values.get("OPENAI_API_BASE_URL", "").strip()
        or DEFAULT_API_BASE
    )
    if ";" in raw_base:
        raise OpenWebUIProbeError("标准部署只允许一个 OpenWebUI API 基地址")
    try:
        normalized_base = normalize_http_base_url(raw_base, field_name="OpenWebUI API 基地址")
    except ValueError as exc:
        raise OpenWebUIProbeError(str(exc)) from exc

    model = (expected_model or values.get("MIMO_MODEL", "") or DEFAULT_EXPECTED_MODEL).strip()
    if not model:
        raise OpenWebUIProbeError("预期模型标识不能为空")

    auth_enabled = _parse_bool(
        values.get("API_AUTH_ENABLED", "false"),
        name="API_AUTH_ENABLED",
    )
    accepted_keys = _split_csv(values.get("API_KEYS", ""))
    connection_key = values.get("OPENWEBUI_API_KEY", "").strip()
    if auth_enabled:
        if not connection_key:
            raise OpenWebUIProbeError("启用 API 鉴权时 OPENWEBUI_API_KEY 不能为空")
        if not accepted_keys:
            raise OpenWebUIProbeError("启用 API 鉴权时 API_KEYS 不能为空")
        if connection_key not in accepted_keys:
            raise OpenWebUIProbeError("OPENWEBUI_API_KEY 必须与 API_KEYS 中的一项一致")

    return OpenWebUIProbeConfig(
        api_base=normalized_base,
        api_root=_api_root(normalized_base),
        expected_model=model,
        auth_enabled=auth_enabled,
        connection_key=connection_key,
        accepted_keys=accepted_keys,
    )


def _request_json(
    url: str,
    *,
    timeout_seconds: float,
    method: str = "GET",
    api_key: str = "",
    payload: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = int(response.status)
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        raw = exc.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise OpenWebUIProbeTransportError("OpenWebUI 连接目标暂时不可达") from exc

    if not raw:
        return status, None
    try:
        return status, json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OpenWebUIProbeError(f"{urlsplit(url).path} 未返回有效 JSON") from exc


def _expect_status(label: str, actual: int, expected: int) -> None:
    if actual != expected:
        raise OpenWebUIProbeError(f"{label} 状态不符：期望 {expected}，实际 {actual}")


def _probe_once(config: OpenWebUIProbeConfig, *, timeout_seconds: float) -> dict[str, Any]:
    checks: dict[str, int] = {}

    health_status, health = _request_json(
        f"{config.api_root}/health",
        timeout_seconds=timeout_seconds,
    )
    _expect_status("健康检查", health_status, 200)
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise OpenWebUIProbeError("健康检查响应结构无效")
    checks["health"] = health_status

    models_status, models = _request_json(
        f"{config.api_base}/models",
        timeout_seconds=timeout_seconds,
    )
    _expect_status("模型发现", models_status, 200)
    raw_models = models.get("data") if isinstance(models, dict) else None
    if not isinstance(raw_models, list):
        raise OpenWebUIProbeError("模型发现响应缺少 data 数组")
    model_ids = sorted(
        {
            str(item.get("id"))
            for item in raw_models
            if isinstance(item, dict) and item.get("id")
        }
    )
    if config.expected_model not in model_ids:
        raise OpenWebUIProbeError("模型发现结果缺少预期模型")
    checks["models"] = models_status

    anonymous_admin_status, _ = _request_json(
        f"{config.api_root}/admin/status",
        timeout_seconds=timeout_seconds,
    )
    expected_anonymous = 401 if config.auth_enabled else 200
    _expect_status("匿名管理接口", anonymous_admin_status, expected_anonymous)
    checks["anonymous_admin"] = anonymous_admin_status

    authenticated_admin_status, _ = _request_json(
        f"{config.api_root}/admin/status",
        timeout_seconds=timeout_seconds,
        api_key=config.connection_key if config.auth_enabled else "",
    )
    _expect_status("连接 Key 管理接口", authenticated_admin_status, 200)
    checks["connection_admin"] = authenticated_admin_status

    anonymous_chat_status, _ = _request_json(
        f"{config.api_base}/chat/completions",
        timeout_seconds=timeout_seconds,
        method="POST",
        payload={},
    )
    expected_anonymous_chat = 401 if config.auth_enabled else 422
    _expect_status("匿名 chat 探测", anonymous_chat_status, expected_anonymous_chat)
    checks["anonymous_chat"] = anonymous_chat_status

    connection_chat_status, _ = _request_json(
        f"{config.api_base}/chat/completions",
        timeout_seconds=timeout_seconds,
        method="POST",
        api_key=config.connection_key if config.auth_enabled else "",
        payload={},
    )
    _expect_status("连接 Key chat 探测", connection_chat_status, 422)
    checks["connection_chat"] = connection_chat_status

    return {
        "ok": True,
        "api_base": config.api_base,
        "auth_enabled": config.auth_enabled,
        "credential_source": "OPENWEBUI_API_KEY" if config.auth_enabled else "not_required",
        "accepted_key_count": len(config.accepted_keys),
        "expected_model": config.expected_model,
        "model_ids": model_ids,
        "checks": checks,
        "external_model_calls": 0,
    }


def probe_openwebui_connection(
    config: OpenWebUIProbeConfig,
    *,
    timeout_seconds: float = 5,
    attempts: int = 1,
    interval_seconds: float = 1,
) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise OpenWebUIProbeError("timeout_seconds 必须大于 0")
    if attempts <= 0:
        raise OpenWebUIProbeError("attempts 必须大于 0")
    if interval_seconds < 0:
        raise OpenWebUIProbeError("interval_seconds 不能小于 0")

    last_error: OpenWebUIProbeTransportError | None = None
    for attempt in range(1, attempts + 1):
        try:
            result = _probe_once(config, timeout_seconds=timeout_seconds)
            result["attempt"] = attempt
            return result
        except OpenWebUIProbeTransportError as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(interval_seconds)
    raise last_error or OpenWebUIProbeError("OpenWebUI 连接探测失败")


def main() -> None:
    parser = argparse.ArgumentParser(description="验证 OpenWebUI 到受保护 OpenAI-compatible API 的连接")
    parser.add_argument("--api-base", default=None, help="OpenWebUI 使用的 /v1 API 基地址")
    parser.add_argument("--expected-model", default=None, help="模型发现必须包含的模型标识")
    parser.add_argument("--timeout-seconds", type=float, default=5)
    parser.add_argument("--attempts", type=int, default=30)
    parser.add_argument("--interval-seconds", type=float, default=2)
    args = parser.parse_args()

    try:
        config = load_probe_config(api_base=args.api_base, expected_model=args.expected_model)
        result = probe_openwebui_connection(
            config,
            timeout_seconds=args.timeout_seconds,
            attempts=args.attempts,
            interval_seconds=args.interval_seconds,
        )
    except OpenWebUIProbeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        raise SystemExit(1) from exc
    print(json.dumps(result))


if __name__ == "__main__":
    main()
