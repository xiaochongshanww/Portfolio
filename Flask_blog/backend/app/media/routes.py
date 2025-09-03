"""
媒体库API路由
提供媒体文件和文件夹的管理功能
"""
import os
import json
import hashlib
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app, send_file
from sqlalchemy import desc, and_, or_, func
from werkzeug.utils import secure_filename
from PIL import Image
import io
import base64

from .. import db, require_auth, require_roles, limiter
from ..models import Media, MediaFolder, User
from .permissions import (
    get_media_query_for_user, get_folder_query_for_user,
    can_view_media, can_modify_media, can_delete_media,
    can_view_folder, can_modify_folder, can_delete_folder,
    filter_media_by_permissions
)

media_bp = Blueprint('media', __name__)


def get_media_type_from_mime(mime_type: str) -> str:
    """根据MIME类型确定媒体类型"""
    if mime_type.startswith('image/'):
        return 'image'
    elif mime_type.startswith('video/'):
        return 'video'
    elif mime_type.startswith('audio/'):
        return 'audio'
    elif mime_type in ['application/pdf', 'text/plain', 'application/msword', 
                       'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        return 'document'
    else:
        return 'other'


def calculate_file_hash(file_stream) -> str:
    """计算文件哈希值"""
    hasher = hashlib.sha256()
    file_stream.seek(0)
    for chunk in iter(lambda: file_stream.read(4096), b""):
        hasher.update(chunk)
    file_stream.seek(0)
    return hasher.hexdigest()


# ================================ 
# 文件上传 API (集成媒体库)
# ================================

@media_bp.route('/upload', methods=['POST'])
@require_auth
@limiter.limit('20/minute')  # 上传限速
def upload_media():
    """上传媒体文件到媒体库"""
    try:
        if 'file' not in request.files:
            return jsonify({'code': 4401, 'message': 'file required'}), 400
            
        file = request.files['file']
        if not file.filename:
            return jsonify({'code': 4401, 'message': 'filename required'}), 400
            
        # 获取额外参数
        folder_id = request.form.get('folder_id', type=int)
        title = request.form.get('title', '')
        alt_text = request.form.get('alt_text', '') 
        description = request.form.get('description', '')
        visibility = request.form.get('visibility', 'private')
        tags = request.form.get('tags', '')  # JSON字符串
        
        # 验证可见性
        if visibility not in ['private', 'shared', 'public']:
            visibility = 'private'
            
        # 验证文件夹权限
        if folder_id:
            folder = MediaFolder.query.get(folder_id)
            if not folder or not can_view_folder(folder, request.user_id, request.user_role):
                return jsonify({'code': 4030, 'message': '无权在此文件夹中上传文件'}), 403
                
        # 检查MIME类型
        mime = file.mimetype or ''
        allowed_types = current_app.config['ALLOWED_IMAGE_TYPES']  # 当前只支持图片
        if mime not in allowed_types:
            return jsonify({
                'code': 4402, 
                'message': 'unsupported type', 
                'data': {'allowed': allowed_types}
            }), 400
            
        # 检查文件大小
        file.stream.seek(0, os.SEEK_END)
        size = file.stream.tell()
        file.stream.seek(0)
        if size > current_app.config['MAX_IMAGE_SIZE']:
            return jsonify({
                'code': 4403, 
                'message': 'file too large', 
                'data': {'max': current_app.config['MAX_IMAGE_SIZE']}
            }), 400
            
        # 计算文件哈希
        file_hash = calculate_file_hash(file.stream)
        
        # 检查是否已存在相同文件
        existing_media = Media.query.filter_by(file_hash=file_hash).first()
        if existing_media and can_view_media(existing_media, request.user_id, request.user_role):
            return jsonify({
                'code': 4090, 
                'message': '文件已存在', 
                'data': existing_media.to_dict()
            }), 409
            
        # 生成文件路径
        now = datetime.utcnow()
        subdir = now.strftime('%Y/%m')
        base_dir = current_app.config['UPLOAD_DIR']
        target_dir = os.path.join(base_dir, subdir)
        os.makedirs(target_dir, exist_ok=True)
        
        # 生成文件名
        ext = os.path.splitext(file.filename)[1].lower() or '.jpg'
        if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
            ext = '.jpg'
        name_root = uuid.uuid4().hex
        filename = name_root + ext
        file_path = os.path.join(target_dir, filename)
        relative_path = os.path.join(subdir, filename).replace('\\', '/')
        
        # 处理图片并保存
        variants_dict = {}
        width = height = None
        lqip_b64 = None
        
        try:
            # 打开图片
            img = Image.open(file.stream)
            width, height = img.size
            
            # 保存原图
            save_kwargs = {}
            if img.format == 'JPEG':
                save_kwargs['optimize'] = True
                save_kwargs['quality'] = 85
            img.save(file_path, **save_kwargs)
            
            # 生成多尺寸变体 (复用现有逻辑)
            from ..uploads.routes import VARIANTS
            variants_list = []
            
            for label, max_w in VARIANTS:
                if width <= max_w:
                    # 不放大，直接链接原图
                    variants_list.append({
                        'label': label, 
                        'url': f"/uploads/{relative_path}", 
                        'width': width, 
                        'height': height
                    })
                    continue
                    
                ratio = max_w / float(width)
                new_h = int(height * ratio)
                resized = img.resize((max_w, new_h))
                
                variant_name = f"{name_root}_{label}{ext}"
                variant_path = os.path.join(target_dir, variant_name)
                resized.save(variant_path, **save_kwargs)
                
                variant_relative = os.path.join(subdir, variant_name).replace('\\', '/')
                variants_list.append({
                    'label': label, 
                    'url': f"/uploads/{variant_relative}", 
                    'width': max_w, 
                    'height': new_h
                })
                
            # 生成WebP版本
            webp_name = f"{name_root}.webp"
            webp_path = os.path.join(target_dir, webp_name)
            img.save(webp_path, format='WEBP', quality=82, method=6)
            webp_relative = os.path.join(subdir, webp_name).replace('\\', '/')
            
            # 生成 LQIP 缩略图
            try:
                lq = img.copy()
                target_w = 32
                if width > target_w:
                    ratio = target_w / float(width)
                    lq = lq.resize((target_w, max(1, int(height * ratio))))
                buf = io.BytesIO()
                lq.save(buf, format='JPEG', quality=25, optimize=True)
                lqip_b64 = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')
            except Exception:
                lqip_b64 = None
                
            # 构建变体字典
            if variants_list:
                srcset = ', '.join(f"{v['url']} {v['width']}w" for v in variants_list if v.get('width'))
                variants_dict = {
                    'variants': variants_list,
                    'srcset': srcset,
                    'webp': f"/uploads/{webp_relative}",
                    'lqip': lqip_b64
                }
                
        except Exception as e:
            # 如果图片处理失败，回退到直接文件保存
            current_app.logger.warning(f"图片处理失败，回退到文件保存: {e}")
            file.stream.seek(0)
            with open(file_path, 'wb') as out:
                out.write(file.read())
                
        # 解析标签
        tags_list = []
        if tags:
            try:
                tags_list = json.loads(tags) if isinstance(tags, str) else tags
            except (json.JSONDecodeError, TypeError):
                tags_list = []
                
        # 创建媒体记录
        media = Media(
            filename=filename,
            original_name=file.filename,
            file_path=relative_path,
            file_size=size,
            file_hash=file_hash,
            mime_type=mime,
            media_type=get_media_type_from_mime(mime),
            owner_id=request.user_id,
            visibility=visibility,
            folder_id=folder_id,
            title=title or file.filename,
            alt_text=alt_text,
            description=description,
            width=width,
            height=height,
            focal_x=0.5,
            focal_y=0.5
        )
        
        # 设置变体和标签
        if variants_dict:
            media.set_variants_dict(variants_dict)
        if tags_list:
            media.set_tags_list(tags_list)
            
        db.session.add(media)
        db.session.commit()
        
        # 返回结果
        result = media.to_dict()
        return jsonify({
            'code': 0, 
            'message': 'success', 
            'data': result
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"媒体上传失败: {e}")
        return jsonify({
            'code': 5000, 
            'message': f'upload failed: {str(e)}', 
            'data': None
        }), 500


# ================================
# 媒体文件管理 API
# ================================

@media_bp.route('', methods=['GET'])
@require_auth
def get_media_list():
    """获取媒体文件列表"""
    try:
        # 获取查询参数
        page = int(request.args.get('page', 1))
        size = min(int(request.args.get('size', 20)), 100)
        media_type = request.args.get('type', '')  # image, video, document, audio
        folder_id = request.args.get('folder_id', type=int)
        keyword = request.args.get('keyword', '')
        owner_id = request.args.get('owner_id', type=int)  # 仅管理员可用
        visibility = request.args.get('visibility', '')  # private, shared, public
        
        # 构建基础查询
        query = get_media_query_for_user(request.user_id, request.user_role)
        
        # 应用过滤条件
        if media_type and media_type in ['image', 'video', 'document', 'audio', 'other']:
            query = query.filter(Media.media_type == media_type)
            
        if folder_id is not None:
            if folder_id == 0:
                # 根目录（没有父文件夹）
                query = query.filter(Media.folder_id.is_(None))
            else:
                query = query.filter(Media.folder_id == folder_id)
                
        if keyword:
            query = query.filter(
                or_(
                    Media.filename.ilike(f'%{keyword}%'),
                    Media.original_name.ilike(f'%{keyword}%'),
                    Media.title.ilike(f'%{keyword}%'),
                    Media.description.ilike(f'%{keyword}%')
                )
            )
            
        if visibility and visibility in ['private', 'shared', 'public']:
            query = query.filter(Media.visibility == visibility)
            
        # 管理员可以按所有者筛选
        if owner_id and request.user_role == 'admin':
            query = query.filter(Media.owner_id == owner_id)
            
        # 排序和分页
        total = query.count()
        media_list = query.order_by(desc(Media.created_at)).offset((page - 1) * size).limit(size).all()
        
        # 转换为字典格式
        media_data = [media.to_dict() for media in media_list]
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'total': total,
                'page': page,
                'size': size,
                'has_next': page * size < total,
                'items': media_data,  # 修改为items字段以匹配前端期望
                'media': media_data  # 保留兼容性
            }
        })
        
    except Exception as e:
        return jsonify({
            'code': 5000,
            'message': f'获取媒体列表失败: {str(e)}',
            'data': None
        }), 500


@media_bp.route('/<int:media_id>', methods=['GET'])
@require_auth
def get_media_detail(media_id: int):
    """获取媒体详情"""
    try:
        media = Media.query.get_or_404(media_id)
        
        # 检查权限
        if not can_view_media(media, request.user_id, request.user_role):
            return jsonify({'code': 4030, 'message': 'forbidden'}), 403
            
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': media.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'code': 5000,
            'message': f'获取媒体详情失败: {str(e)}',
            'data': None
        }), 500


@media_bp.route('/<int:media_id>', methods=['PUT'])
@require_auth
def update_media(media_id: int):
    """更新媒体元数据"""
    try:
        media = Media.query.get_or_404(media_id)
        
        # 检查权限
        if not can_modify_media(media, request.user_id, request.user_role):
            return jsonify({'code': 4030, 'message': 'forbidden'}), 403
            
        data = request.get_json() or {}
        
        # 更新允许的字段
        if 'title' in data:
            media.title = data['title']
        if 'alt_text' in data:
            media.alt_text = data['alt_text']
        if 'description' in data:
            media.description = data['description']
        if 'tags' in data and isinstance(data['tags'], list):
            media.set_tags_list(data['tags'])
        if 'visibility' in data and data['visibility'] in ['private', 'shared', 'public']:
            media.visibility = data['visibility']
        if 'folder_id' in data:
            media.folder_id = data['folder_id'] if data['folder_id'] else None
        if 'focal_x' in data and isinstance(data['focal_x'], (int, float)):
            media.focal_x = max(0, min(1, data['focal_x']))
        if 'focal_y' in data and isinstance(data['focal_y'], (int, float)):
            media.focal_y = max(0, min(1, data['focal_y']))
            
        media.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': media.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 5000,
            'message': f'更新媒体失败: {str(e)}',
            'data': None
        }), 500


@media_bp.route('/<int:media_id>', methods=['DELETE'])
@require_auth
def delete_media(media_id: int):
    """删除媒体文件"""
    try:
        media = Media.query.get_or_404(media_id)
        
        # 检查权限
        if not can_delete_media(media, request.user_id, request.user_role):
            return jsonify({'code': 4030, 'message': 'forbidden'}), 403
            
        # 删除物理文件
        file_path = os.path.join(current_app.config['UPLOAD_DIR'], media.file_path)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                
                # 删除变体文件
                variants = media.get_variants_dict()
                for variant_info in variants.values():
                    if isinstance(variant_info, dict) and 'variants' in variant_info:
                        for variant in variant_info['variants']:
                            if 'url' in variant:
                                variant_path = variant['url'].replace('/uploads/', '')
                                full_variant_path = os.path.join(current_app.config['UPLOAD_DIR'], variant_path)
                                if os.path.exists(full_variant_path):
                                    os.remove(full_variant_path)
                                    
            except OSError as e:
                current_app.logger.warning(f"无法删除物理文件 {file_path}: {e}")
                
        # 删除数据库记录
        db.session.delete(media)
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': None
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 5000,
            'message': f'删除媒体失败: {str(e)}',
            'data': None
        }), 500


@media_bp.route('/<int:media_id>/download', methods=['GET'])
@require_auth
def download_media(media_id: int):
    """下载媒体文件"""
    try:
        media = Media.query.get_or_404(media_id)
        
        # 检查权限
        if not can_view_media(media, request.user_id, request.user_role):
            return jsonify({'code': 4030, 'message': 'forbidden'}), 403
            
        # 增加下载计数
        media.increment_download_count()
        db.session.commit()
        
        # 发送文件
        file_path = os.path.join(current_app.config['UPLOAD_DIR'], media.file_path)
        if not os.path.exists(file_path):
            return jsonify({'code': 4040, 'message': 'file not found'}), 404
            
        return send_file(
            file_path,
            as_attachment=True,
            download_name=media.original_name,
            mimetype=media.mime_type
        )
        
    except Exception as e:
        return jsonify({
            'code': 5000,
            'message': f'下载媒体失败: {str(e)}',
            'data': None
        }), 500


# ================================
# 文件夹管理 API
# ================================

@media_bp.route('/folders', methods=['GET'])
@require_auth
def get_folders():
    """获取文件夹列表"""
    try:
        parent_id = request.args.get('parent_id', type=int)
        
        # 构建查询
        query = get_folder_query_for_user(request.user_id, request.user_role)
        
        if parent_id is not None:
            if parent_id == 0:
                # 根目录文件夹
                query = query.filter(MediaFolder.parent_id.is_(None))
            else:
                query = query.filter(MediaFolder.parent_id == parent_id)
        
        folders = query.order_by(MediaFolder.name).all()
        folders_data = [folder.to_dict() for folder in folders]
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': folders_data
        })
        
    except Exception as e:
        return jsonify({
            'code': 5000,
            'message': f'获取文件夹列表失败: {str(e)}',
            'data': None
        }), 500


@media_bp.route('/folders', methods=['POST'])
@require_auth
def create_folder():
    """创建文件夹"""
    try:
        data = request.get_json() or {}
        
        if not data.get('name'):
            return jsonify({'code': 4000, 'message': '文件夹名称不能为空'}), 400
            
        # 检查父文件夹权限
        parent_id = data.get('parent_id')
        if parent_id:
            parent_folder = MediaFolder.query.get(parent_id)
            if not parent_folder or not can_view_folder(parent_folder, request.user_id, request.user_role):
                return jsonify({'code': 4030, 'message': '无权在此文件夹下创建子文件夹'}), 403
                
        # 创建文件夹
        folder = MediaFolder(
            name=data['name'],
            owner_id=request.user_id,
            parent_id=parent_id,
            visibility=data.get('visibility', 'private'),
            description=data.get('description', '')
        )
        
        db.session.add(folder)
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': folder.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 5000,
            'message': f'创建文件夹失败: {str(e)}',
            'data': None
        }), 500


@media_bp.route('/folders/<int:folder_id>', methods=['PUT'])
@require_auth
def update_folder(folder_id: int):
    """更新文件夹"""
    try:
        folder = MediaFolder.query.get_or_404(folder_id)
        
        # 检查权限
        if not can_modify_folder(folder, request.user_id, request.user_role):
            return jsonify({'code': 4030, 'message': 'forbidden'}), 403
            
        data = request.get_json() or {}
        
        # 更新允许的字段
        if 'name' in data:
            folder.name = data['name']
        if 'description' in data:
            folder.description = data['description']
        if 'visibility' in data and data['visibility'] in ['private', 'shared', 'public']:
            folder.visibility = data['visibility']
            
        folder.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': folder.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 5000,
            'message': f'更新文件夹失败: {str(e)}',
            'data': None
        }), 500


@media_bp.route('/folders/<int:folder_id>', methods=['DELETE'])
@require_auth
def delete_folder(folder_id: int):
    """删除文件夹"""
    try:
        folder = MediaFolder.query.get_or_404(folder_id)
        
        # 检查权限
        if not can_delete_folder(folder, request.user_id, request.user_role):
            return jsonify({'code': 4030, 'message': 'forbidden'}), 403
            
        # 检查是否为空文件夹
        if folder.children.count() > 0 or folder.media_files.count() > 0:
            return jsonify({'code': 4090, 'message': '无法删除非空文件夹'}), 409
            
        db.session.delete(folder)
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': None
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 5000,
            'message': f'删除文件夹失败: {str(e)}',
            'data': None
        }), 500


# ================================
# 统计和管理 API
# ================================

@media_bp.route('/stats', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_media_stats():
    """获取媒体库统计信息"""
    try:
        # 根据权限过滤统计数据
        query = get_media_query_for_user(request.user_id, request.user_role)
        
        # 基础统计
        total_count = query.count()
        total_size = db.session.query(func.sum(Media.file_size)).filter(
            Media.id.in_(query.with_entities(Media.id))
        ).scalar() or 0
        
        # 按类型统计
        type_stats = db.session.query(
            Media.media_type,
            func.count(Media.id).label('count'),
            func.sum(Media.file_size).label('size')
        ).filter(
            Media.id.in_(query.with_entities(Media.id))
        ).group_by(Media.media_type).all()
        
        # 按可见性统计
        visibility_stats = db.session.query(
            Media.visibility,
            func.count(Media.id).label('count')
        ).filter(
            Media.id.in_(query.with_entities(Media.id))
        ).group_by(Media.visibility).all()
        
        # 最近上传
        recent_media = query.order_by(desc(Media.created_at)).limit(5).all()
        
        stats = {
            'total_count': total_count,
            'total_size': total_size,
            'type_distribution': {
                stat.media_type: {'count': stat.count, 'size': stat.size or 0}
                for stat in type_stats
            },
            'visibility_distribution': {
                stat.visibility: stat.count for stat in visibility_stats
            },
            'recent_uploads': [media.to_dict(include_variants=False) for media in recent_media]
        }
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': stats
        })
        
    except Exception as e:
        return jsonify({
            'code': 5000,
            'message': f'获取统计信息失败: {str(e)}',
            'data': None
        }), 500


@media_bp.route('/search', methods=['POST'])
@require_auth
def search_media():
    """高级媒体搜索"""
    try:
        data = request.get_json() or {}
        
        # 基础查询参数
        page = int(data.get('page', 1))
        size = min(int(data.get('size', 20)), 100)
        
        # 搜索条件
        keyword = data.get('keyword', '')
        media_types = data.get('media_types', [])  # 媒体类型列表
        tags = data.get('tags', [])  # 标签列表
        size_range = data.get('size_range', {})  # {min: 100000, max: 10000000}
        date_range = data.get('date_range', {})  # {start: '2024-01-01', end: '2024-12-31'}
        visibility = data.get('visibility', '')
        
        # 构建查询
        query = get_media_query_for_user(request.user_id, request.user_role)
        
        # 关键词搜索
        if keyword:
            query = query.filter(
                or_(
                    Media.filename.ilike(f'%{keyword}%'),
                    Media.original_name.ilike(f'%{keyword}%'),
                    Media.title.ilike(f'%{keyword}%'),
                    Media.description.ilike(f'%{keyword}%'),
                    Media.tags.ilike(f'%{keyword}%')
                )
            )
            
        # 媒体类型过滤
        if media_types:
            valid_types = [t for t in media_types if t in ['image', 'video', 'document', 'audio', 'other']]
            if valid_types:
                query = query.filter(Media.media_type.in_(valid_types))
                
        # 文件大小过滤
        if size_range.get('min'):
            query = query.filter(Media.file_size >= size_range['min'])
        if size_range.get('max'):
            query = query.filter(Media.file_size <= size_range['max'])
            
        # 日期范围过滤
        if date_range.get('start'):
            try:
                start_date = datetime.fromisoformat(date_range['start'])
                query = query.filter(Media.created_at >= start_date)
            except ValueError:
                pass
        if date_range.get('end'):
            try:
                end_date = datetime.fromisoformat(date_range['end'])
                query = query.filter(Media.created_at <= end_date)
            except ValueError:
                pass
                
        # 可见性过滤
        if visibility and visibility in ['private', 'shared', 'public']:
            query = query.filter(Media.visibility == visibility)
            
        # 排序和分页
        sort_by = data.get('sort_by', 'created_at')  # created_at, file_size, filename, usage_count
        sort_order = data.get('sort_order', 'desc')  # asc, desc
        
        if sort_by == 'file_size':
            query = query.order_by(desc(Media.file_size) if sort_order == 'desc' else Media.file_size)
        elif sort_by == 'filename':
            query = query.order_by(desc(Media.filename) if sort_order == 'desc' else Media.filename)
        elif sort_by == 'usage_count':
            query = query.order_by(desc(Media.usage_count) if sort_order == 'desc' else Media.usage_count)
        else:
            query = query.order_by(desc(Media.created_at) if sort_order == 'desc' else Media.created_at)
            
        total = query.count()
        media_list = query.offset((page - 1) * size).limit(size).all()
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'total': total,
                'page': page,
                'size': size,
                'has_next': page * size < total,
                'media': [media.to_dict() for media in media_list]
            }
        })
        
    except Exception as e:
        return jsonify({
            'code': 5000,
            'message': f'搜索失败: {str(e)}',
            'data': None
        }), 500