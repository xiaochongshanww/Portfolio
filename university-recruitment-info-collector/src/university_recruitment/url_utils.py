"""URL normalization and stable job ID generation."""

import hashlib
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Tracking/noise parameters to always drop
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "spm", "from", "ref", "referrer", "source", "trackingid",
    "sessionid", "timestamp", "_t", "t", "rand", "random", "nocache",
}


def canonicalize_url(url: str) -> str:
    """Produce a stable canonical URL.

    - Lowercase scheme and hostname
    - Remove fragment
    - Remove default ports (80, 443)
    - Strip trailing slash except root
    - Preserve unknown query parameters
    - Drop known tracking/noise parameters
    - Sort query keys and repeated values
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
    """Generate a stable job ID from a canonicalized URL."""
    canonical = canonicalize_url(source_url)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return f"job-{digest[:24]}"


def build_position_job_id(canonical_url: str, position_raw: str, department: str | None = None) -> str:
    """Generate a stable job ID for a single position within a multi-position notice.

    Different positions in the same notice get different IDs.
    Same position in different orders still gets the same ID.
    """
    identity = "|".join([
        canonicalize_url(canonical_url),
        " ".join(position_raw.strip().lower().split()),
        (department or "").strip().lower(),
    ])
    digest = hashlib.sha256(identity.encode()).hexdigest()
    return f"pos-{digest[:24]}"


# Backward-compatible aliases
generate_job_id = build_job_id


def content_hash(text: str) -> str:
    """Generate a SHA-256 hash of normalized content text."""
    normalized = " ".join(text.split()).strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()
