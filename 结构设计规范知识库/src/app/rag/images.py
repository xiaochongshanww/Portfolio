import base64
import mimetypes
from pathlib import Path

from ..core.config import settings
from src.pipeline.audit.multimodal import find_source_pdf, render_pdf_pages
from src.pipeline.paths import AUDIT_DIR, RAW_DIR


def _data_url(image_path: Path) -> str:
    media_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(image_path.read_bytes()).decode()
    return f"data:{media_type};base64,{encoded}"


def load_images_by_name(filenames: list[str]) -> list[str]:
    if not settings.img_dir.is_dir():
        return []

    images: list[str] = []
    for filename in filenames:
        image_path = settings.img_dir / Path(filename).name
        if image_path.exists():
            images.append(_data_url(image_path))
    return images


def page_image_filenames(source: str, pages: list[int]) -> list[str]:
    if not settings.img_dir.is_dir():
        return []

    name_part = Path(source).stem
    filenames: list[str] = []
    for page in pages:
        for image_path in settings.img_dir.glob(f"{name_part}_p{page:04d}.*"):
            if image_path.is_file():
                filenames.append(image_path.name)
                break
    return filenames


def source_pdf_available(source: str) -> bool:
    return find_source_pdf(source, RAW_DIR) is not None


def load_page_images(source: str, pages: list[int]) -> list[str]:
    images: list[str] = []
    pdf_path = find_source_pdf(source, RAW_DIR)
    if pdf_path:
        rendered = render_pdf_pages(pdf_path, pages, AUDIT_DIR / "page_images")
        for page in pages:
            image_path = rendered.get(page)
            if image_path and image_path.exists():
                images.append(_data_url(image_path))
    if images:
        return images

    for filename in page_image_filenames(source, pages):
        images.append(_data_url(settings.img_dir / filename))
    return images
