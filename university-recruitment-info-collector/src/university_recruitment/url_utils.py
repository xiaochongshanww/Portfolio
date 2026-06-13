"""URL normalization and stable job ID generation."""

import hashlib
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Query parameters worth preserving in canonical URLs
_PRESERVE_PARAMS = {
    "id", "articleid", "article_id", "aid", "cid", "pid", "newsid",
    "infoid", "contentid", "pageid", "postid", "recruitid",
}


def normalize_url(url: str) -> str:
    """Produce a stable canonical form of a URL.

    - Lowercase scheme and host
    - Remove fragment
    - Strip trailing slash from path (except root "/")
    - Sort query parameters, keep only business-meaningful ones
    """
    parsed = urlparse(str(url))
    scheme = parsed.scheme.lower()
    netloc = parsed.hostname or ""
    if parsed.port and parsed.port not in (80, 443):
        netloc += f":{parsed.port}"
    path = parsed.path.rstrip("/") or "/"

    # Keep only meaningful query parameters, sorted
    if parsed.query:
        qs = parse_qs(parsed.query, keep_blank_values=False)
        filtered = {k: sorted(v) for k, v in qs.items() if k.lower() in _PRESERVE_PARAMS}
        query = urlencode(filtered, doseq=True) if filtered else ""
    else:
        query = ""

    return urlunparse((scheme, netloc, path, "", query, ""))


def generate_job_id(canonical_url: str) -> str:
    """Generate a stable job ID from a canonical URL.

    Uses SHA-256 for collision resistance, with a human-readable prefix.
    """
    digest = hashlib.sha256(canonical_url.encode()).hexdigest()
    return f"job-{digest[:24]}"


def content_hash(text: str) -> str:
    """Generate a SHA-256 hash of normalized content text."""
    normalized = " ".join(text.split()).strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()
