"""媒体库业务逻辑 — 供 routes.py 编排调用"""

import hashlib
import io
import os
import uuid
from datetime import datetime, timezone

from flask import current_app
from PIL import Image
from werkzeug.utils import secure_filename

from .. import db
from ..models import Media, MediaFolder


ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/svg+xml'}
ALLOWED_DOC_TYPES = {'application/pdf', 'text/plain', 'application/msword',
                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
THUMBNAIL_SIZE = (200, 200)


def get_media_type_from_mime(mime_type: str) -> str:
    if mime_type in ALLOWED_IMAGE_TYPES:
        return 'image'
    if mime_type in ALLOWED_DOC_TYPES:
        return 'document'
    return 'other'


def calculate_file_hash(file_stream) -> str:
    pos = file_stream.tell()
    file_stream.seek(0)
    sha256 = hashlib.sha256()
    for chunk in iter(lambda: file_stream.read(8192), b''):
        sha256.update(chunk)
    file_stream.seek(pos)
    return sha256.hexdigest()


def upload_media_file(file_storage, user_id: int, folder_id: int = None) -> Media:
    """上传媒体文件，返回 Media 记录。"""
    original_filename = secure_filename(file_storage.filename or 'untitled')
    mime_type = file_storage.content_type or 'application/octet-stream'
    file_hash = calculate_file_hash(file_storage)

    # 查重
    existing = Media.query.filter_by(file_hash=file_hash).first()
    if existing:
        return existing

    ext = os.path.splitext(original_filename)[1].lower() or '.bin'
    stored_name = f"{uuid.uuid4().hex}{ext}"
    today = datetime.now(timezone.utc).strftime('%Y/%m/%d')
    relative_dir = os.path.join('media', today)
    upload_dir = os.path.join(current_app.config['UPLOAD_DIR'], relative_dir)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, stored_name)
    file_storage.save(file_path)

    media_type = get_media_type_from_mime(mime_type)
    file_size = os.path.getsize(file_path)

    # 生成缩略图
    thumb_path = None
    if media_type == 'image':
        try:
            img = Image.open(file_path)
            img.thumbnail(THUMBNAIL_SIZE)
            thumb_name = f"thumb_{stored_name}"
            thumb_path = os.path.join(upload_dir, thumb_name)
            img.save(thumb_path)
        except Exception:
            thumb_path = None

    media = Media(
        filename=original_filename, stored_name=stored_name,
        file_path=os.path.join(relative_dir, stored_name),
        thumbnail_path=os.path.join(relative_dir, thumb_name) if thumb_name else None,
        file_size=file_size, mime_type=mime_type, media_type=media_type,
        file_hash=file_hash, folder_id=folder_id,
        uploader_id=user_id,
    )
    db.session.add(media)
    db.session.commit()
    return media


def query_media(page: int, size: int, media_type: str = None,
                folder_id: int = None, search: str = None, sort: str = 'created_at:desc'):
    """分页查询媒体库。"""
    q = Media.query
    if media_type:
        q = q.filter(Media.media_type == media_type)
    if folder_id is not None:
        q = q.filter(Media.folder_id == folder_id)
    if search:
        q = q.filter(Media.filename.ilike(f'%{search}%'))
    sort_field, _, sort_dir = sort.partition(':')
    col = getattr(Media, sort_field, Media.created_at)
    order = col.desc() if sort_dir == 'desc' else col.asc()
    total = q.count()
    items = q.order_by(order).offset((page - 1) * size).limit(size).all()
    return total, items


def get_folders_tree(parent_id: int = None):
    """获取文件夹树。"""
    q = MediaFolder.query
    if parent_id is not None:
        q = q.filter(MediaFolder.parent_id == parent_id)
    else:
        q = q.filter(MediaFolder.parent_id.is_(None))
    folders = q.order_by(MediaFolder.name).all()
    result = []
    for f in folders:
        children = get_folders_tree(f.id)
        item = {'id': f.id, 'name': f.name, 'parent_id': f.parent_id}
        if children:
            item['children'] = children
        result.append(item)
    return result


def create_folder(name: str, parent_id: int = None, user_id: int = None) -> MediaFolder:
    """创建文件夹。"""
    folder = MediaFolder(name=name, parent_id=parent_id, created_by=user_id)
    db.session.add(folder)
    db.session.commit()
    return folder
