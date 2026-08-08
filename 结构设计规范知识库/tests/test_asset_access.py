import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from src.app.api import images
from src.app.core import content_access, security
from src.app.core.middleware import ServiceMiddleware


def _request(path: str, *, query: str = "", host: str = "127.0.0.1", headers: dict | None = None) -> Request:
    raw_headers = [
        (str(key).lower().encode("latin-1"), str(value).encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": query.encode("ascii"),
            "headers": raw_headers,
            "client": (host, 12345),
            "server": ("testserver", 80),
        }
    )


def _write_policy(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "source_file": "GB 50009-2012_荷载规范.pdf",
                        "image_access": "public",
                        "page_image_access": "disabled",
                    },
                    {
                        "source_file": "GB 50011-2010_抗震规范.pdf",
                        "image_access": "authenticated",
                        "page_image_access": "authenticated",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_source_access_policy_matches_source_and_image_and_fails_closed(tmp_path: Path, monkeypatch):
    policy = tmp_path / "specs.json"
    _write_policy(policy)
    monkeypatch.setattr(content_access, "settings", SimpleNamespace(source_metadata_path=policy))

    assert content_access.asset_access_scope("image", "GB 50009-2012_荷载规范_mineru_001.png") == "public"
    assert content_access.asset_access_scope("page_image", "GB 50009-2012_荷载规范.pdf") == "disabled"
    assert content_access.asset_access_scope("image", "unknown.png") == "authenticated"

    payload = json.loads(policy.read_text(encoding="utf-8"))
    payload["documents"][0]["image_access"] = "invalid"
    policy.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    assert content_access.asset_access_scope("image", "GB 50009-2012_荷载规范_mineru_001.png") == "disabled"


def test_signed_asset_url_rejects_expiry_and_tampering(monkeypatch):
    configured = SimpleNamespace(
        asset_signing_key="s" * 32,
        asset_url_ttl_seconds=300,
        api_auth_enabled=True,
        api_keys=["api-key"],
    )
    monkeypatch.setattr(security, "settings", configured)
    path = "/images/%E6%B5%8B%E8%AF%95.png"
    signed = security.sign_asset_url(path, now=1000)
    parsed = urlsplit(signed)

    assert security.verify_signed_asset_request(_request(parsed.path, query=parsed.query), now=1000) is True
    assert security.verify_signed_asset_request(_request(parsed.path, query=parsed.query), now=1301) is False
    assert security.verify_signed_asset_request(_request("/images/other.png", query=parsed.query), now=1000) is False

    query = parse_qs(parsed.query)
    too_long = f"expires=2000&signature={query['signature'][0]}"
    assert security.verify_signed_asset_request(_request(parsed.path, query=too_long), now=1000) is False


def test_middleware_authorizes_api_key_or_signed_asset(monkeypatch):
    configured = SimpleNamespace(
        asset_signing_key="s" * 32,
        asset_url_ttl_seconds=300,
        api_auth_enabled=True,
        api_keys=["api-key"],
    )
    monkeypatch.setattr(security, "settings", configured)
    monkeypatch.setattr(security, "asset_scope_from_path", lambda *_: "authenticated")
    signed = security.sign_asset_url("/images/evidence.png")
    parsed = urlsplit(signed)

    assert security.is_authorized(_request(parsed.path, headers={"authorization": "Bearer api-key"})) is True
    assert security.is_authorized(_request(parsed.path, query=parsed.query)) is True
    assert security.is_authorized(_request(parsed.path)) is False


def test_image_route_blocks_remote_authenticated_source_without_global_auth(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(images, "asset_access_scope", lambda *_: "authenticated")
    monkeypatch.setattr(images, "settings", SimpleNamespace(img_dir=tmp_path))
    monkeypatch.setattr(
        security,
        "settings",
        SimpleNamespace(api_auth_enabled=False, api_keys=[], asset_signing_key="", asset_url_ttl_seconds=300),
    )

    response = asyncio.run(images.serve_image("preview.png", _request("/images/preview.png", host="203.0.113.8")))

    assert response.status_code == 403


def test_image_route_cannot_escape_image_directory(tmp_path: Path, monkeypatch):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    monkeypatch.setattr(images, "asset_access_scope", lambda *_: "public")
    monkeypatch.setattr(images, "settings", SimpleNamespace(img_dir=image_dir))

    response = asyncio.run(images.serve_image("../secret.txt", _request("/images/../secret.txt")))

    assert response.status_code == 404


def test_asset_access_through_real_middleware_and_router(tmp_path: Path, monkeypatch):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    for name in ("public_doc_preview.png", "protected_doc_preview.png", "disabled_doc_preview.png"):
        (image_dir / name).write_bytes(b"image")
    policy = tmp_path / "specs.json"
    policy.write_text(
        json.dumps(
            {
                "documents": [
                    {"source_file": "public_doc.pdf", "image_access": "public", "page_image_access": "public"},
                    {
                        "source_file": "protected_doc.pdf",
                        "image_access": "authenticated",
                        "page_image_access": "authenticated",
                    },
                    {
                        "source_file": "disabled_doc.pdf",
                        "image_access": "disabled",
                        "page_image_access": "disabled",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    configured_security = SimpleNamespace(
        asset_signing_key="s" * 32,
        asset_url_ttl_seconds=300,
        api_auth_enabled=True,
        api_keys=["api-key"],
    )
    monkeypatch.setattr(content_access, "settings", SimpleNamespace(source_metadata_path=policy))
    content_access._cached_document_records.cache_clear()
    monkeypatch.setattr(security, "settings", configured_security)
    monkeypatch.setattr(images, "settings", SimpleNamespace(img_dir=image_dir))

    app = FastAPI()
    app.add_middleware(ServiceMiddleware)
    app.include_router(images.router)
    client = TestClient(app)

    assert client.get("/images/public_doc_preview.png").status_code == 200
    assert client.get("/images/protected_doc_preview.png").status_code == 401
    assert client.get(
        "/images/protected_doc_preview.png",
        headers={"Authorization": "Bearer api-key"},
    ).status_code == 200
    signed = security.sign_asset_url("/images/protected_doc_preview.png")
    assert client.get(signed).status_code == 200
    assert client.get(
        "/images/disabled_doc_preview.png",
        headers={"Authorization": "Bearer api-key"},
    ).status_code == 403
