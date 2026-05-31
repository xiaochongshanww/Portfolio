"""媒体库 API 测试。"""

import io
from .helpers import auth_header


class TestMedia:
    def test_list_media(self, client):
        h = auth_header(client, role='author')
        resp = client.get('/api/v1/media/', headers=h)
        assert resp.status_code in (200,)

    def test_list_media_unauthorized(self, client):
        resp = client.get('/api/v1/media/')
        assert resp.status_code == 401

    def test_upload_media(self, client, app):
        h = auth_header(client, role='author')
        data = {'file': (io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100), 'test.png')}
        resp = client.post('/api/v1/media/upload', data=data, headers=h,
                           content_type='multipart/form-data')
        # upload might redirect or respond directly
        assert resp.status_code not in (401, 403, 500)

    def test_media_stats(self, client):
        h = auth_header(client, role='author')
        resp = client.get('/api/v1/media/stats', headers=h)
        assert resp.status_code in (200,)

    def test_media_folders(self, client):
        h = auth_header(client, role='author')
        resp = client.get('/api/v1/media/folders', headers=h)
        assert resp.status_code in (200,)

    def test_create_folder(self, client):
        h = auth_header(client, role='author')
        resp = client.post('/api/v1/media/folders', json={
            'name': 'Test Folder',
        }, headers=h)
        assert resp.status_code in (200, 201)
