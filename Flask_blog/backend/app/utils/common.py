import markdown as md
import bleach
import hashlib
import json

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
