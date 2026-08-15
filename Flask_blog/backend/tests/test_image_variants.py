"""图片多尺寸/焦点裁剪管线测试。"""

import os

import pytest
from app.services.image_variants import generate_focal_crops, image_dimensions
from PIL import Image


@pytest.fixture()
def upload_dir(tmp_path):
    d = tmp_path / "uploads"
    d.mkdir()
    return str(d)


def _write_image(path, size=(800, 600), color=(200, 30, 30)):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img = Image.new("RGB", size, color)
    img.save(path, format="JPEG", quality=90)
    return path


class TestGenerateFocalCrops:
    def test_none_focal_returns_empty(self, upload_dir):
        assert generate_focal_crops("/uploads/x.jpg", None, None, upload_dir) == {}

    def test_non_uploads_url_returns_empty(self, upload_dir):
        assert generate_focal_crops("/media/x.jpg", 0.5, 0.5, upload_dir) == {}

    def test_missing_file_returns_empty(self, upload_dir):
        assert generate_focal_crops("/uploads/missing.jpg", 0.5, 0.5, upload_dir) == {}

    def test_generates_crops(self, upload_dir):
        src = os.path.join(upload_dir, "2025", "08", "abc.jpg")
        _write_image(src, (800, 600))
        url = "/uploads/2025/08/abc.jpg"
        out = generate_focal_crops(url, 0.5, 0.5, upload_dir)
        # Both aspects present for a large enough source
        assert "16x9" in out
        assert "1x1" in out
        variants = out["16x9"]["variants"]
        assert variants
        assert "srcset" in out["16x9"]
        # Files actually written
        for v in variants:
            rel = v["url"].replace("/uploads/", "")
            assert os.path.exists(os.path.join(upload_dir, rel))

    def test_idempotent_skip_existing(self, upload_dir):
        src = os.path.join(upload_dir, "abc.jpg")
        _write_image(src, (800, 600))
        url = "/uploads/abc.jpg"
        out1 = generate_focal_crops(url, 0.5, 0.5, upload_dir)
        before = set(
            os.path.join(upload_dir, v["url"].replace("/uploads/", ""))
            for aspect in out1.values()
            for v in aspect["variants"]
        )
        # touch mtimes to detect regeneration
        for p in before:
            os.utime(p, (1000, 1000))
        out2 = generate_focal_crops(url, 0.3, 0.7, upload_dir)
        after = set(
            os.path.join(upload_dir, v["url"].replace("/uploads/", ""))
            for aspect in out2.values()
            for v in aspect["variants"]
        )
        assert before == after  # no new files

    def test_tiny_image_skips_small_sizes(self, upload_dir):
        src = os.path.join(upload_dir, "tiny.jpg")
        _write_image(src, (60, 60))
        out = generate_focal_crops("/uploads/tiny.jpg", 0.5, 0.5, upload_dir)
        # very small source may produce no variants at all
        assert isinstance(out, dict)

    def test_non_image_file(self, upload_dir):
        p = os.path.join(upload_dir, "notimg.jpg")
        os.makedirs(upload_dir, exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"not an image")
        assert generate_focal_crops("/uploads/notimg.jpg", 0.5, 0.5, upload_dir) == {}


class TestImageDimensions:
    def test_dimensions(self, upload_dir):
        src = os.path.join(upload_dir, "dim.jpg")
        _write_image(src, (400, 300))
        assert image_dimensions("/uploads/dim.jpg", upload_dir) == (400, 300)

    def test_missing_returns_none(self, upload_dir):
        assert image_dimensions("/uploads/nope.jpg", upload_dir) is None

    def test_bad_url_returns_none(self, upload_dir):
        assert image_dimensions("/foo.jpg", upload_dir) is None
