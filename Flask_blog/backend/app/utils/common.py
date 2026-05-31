import hashlib
import json

import bleach
import markdown as md

ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union({
    'p','pre','code','img','h1','h2','h3','h4','h5','h6','span','blockquote','hr','br','ul','ol','li','strong','em','table','thead','tbody','tr','th','td','a'
})
ALLOWED_ATTRS = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    'img': ['src','alt','title'],
    'a': ['href','title','rel','target'],
    'code': ['class'],
    'span': ['class']
}

MD_EXTENSIONS = [
    'fenced_code','codehilite','tables','toc'
]

# Deprecated: use services.content_sanitizer.render_and_sanitize instead
def render_markdown(raw: str) -> str:  # noqa: E305
    if not raw:
        return ''
    html = md.markdown(raw, extensions=MD_EXTENSIONS, output_format='html5')
    cleaned = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    return cleaned

def audit_log(action: str, operator_id: int, note: str = None, article_id: int = None):
    """通用审计日志。"""
    try:
        from .. import db
        from ..models import AuditLog
        al = AuditLog(article_id=article_id, operator_id=operator_id, action=action, note=note)
        db.session.add(al)
        db.session.commit()
    except Exception:
        try:
            from .. import db
            db.session.rollback()
        except Exception:
            pass


def compute_etag(obj) -> str:
    """根据对象（dict/列表/字符串）生成稳定 ETag。"""
    try:
        if isinstance(obj, (dict, list)):
            raw = json.dumps(obj, sort_keys=True, separators=(',',':'), ensure_ascii=False)
        else:
            raw = str(obj)
        h = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:32]
        return 'W/"'+h+'"'
    except Exception:
        return 'W/"fallback"'
