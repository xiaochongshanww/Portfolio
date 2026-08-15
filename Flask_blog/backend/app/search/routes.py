import hashlib
import json

from flask import Blueprint, current_app, jsonify, request
from flask_limiter.util import get_remote_address

from .. import limiter, redis_client
from ..utils import compute_etag
from .service import normalize_hits, perform_search

# 指标
try:
    from .. import (
        CACHE_HIT_TOTAL,
        CACHE_MISS_TOTAL,
        SEARCH_QUERIES_TOTAL,
        SEARCH_ZERO_RESULT_TOTAL,
    )
except Exception:
    SEARCH_QUERIES_TOTAL = None
    SEARCH_ZERO_RESULT_TOTAL = None
    CACHE_HIT_TOTAL = None
    CACHE_MISS_TOTAL = None

search_bp = Blueprint("search", __name__)


@search_bp.route("/", methods=["GET"])
@limiter.limit("120/minute", key_func=get_remote_address)
@limiter.limit("30/minute")
def search():
    raw_q = request.args.get("q", "")
    q = (raw_q or "")[:200]
    base_params = sorted([(k, v) for k, v in request.args.items()])
    key_raw = json.dumps([q, base_params], ensure_ascii=False)
    key_hash = hashlib.md5(key_raw.encode("utf-8")).hexdigest()
    cache_key = f"search:{key_hash}"
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            try:
                resp_cached = json.loads(cached)
                if CACHE_HIT_TOTAL:
                    try:
                        CACHE_HIT_TOTAL.labels("search").inc()
                    except Exception:
                        pass
                etag = compute_etag(resp_cached.get("data"))
                if request.headers.get("If-None-Match") == etag:
                    return ("", 304, {"ETag": etag})
                resp = jsonify(resp_cached)
                resp.headers["ETag"] = etag
                return resp
            except Exception:
                pass
        else:
            if CACHE_MISS_TOTAL:
                try:
                    CACHE_MISS_TOTAL.labels("search").inc()
                except Exception:
                    pass

    def to_int(name, default, min_v=1, max_v=1000):
        try:
            v = int(request.args.get(name, default))
            if v < min_v:
                v = min_v
            if v > max_v:
                v = max_v
            return v
        except Exception:
            return default

    page = to_int("page", 1)
    size = to_int("page_size", 10, 1, 100)

    status = request.args.get("status")
    single_tag = request.args.get("tag")
    multi_tags_raw = request.args.get("tags")
    match_mode = (request.args.get("match_mode") or "and").lower()
    tags_list = []
    if multi_tags_raw:
        tags_list = [t.strip() for t in multi_tags_raw.split(",") if t.strip()][:10]
    elif single_tag:
        tags_list = [single_tag]
    category_id = request.args.get("category_id")
    author_id = request.args.get("author_id")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    facets_param = request.args.get("facets")
    sort = request.args.get("sort")

    facets_wanted = []
    if facets_param:
        facets_wanted = [f.strip() for f in facets_param.split(",") if f.strip()]

    total, hits, facets_distribution, used_fallback, sort_expr = perform_search(
        q,
        page,
        size,
        status,
        tags_list,
        match_mode,
        category_id,
        author_id,
        date_from,
        date_to,
        facets_wanted,
        sort,
    )

    if SEARCH_QUERIES_TOTAL:
        try:
            SEARCH_QUERIES_TOTAL.inc()
        except Exception:
            pass
    if total == 0 and SEARCH_ZERO_RESULT_TOTAL:
        try:
            SEARCH_ZERO_RESULT_TOTAL.inc()
        except Exception:
            pass

    normalized = normalize_hits(hits, used_fallback, sort_expr)
    has_next = (page * size) < total
    resp_obj = {
        "code": 0,
        "data": {
            "total": total,
            "page": page,
            "page_size": size,
            "has_next": has_next,
            "query": q,
            "filters": {
                "status": status,
                "tags": tags_list,
                "match_mode": match_mode,
                "sort": sort,
                "category_id": category_id,
                "author_id": author_id,
                "date_from": date_from,
                "date_to": date_to,
            },
            "list": normalized,
            "facets": facets_distribution,
        },
        "message": "ok",
    }
    etag = compute_etag(resp_obj["data"])
    if request.headers.get("If-None-Match") == etag:
        return ("", 304, {"ETag": etag})
    if redis_client:
        redis_client.setex(
            cache_key,
            current_app.config.get("CACHE_SEARCH_TTL", 60),
            json.dumps(resp_obj, ensure_ascii=False),
        )
    resp = jsonify(resp_obj)
    resp.headers["ETag"] = etag
    return resp
