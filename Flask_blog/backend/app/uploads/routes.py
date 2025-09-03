import os, uuid, base64, io
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from PIL import Image
from .. import require_auth, limiter  # 补充导入

# 新增: 统一尺寸配置
VARIANTS = [
    ('lg', 1600),
    ('md', 800),
    ('sm', 400),
    ('thumb', 200)
]

uploads_bp = Blueprint('uploads', __name__)

@uploads_bp.route('/image', methods=['POST'])
@require_auth
@limiter.limit('20/minute')  # 上传限速
def upload_image():
    if 'file' not in request.files:
        return jsonify({'code':4401,'message':'file required'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'code':4401,'message':'filename required'}), 400
    mime = f.mimetype or ''
    allowed = current_app.config['ALLOWED_IMAGE_TYPES']
    if mime not in allowed:
        return jsonify({'code':4402,'message':'unsupported type','data':{'allowed':allowed}}), 400
    # 限制大小
    f.stream.seek(0, os.SEEK_END)
    size = f.stream.tell()
    f.stream.seek(0)
    if size > current_app.config['MAX_IMAGE_SIZE']:
        return jsonify({'code':4403,'message':'file too large','data':{'max':current_app.config['MAX_IMAGE_SIZE']}}), 400
    # 目录: uploads/YYYY/MM
    now = datetime.utcnow()
    subdir = now.strftime('%Y/%m')
    base_dir = current_app.config['UPLOAD_DIR']
    target_dir = os.path.join(base_dir, subdir)
    os.makedirs(target_dir, exist_ok=True)
    ext = os.path.splitext(f.filename)[1].lower() or '.jpg'
    if ext not in ('.jpg','.jpeg','.png','.webp'):
        ext = '.jpg'
    name_root = uuid.uuid4().hex
    orig_name = name_root + ext
    orig_path = os.path.join(target_dir, orig_name)
    width = height = None
    variants_meta = []
    lqip_b64 = None
    try:
        img = Image.open(f.stream)
        width, height = img.size
        save_kwargs = {}
        if img.format == 'JPEG':
            save_kwargs['optimize'] = True
            save_kwargs['quality'] = 85
        img.save(orig_path, **save_kwargs)
        # 生成多尺寸
        for label, max_w in VARIANTS:
            if width <= max_w:
                # 不放大，直接链接原图
                variants_meta.append({'label': label, 'url': f"/uploads/{subdir}/{orig_name}", 'width': width, 'height': height})
                continue
            ratio = max_w / float(width)
            new_h = int(height * ratio)
            resized = img.resize((max_w, new_h))
            variant_name = f"{name_root}_{label}{ext}"
            variant_path = os.path.join(target_dir, variant_name)
            resized.save(variant_path, **save_kwargs)
            variants_meta.append({'label': label, 'url': f"/uploads/{subdir}/{variant_name}", 'width': max_w, 'height': new_h})
        # 生成 webp (原图尺寸)
        webp_name = f"{name_root}.webp"
        webp_path = os.path.join(target_dir, webp_name)
        img.save(webp_path, format='WEBP', quality=82, method=6)
        # 生成 LQIP (模糊微缩 32px 宽)
        try:
            lq = img.copy()
            target_w = 32
            if width > target_w:
                ratio = target_w / float(width)
                lq = lq.resize((target_w, max(1, int(height*ratio))))
            buf = io.BytesIO()
            lq.save(buf, format='JPEG', quality=25, optimize=True)
            lqip_b64 = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')
        except Exception:
            lqip_b64 = None
    except Exception:
        f.stream.seek(0)
        with open(orig_path, 'wb') as out:
            out.write(f.read())
    # 统计文件大小
    def _size(p):
        try:
            return os.path.getsize(p)
        except Exception:
            return None
    orig_url = f"/uploads/{subdir.replace(os.sep,'/')}/{orig_name}"
    # 构建 srcset (仅从 variants_meta 汇总宽度)
    srcset = ', '.join(f"{v['url']} {v['width']}w" for v in variants_meta if v.get('width')) if variants_meta else None
    data = {
        'url': orig_url,
        'width': width,
        'height': height,
        'size': _size(orig_path),
        'variants': variants_meta,
        'srcset': srcset,
        'lqip': lqip_b64,
        'webp': f"/uploads/{subdir}/{name_root}.webp" if os.path.exists(webp_path) else None
    }
    return jsonify({'code':0,'message':'ok','data':data}), 201
