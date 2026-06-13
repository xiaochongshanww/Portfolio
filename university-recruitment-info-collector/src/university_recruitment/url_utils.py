"""URL normalization and stable job ID generation."""

import hashlib
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Query parameters worth preserving in canonical URLs
_PRESERVE_PARAMS = {
    "id", "articleid", "article_id", "aid", "cid", "pid", "newsid",
    "infoid", "contentid", "pageid", "postid", "recruitid",
}

# Tracking/noise parameters to always drop
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "spm", "from", "ref", "referrer", "source", "trackingid",
    "sessionid", "timestamp", "_t", "t", "rand", "random", "nocache",
}


def canonicalize_url(url: str) -> str:
    """Produce a stable canonical form of a URL.

    - Lowercase scheme and hostname
    - Remove fragment
    - Strip trailing slash from path (except root "/")
    - Drop tracking/noise query parameters
    - Sort remaining query parameters, keep only business-meaningful ones
    """
    parsed = urlparse(str(url))
    scheme = parsed.scheme.lower()
    netloc = parsed.hostname or ""
    if parsed.port and parsed.port not in (80, 443):
        netloc += f":{parsed.port}"
    path = parsed.path.rstrip("/") or "/"

    # Filter and sort query parameters
    if parsed.query:
        qs = parse_qs(parsed.query, keep_blank_values=True)
        cleaned = {}
        for k, v in qs.items():
            key_lower = k.lower()
            if key_lower in _TRACKING_PARAMS:
                continue
            cleaned[k] = sorted(v)
        # Sort for stability regardless of original param order
        query = urlencode(sorted(cleaned.items()), doseq=True) if cleaned else ""
    else:
        query = ""

    return urlunparse((scheme, netloc, path, "", query, ""))


# Backward-compatible alias
normalize_url = canonicalize_url


def build_job_id(source_url: str) -> str:
    """Generate a stable job ID from a canonicalized URL.

    Uses SHA-256 for collision resistance, with a human-readable prefix.
    """
    canonical = canonicalize_url(source_url)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return f"job-{digest[:24]}"


# Backward-compatible alias
generate_job_id = build_job_id


def content_hash(text: str) -> str:
    """Generate a SHA-256 hash of normalized content text."""
    normalized = " ".join(text.split()).strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()
