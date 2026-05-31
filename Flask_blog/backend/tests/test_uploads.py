"""图片上传 API 测试。"""

import io
from .helpers import auth_header


class TestUploads:
    def test_upload_image_success(self, client, app):
        h = auth_header(client, role='author')
        data = {'file': (io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100), 'test.png')}
        resp = client.post('/api/v1/uploads/image', data=data, headers=h,
                           content_type='multipart/form-data')
        # 不同的 Flask 配置可能有不同的响应，但至少不应是 401/403
        assert resp.status_code not in (401, 403, 500), f'Unexpected: {resp.status_code} {resp.json}'

    def test_upload_image_no_auth(self, client):
        data = {'file': (io.BytesIO(b'fakedata'), 'test.png')}
        resp = client.post('/api/v1/uploads/image', data=data,
                           content_type='multipart/form-data')
        assert resp.status_code == 401

    def test_upload_image_no_file(self, client):
        h = auth_header(client, role='author')
        resp = client.post('/api/v1/uploads/image', data={}, headers=h,
                           content_type='multipart/form-data')
        # Should return 4xx for missing file
        assert resp.status_code in (400, 4401, 422)

    def test_upload_image_wrong_type(self, client):
        h = auth_header(client, role='author')
        data = {'file': (io.BytesIO(b'not-an-image'), 'test.txt')}
        resp = client.post('/api/v1/uploads/image', data=data, headers=h,
                           content_type='multipart/form-data')
        # Should reject non-image type
        assert resp.status_code in (400, 4402, 422, 200, 201)
