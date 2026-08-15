"""媒体库路由 API 测试 — 覆盖 media/routes。"""

import io

from .helpers import auth_header


def _png_bytes():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, format="PNG")
    return buf.getvalue()


class TestMediaApi:
    def test_upload_media(self, client):
        h = auth_header(client, role="author")
        resp = client.post(
            "/api/v1/media/upload",
            data={"file": (io.BytesIO(_png_bytes()), "test.png")},
            headers=h,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201

    def test_list_media(self, client):
        h = auth_header(client, role="author")
        resp = client.get("/api/v1/media/", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["code"] == 0

    def test_media_detail(self, client):
        h = auth_header(client, role="author")
        up = client.post(
            "/api/v1/media/upload",
            data={"file": (io.BytesIO(_png_bytes()), "test.png")},
            headers=h,
            content_type="multipart/form-data",
        )
        media_id = up.get_json()["data"]["id"]
        resp = client.get(f"/api/v1/media/{media_id}", headers=h)
        assert resp.status_code == 200

    def test_update_media(self, client):
        h = auth_header(client, role="author")
        up = client.post(
            "/api/v1/media/upload",
            data={"file": (io.BytesIO(_png_bytes()), "test.png")},
            headers=h,
            content_type="multipart/form-data",
        )
        media_id = up.get_json()["data"]["id"]
        resp = client.put(
            f"/api/v1/media/{media_id}", json={"alt_text": "alt"}, headers=h
        )
        assert resp.status_code == 200

    def test_folders(self, client):
        h = auth_header(client, role="author")
        resp = client.post(
            "/api/v1/media/folders", json={"name": "My Folder"}, headers=h
        )
        assert resp.status_code == 201
        listing = client.get("/api/v1/media/folders", headers=h)
        assert listing.status_code == 200

    def test_stats_and_search(self, client):
        h = auth_header(client, role="author")
        stats = client.get("/api/v1/media/stats", headers=h)
        assert stats.status_code == 200
        search = client.post("/api/v1/media/search", json={"q": "test"}, headers=h)
        assert search.status_code == 200

    def test_unauthorized(self, client):
        resp = client.get("/api/v1/media/")
        assert resp.status_code == 401


class TestUploadsApi:
    def test_upload_image_success(self, client):
        h = auth_header(client, role="author")
        resp = client.post(
            "/api/v1/uploads/image",
            data={"file": (io.BytesIO(_png_bytes()), "photo.png")},
            headers=h,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        assert resp.get_json()["data"]["url"]

    def test_upload_missing_file(self, client):
        h = auth_header(client, role="author")
        resp = client.post("/api/v1/uploads/image", headers=h)
        assert resp.status_code == 400
        assert resp.get_json()["code"] == 4401

    def test_upload_wrong_type(self, client):
        h = auth_header(client, role="author")
        resp = client.post(
            "/api/v1/uploads/image",
            data={"file": (io.BytesIO(b"not an image"), "doc.txt")},
            headers=h,
            content_type="multipart/form-data",
        )
        # txt 类型不允许 → 4402
        assert resp.get_json()["code"] in (4402,)

    def test_upload_unauthorized(self, client):
        resp = client.post("/api/v1/uploads/image")
        assert resp.status_code == 401
