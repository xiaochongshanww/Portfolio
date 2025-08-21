"""Content rendering & sanitization service.

Provides:
- render_markdown(md_text) -> raw HTML (unsanitized)
- sanitize_html(html) -> safe HTML (bleach cleaned)
- render_and_sanitize(md_text) -> safe HTML in one step

Design:
- Separate rendering & sanitization to allow future caching / security auditing.
- Centralize ALLOWED_* so other modules (e.g., feeds, previews) can reuse.
"""
from __future__ import annotations
from typing import Iterable
import re
from urllib.parse import urlparse, parse_qs
import markdown as md
import bleach

# 兼容: 某些 bleach 版本可能没有 build_rel_callback；提供回退实现
try:  # pragma: no cover - 简单探测
    from bleach.linkifier import build_rel_callback as _build_rel_callback
except Exception:  # noqa
    _build_rel_callback = None

# Core markdown extensions (codehilite adds Pygments classes; keep span/class allowed)
MD_EXTENSIONS: list[str] = [
    'fenced_code',
    'codehilite',
    'tables',
    'toc'
]

# Allowed HTML tags (start from bleach default, extend)
# 新增: iframe (受限白名单域) + div 已用于自定义 embed 包裹
ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS).union({
    'p','pre','code','img','h1','h2','h3','h4','h5','h6','span','blockquote','hr','br',
    'ul','ol','li','strong','em','table','thead','tbody','tr','th','td','a','div','iframe'
})

# Allowed attributes per tag
ALLOWED_ATTRS: dict[str, Iterable[str]] = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    'img': ['src','alt','title'],
    'a': ['href','title','rel','target'],
    'code': ['class'],  # language-xxx classes from Pygments / codehilite
    'span': ['class'],
    'div': ['class','data-gist'],  # data-gist 用于 gist 动态加载
    'iframe': ['src','width','height','allow','allowfullscreen','loading','referrerpolicy','frameborder'],
}

# Allowed URL protocols
ALLOWED_PROTOCOLS = [
    'http','https','mailto'
]

# Rel attribute to enforce on links for security (can be tuned)
DEFAULT_LINK_REL = 'nofollow noopener noreferrer'

VIDEO_HOSTS = {
    'youtu.be': 'youtube',
    'www.youtube.com': 'youtube',
    'youtube.com': 'youtube',
    'player.bilibili.com': 'bilibili',
    'www.bilibili.com': 'bilibili',
    'bilibili.com': 'bilibili',
    'vimeo.com': 'vimeo',
    'www.vimeo.com': 'vimeo',
    'player.vimeo.com': 'vimeo'
}

ALLOWED_IFRAME_HOSTS = {
    'www.youtube.com', 'youtube.com', 'player.bilibili.com', 'player.vimeo.com'
}

def _build_video_iframe(url: str) -> str:
    """Given a raw video page url, produce an embeddable iframe snippet (raw, will be sanitized)."""
    try:
        parsed = urlparse(url)
    except Exception:  # pragma: no cover - 容错
        return ''
    host = parsed.hostname or ''
    kind = VIDEO_HOSTS.get(host)
    video_src = ''
    if kind == 'youtube':
        vid = ''
        if host in {'youtube.com','www.youtube.com'}:
            qs = parse_qs(parsed.query)
            vid = qs.get('v', [''])[0]
        if host == 'youtu.be':
            vid = parsed.path.strip('/')
        if vid:
            video_src = f"https://www.youtube.com/embed/{vid}"
    elif kind == 'bilibili':
        # 解析 BV 号（简单匹配）
        m = re.search(r'(BV[0-9A-Za-z]+)', parsed.path)
        if m:
            bvid = m.group(1)
            video_src = f"https://player.bilibili.com/player.html?bvid={bvid}&page=1"
    elif kind == 'vimeo':
        # Vimeo: https://vimeo.com/<id>  or https://player.vimeo.com/video/<id>
        vid_match = re.search(r'/video/(\d+)', parsed.path)
        if not vid_match:
            vid_match = re.search(r'/(\d+)', parsed.path)
        if vid_match:
            vid = vid_match.group(1)
            video_src = f"https://player.vimeo.com/video/{vid}"
    if not video_src:
        return ''
    # 包裹 div 方便前端自适应
    return (
        '<div class="video-embed">'
        f'<iframe src="{video_src}" loading="lazy" allowfullscreen frameborder="0" '
        'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
        'referrerpolicy="no-referrer-when-downgrade"></iframe>'
        '</div>'
    )

SHORTCODE_RE = re.compile(r'^:::(video|gist)\s+(\S+)\s*:::$')

def _preprocess_shortcodes(text: str) -> str:
    """Convert :::video <url>::: / :::gist <url>::: lines into HTML placeholders before markdown render."""
    out_lines: list[str] = []
    for line in text.splitlines():
        m = SHORTCODE_RE.match(line.strip())
        if m:
            kind, url = m.group(1), m.group(2)
            if kind == 'video':
                iframe_html = _build_video_iframe(url)
                if iframe_html:
                    out_lines.append(iframe_html)
                else:
                    out_lines.append(line)  # 回退保留原始文本
            elif kind == 'gist':
                # Gist: <div class="embed-gist" data-gist="..." /> 由前端动态拉取
                out_lines.append(f'<div class="embed-gist" data-gist="{url}"></div>')
        else:
            out_lines.append(line)
    return '\n'.join(out_lines)

def render_markdown(md_text: str | None) -> str:
    """Render markdown text to raw HTML (WITHOUT sanitization). 处理自定义短代码。"""
    if not md_text:
        return ''
    processed = _preprocess_shortcodes(md_text)
    return md.markdown(processed, extensions=MD_EXTENSIONS, output_format='html5')

def sanitize_html(raw_html: str | None) -> str:
    """Sanitize arbitrary HTML string to safe subset using bleach."""
    if not raw_html:
        return ''
    cleaned = bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True
    )
    # Linkify AFTER cleaning (so we don't accidentally allow scripts). Then sanitize again lightly.
    # 链接 rel 处理：优先使用官方 build_rel_callback，否则使用本地回退
    if _build_rel_callback:
        rel_cb = _build_rel_callback(fixed_rel=DEFAULT_LINK_REL)
    else:
        def rel_cb(attrs, new=False):  # noqa: D401
            # 合并/追加安全 rel 标记
            rel = attrs.get('rel') or ''
            existing = set(filter(None, rel.split()))
            for t in DEFAULT_LINK_REL.split():
                existing.add(t)
            attrs['rel'] = ' '.join(sorted(existing))
            return attrs
    # 修复bleach.linkify的版本兼容性问题
    try:
        cleaned = bleach.linkify(cleaned, callbacks=[rel_cb])
    except (ValueError, TypeError) as e:
        # 如果linkify失败，跳过自动链接化功能，但继续清洗HTML
        print(f"警告: bleach.linkify失败，跳过自动链接化: {e}")
        pass
    
    # Second pass to ensure linkify additions are safe
    cleaned = bleach.clean(
        cleaned,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True
    )
    # 额外过滤 iframe 源域名（仅允许白名单）
    def _filter_iframes(html: str) -> str:
        pattern = re.compile(r'<iframe\b.*?</iframe>', re.IGNORECASE | re.DOTALL)
        def repl(m):
            block = m.group(0)
            src_m = re.search(r'src=["\']([^"\']+)["\']', block, re.IGNORECASE)
            if not src_m:
                return ''
            src_url = src_m.group(1)
            try:
                host = urlparse(src_url).hostname or ''
            except Exception:
                return ''
            if host not in ALLOWED_IFRAME_HOSTS:
                return ''
            return block
        return pattern.sub(repl, html)
    cleaned = _filter_iframes(cleaned)
    return cleaned

def render_and_sanitize_simple(md_text: str | None) -> str:
    """简化版本：仅渲染Markdown，跳过problematic linkify步骤"""
    if not md_text:
        return ''
    
    try:
        # 只进行基本的Markdown渲染
        html = render_markdown(md_text)
        
        # 简单的HTML清洗，跳过linkify
        cleaned = bleach.clean(
            html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRS,
            protocols=ALLOWED_PROTOCOLS,
            strip=True
        )
        return cleaned
    except Exception as e:
        print(f"Markdown渲染失败，返回纯文本: {e}")
        # 如果所有处理都失败，返回纯文本
        return bleach.clean(md_text or '', tags=[], attributes={}, strip=True)

def render_and_sanitize(md_text: str | None) -> str:
    """Convenience: render markdown then sanitize."""
    try:
        return sanitize_html(render_markdown(md_text))
    except Exception as e:
        print(f"完整HTML处理失败，使用简化版本: {e}")
        return render_and_sanitize_simple(md_text)

__all__ = [
    'render_markdown',
    'sanitize_html',
    'render_and_sanitize',
    'ALLOWED_TAGS',
    'ALLOWED_ATTRS',
    'ALLOWED_PROTOCOLS'
]
