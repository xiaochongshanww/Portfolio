"""媒体库 API 路由 — HTTP 编排，业务逻辑委托给 service.py"""

import os
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request, send_file
from PIL import Image
from sqlalchemy import and_, desc, func, or_
from werkzeug.utils import secure_filename

from .. import db, limiter, require_auth, require_roles
from ..models import Media, MediaFolder, User
from .permissions import (
    can_delete_media,
    can_modify_media,
    can_view_media,
)
from .service import (
    create_folder,
    get_folders_tree,
    query_media,
    upload_media_file,
)

media_bp = Blueprint('media', __name__)


def _ok(data=None, message='ok'):
    return jsonify({'code': 0, 'message': message, 'data': data or {}})


def _err(code, message, status=400):
    return jsonify({'code': code, 'message': message}), status


def _serialize_media(m: Media):
    return {
        'id': m.id, 'filename': m.filename, 'stored_name': m.stored_name,
        'file_path': m.file_path, 'thumbnail_path': m.thumbnail_path,
        'file_size': m.file_size, 'mime_type': m.mime_type,
        'media_type': m.media_type, 'file_hash': m.file_hash,
        'folder_id': m.folder_id, 'uploader_id': m.uploader_id,
        'width': m.width, 'height': m.height,
        'alt_text': m.alt_text, 'caption': m.caption,
        'created_at': m.created_at.isoformat() + 'Z' if m.created_at else None,
    }


# ─── 上传 ──────────────────────────────────────────────────

@media_bp.route('/upload', methods=['POST'])
@require_auth
@limiter.limit('30/minute')
def upload_media():
    if 'file' not in request.files:
        return _err(4001, 'No file provided')
    file = request.files['file']
    if not file.filename:
        return _err(4001, 'Empty filename')
    try:
        folder_id = request.form.get('folder_id', type=int)
        media = upload_media_file(file, request.user_id, folder_id)
        return _ok(_serialize_media(media), 'Uploaded'), 201
    except Exception as e:
        return _err(5000, str(e), 500)


# ─── 列表 ──────────────────────────────────────────────────

@media_bp.route('', methods=['GET'])
@require_auth
def get_media_list():
    page = max(1, int(request.args.get('page', 1)))
    size = min(max(1, int(request.args.get('page_size', 20))), 100)
    media_type = request.args.get('type')
    folder_id = request.args.get('folder_id', type=int)
    search = request.args.get('search')
    sort = request.args.get('sort', 'created_at:desc')
    total, items = query_media(page, size, media_type, folder_id, search, sort)
    return _ok({
        'total': total, 'page': page, 'page_size': size,
        'has_next': page * size < total,
        'items': [_serialize_media(m) for m in items],
    })


# ─── 详情 ──────────────────────────────────────────────────

@media_bp.route('/<int:media_id>', methods=['GET'])
@require_auth
def get_media_detail(media_id: int):
    m = Media.query.get_or_404(media_id)
    return _ok(_serialize_media(m))


@media_bp.route('/<int:media_id>', methods=['PUT'])
@require_auth
def update_media(media_id: int):
    m = Media.query.get_or_404(media_id)
    if not can_modify_media(m, request.user_id, request.user_role):
        return _err(4030, 'Forbidden', 403)
    data = request.get_json() or {}
    for field in ('alt_text', 'caption', 'folder_id'):
        if field in data:
            setattr(m, field, data[field])
    db.session.commit()
    return _ok(_serialize_media(m), 'Updated')


@media_bp.route('/<int:media_id>', methods=['DELETE'])
@require_auth
def delete_media(media_id: int):
    m = Media.query.get_or_404(media_id)
    if not can_delete_media(m, request.user_id, request.user_role):
        return _err(4030, 'Forbidden', 403)
    file_path = os.path.join(current_app.config['UPLOAD_DIR'], m.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    if m.thumbnail_path:
        thumb = os.path.join(current_app.config['UPLOAD_DIR'], m.thumbnail_path)
        if os.path.exists(thumb):
            os.remove(thumb)
    db.session.delete(m)
    db.session.commit()
    return _ok(None, 'Deleted')


@media_bp.route('/<int:media_id>/download', methods=['GET'])
@require_auth
def download_media(media_id: int):
    m = Media.query.get_or_404(media_id)
    file_path = os.path.join(current_app.config['UPLOAD_DIR'], m.file_path)
    if not os.path.exists(file_path):
        return _err(4040, 'File not found', 404)
    return send_file(file_path, mimetype=m.mime_type, as_attachment=True,
                     download_name=m.filename)


# ─── 文件夹 ────────────────────────────────────────────────

@media_bp.route('/folders', methods=['GET'])
@require_auth
def get_folders():
    tree = get_folders_tree()
    return _ok({'folders': tree})


@media_bp.route('/folders', methods=['POST'])
@require_auth
def create_folder_route():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return _err(4001, 'Folder name required')
    parent_id = data.get('parent_id')
    folder = create_folder(name, parent_id, request.user_id)
    return _ok({'id': folder.id, 'name': folder.name, 'parent_id': folder.parent_id}, 'Created'), 201


@media_bp.route('/folders/<int:folder_id>', methods=['PUT'])
@require_auth
def update_folder(folder_id: int):
    folder = MediaFolder.query.get_or_404(folder_id)
    data = request.get_json() or {}
    if 'name' in data:
        folder.name = data['name'].strip()
    if 'parent_id' in data:
        folder.parent_id = data['parent_id']
    db.session.commit()
    return _ok({'id': folder.id, 'name': folder.name}, 'Updated')


@media_bp.route('/folders/<int:folder_id>', methods=['DELETE'])
@require_auth
def delete_folder(folder_id: int):
    folder = MediaFolder.query.get_or_404(folder_id)
    count = Media.query.filter_by(folder_id=folder_id).count()
    if count > 0:
        return _err(4001, f'Folder not empty: {count} media items', 400)
    db.session.delete(folder)
    db.session.commit()
    return _ok(None, 'Deleted')


# ─── 统计 ──────────────────────────────────────────────────

@media_bp.route('/stats', methods=['GET'])
@require_auth
def media_stats():
    total = Media.query.count()
    total_size = db.session.query(db.func.sum(Media.file_size)).scalar() or 0
    by_type = db.session.query(Media.media_type, func.count(Media.id)).group_by(Media.media_type).all()
    return _ok({
        'total': total, 'total_size_bytes': total_size,
        'by_type': {t: c for t, c in by_type},
    })


# ─── 搜索 ──────────────────────────────────────────────────

@media_bp.route('/search', methods=['POST'])
@require_auth
def search_media():
    data = request.get_json() or {}
    page = max(1, int(data.get('page', 1)))
    size = min(max(1, int(data.get('page_size', 20))), 100)
    q = data.get('q', '').strip()
    media_type = data.get('type')
    folder_id = data.get('folder_id', type=int) if data.get('folder_id') else None
    total, items = query_media(page, size, media_type, folder_id, search=q)
    return _ok({
        'total': total, 'page': page, 'page_size': size,
        'has_next': page * size < total,
        'items': [_serialize_media(m) for m in items],
    })
