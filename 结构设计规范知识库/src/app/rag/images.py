import base64
from pathlib import Path

from ..core.config import settings


def load_page_images(source: str, pages: list[int]) -> list[str]:
    if not settings.img_dir.is_dir():
        return []

    name_part = Path(source).stem
    images: list[str] = []
    for page in pages:
        image_path = settings.img_dir / f"{name_part}_p{page:04d}.png"
        if image_path.exists():
            encoded = base64.b64encode(image_path.read_bytes()).decode()
            images.append(f"data:image/png;base64,{encoded}")
    return images

