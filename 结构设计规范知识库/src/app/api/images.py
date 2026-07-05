import mimetypes
from urllib.parse import unquote

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..core.config import settings
from ..core.errors import ErrorCode, error_response
from src.pipeline.audit.multimodal import find_source_pdf, render_pdf_pages
from src.pipeline.paths import AUDIT_DIR, RAW_DIR

router = APIRouter()


@router.get("/page-images/{doc}/{page}")
async def serve_page_image(doc: str, page: int):
    pdf_path = find_source_pdf(decoded_doc := unquote(doc), RAW_DIR)
    if not pdf_path:
        return error_response(404, ErrorCode.IMAGE_NOT_FOUND, f"源 PDF 不存在: {decoded_doc}")
    rendered = render_pdf_pages(pdf_path, [page], AUDIT_DIR / "page_images")
    image_path = rendered.get(page)
    if not image_path or not image_path.exists():
        return error_response(404, ErrorCode.IMAGE_NOT_FOUND, f"页截图不存在: {decoded_doc} page {page}")
    return FileResponse(image_path, media_type="image/png")


@router.get("/images/{filename:path}")
async def serve_image(filename: str):
    decoded = unquote(filename)
    decoded_path = settings.img_dir / decoded
    if decoded_path.exists():
        return FileResponse(decoded_path, media_type=mimetypes.guess_type(decoded_path.name)[0] or "application/octet-stream")

    raw_path = settings.img_dir / filename
    if raw_path.exists():
        return FileResponse(raw_path, media_type=mimetypes.guess_type(raw_path.name)[0] or "application/octet-stream")

    return error_response(404, ErrorCode.IMAGE_NOT_FOUND, f"图片不存在: {filename}")
