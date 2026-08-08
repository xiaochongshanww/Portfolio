from __future__ import annotations

import time
from typing import Any

import httpx

from src.app.core.urls import normalize_http_base_url


def probe_api_readiness(
    api_base: str,
    *,
    timeout: float = 30,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    normalized = normalize_http_base_url(api_base, field_name="API 目标地址")
    target = f"{normalized}/ready"
    owns_client = client is None
    active_client = client or httpx.Client(timeout=timeout)
    try:
        try:
            response = active_client.get(target)
        except Exception as exc:
            return {
                "ok": False,
                "api_base": normalized,
                "ready_url": target,
                "duration_seconds": round(time.monotonic() - started, 2),
                "error": f"目标 API 不可达：{exc}",
            }
        try:
            payload = response.json()
        except Exception as exc:
            return {
                "ok": False,
                "api_base": normalized,
                "ready_url": target,
                "status_code": response.status_code,
                "duration_seconds": round(time.monotonic() - started, 2),
                "error": f"目标 API 的 /ready 未返回有效 JSON：{exc}",
            }
        if not isinstance(payload, dict):
            return {
                "ok": False,
                "api_base": normalized,
                "ready_url": target,
                "status_code": response.status_code,
                "duration_seconds": round(time.monotonic() - started, 2),
                "error": "目标 API 的 /ready JSON 必须是对象",
            }
        ready = response.status_code == 200 and payload.get("ready") is True
        raw_reasons = payload.get("reasons", [])
        reasons = [str(reason) for reason in raw_reasons] if isinstance(raw_reasons, list) else []
        result = {
            "ok": ready,
            "api_base": normalized,
            "ready_url": target,
            "status_code": response.status_code,
            "ready": bool(payload.get("ready")),
            "reasons": reasons,
            "checks": payload.get("checks", {}),
            "data_version_hash": str(payload.get("data_version_hash") or ""),
            "duration_seconds": round(time.monotonic() - started, 2),
        }
        if not ready:
            reason_text = ", ".join(reasons) if reasons else f"HTTP {response.status_code}"
            result["error"] = f"目标 API 未就绪：{reason_text}"
        return result
    finally:
        if owns_client:
            active_client.close()
