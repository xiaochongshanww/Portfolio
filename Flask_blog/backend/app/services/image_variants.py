import os
from PIL import Image
from typing import List, Dict, Tuple

# Reuse size labels consistent with upload variants
SIZE_VARIANTS: List[Tuple[str, int]] = [
    ("lg", 1600),
    ("md", 800),
    ("sm", 400),
    ("thumb", 200),
]

# Aspect ratios to crop (name, ratio = width/height)
CROP_ASPECTS: List[Tuple[str, float]] = [
    ("16x9", 16/9),
    ("1x1", 1.0),
]


def _safe_open(path: str):
    try:
        return Image.open(path)
    except Exception:
        return None

def _derive_paths(image_url: str, upload_dir: str):
    # image_url like /uploads/2025/08/uuid.jpg
    rel = image_url.lstrip('/')
    if not rel.startswith('uploads/'):
        return None, None, None
    fs_path = os.path.join(upload_dir, rel.replace('uploads/', ''))
    base_dir = os.path.dirname(fs_path)
    filename = os.path.basename(fs_path)
    name_root, ext = os.path.splitext(filename)
    return fs_path, base_dir, (name_root, ext or '.jpg')


def generate_focal_crops(image_url: str, focal_x: float, focal_y: float, upload_dir: str) -> Dict[str, Dict]:
    """Generate cropped variants focusing at focal_x / focal_y (0-1) for each aspect & size.
    Returns mapping: aspect -> { variants: [ {label,url,width,height} ], srcset: str }
    Idempotent: skips existing files.
    """
    out: Dict[str, Dict] = {}
    if focal_x is None or focal_y is None:
        return out
    info = _derive_paths(image_url, upload_dir)
    if not info or not info[0]:
        return out
    orig_path, base_dir, (name_root, ext) = info
    if not os.path.exists(orig_path):
        return out
    img = _safe_open(orig_path)
    if not img:
        return out
    orig_w, orig_h = img.size
    for aspect_name, aspect in CROP_ASPECTS:
        variants = []
        for label, target_w in SIZE_VARIANTS:
            if orig_w < 50 or orig_h < 50:
                break
            # Skip upsizing aggressively: allow if original width >= target_w * 0.6 (else break smaller sizes ok)
            effective_w = min(orig_w, target_w) if orig_w >= target_w * 0.6 else int(orig_w)
            if effective_w < 40:
                continue
            target_w_final = min(target_w, effective_w)
            target_h_final = int(round(target_w_final / aspect))
            # Determine max crop width preserving aspect
            crop_w = min(orig_w, int(orig_h * aspect))
            crop_h = int(round(crop_w / aspect))
            if crop_h > orig_h:
                crop_h = orig_h
                crop_w = int(round(crop_h * aspect))
            # Center around focal
            cx = focal_x * orig_w
            cy = focal_y * orig_h
            left = int(round(cx - crop_w / 2))
            top = int(round(cy - crop_h / 2))
            # Clamp
            if left < 0: left = 0
            if top < 0: top = 0
            if left + crop_w > orig_w: left = orig_w - crop_w
            if top + crop_h > orig_h: top = orig_h - crop_h
            box = (left, top, left + crop_w, top + crop_h)
            variant_name = f"{name_root}_f{aspect_name}_{label}{ext}"
            variant_path = os.path.join(base_dir, variant_name)
            if not os.path.exists(variant_path):
                try:
                    region = img.crop(box)
                    if region.size[0] != target_w_final:
                        region = region.resize((target_w_final, target_h_final))
                    # Save
                    save_kwargs = {}
                    if ext.lower() in ('.jpg', '.jpeg'):
                        save_kwargs['quality'] = 85
                        save_kwargs['optimize'] = True
                    region.save(variant_path, **save_kwargs)
                except Exception:
                    continue
            rel_url = '/uploads/' + os.path.relpath(variant_path, upload_dir).replace('\\', '/')
            variants.append({
                'label': label,
                'url': rel_url,
                'width': target_w_final,
                'height': target_h_final
            })
        if variants:
            srcset = ', '.join(f"{v['url']} {v['width']}w" for v in variants)
            out[aspect_name] = {'variants': variants, 'srcset': srcset}
    return out


def image_dimensions(image_url: str, upload_dir: str):
    info = _derive_paths(image_url, upload_dir)
    if not info or not info[0]:
        return None
    path = info[0]
    if not os.path.exists(path):
        return None
    img = _safe_open(path)
    if not img:
        return None
    return img.size  # (w,h)
