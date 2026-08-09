import mimetypes
from urllib.parse import unquote

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from src.pipeline.active_db import active_images_dir
from src.pipeline.audit.multimodal import find_source_pdf, render_pdf_pages
from src.pipeline.paths import AUDIT_DIR, RAW_DIR

from ..core.config import settings
from ..core.content_access import asset_access_scope
from ..core.errors import ErrorCode, error_response
from ..core.security import is_asset_request_allowed

router = APIRouter()


@router.get("/page-images/{doc}/{page}")
async def serve_page_image(doc: str, page: int, request: Request):
    scope = asset_access_scope("page_image", doc)
    if not is_asset_request_allowed(request, scope):
        return error_response(403, ErrorCode.ASSET_ACCESS_DENIED, "当前来源不允许访问页面截图")
    pdf_path = find_source_pdf(decoded_doc := unquote(doc), RAW_DIR)
    if not pdf_path:
        return error_response(404, ErrorCode.IMAGE_NOT_FOUND, f"源 PDF 不存在: {decoded_doc}")
    rendered = render_pdf_pages(pdf_path, [page], AUDIT_DIR / "page_images")
    image_path = rendered.get(page)
    if not image_path or not image_path.exists():
        return error_response(
            404, ErrorCode.IMAGE_NOT_FOUND, f"页截图不存在: {decoded_doc} page {page}"
        )
    return FileResponse(image_path, media_type="image/png")


@router.get("/images/{filename:path}")
async def serve_image(filename: str, request: Request):
    decoded = unquote(filename)
    scope = asset_access_scope("image", decoded)
    if not is_asset_request_allowed(request, scope):
        return error_response(403, ErrorCode.ASSET_ACCESS_DENIED, "当前来源不允许访问提取图片")
    root = active_images_dir(default=settings.img_dir).resolve()
    decoded_path = (root / decoded).resolve()
    if decoded_path.is_relative_to(root) and decoded_path.is_file():
        return FileResponse(
            decoded_path,
            media_type=mimetypes.guess_type(decoded_path.name)[0] or "application/octet-stream",
        )

    return error_response(404, ErrorCode.IMAGE_NOT_FOUND, f"图片不存在: {filename}")
