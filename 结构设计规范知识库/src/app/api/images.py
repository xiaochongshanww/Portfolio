from urllib.parse import unquote

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..core.config import settings
from ..core.errors import ErrorCode, error_response

router = APIRouter()


@router.get("/images/{filename:path}")
async def serve_image(filename: str):
    decoded = unquote(filename)
    decoded_path = settings.img_dir / decoded
    if decoded_path.exists():
        return FileResponse(decoded_path, media_type="image/png")

    raw_path = settings.img_dir / filename
    if raw_path.exists():
        return FileResponse(raw_path, media_type="image/png")

    return error_response(404, ErrorCode.IMAGE_NOT_FOUND, f"图片不存在: {filename}")
