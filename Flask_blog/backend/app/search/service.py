"""搜索业务逻辑层 — 供 routes.py 编排调用。

通过 `from . import client as search_client` 引用，使测试中
`monkeypatch app.search.client.ensure_index` 仍然生效。
"""

from flask import current_app

# 模块引用以便测试 monkeypatch app.search.client.ensure_index 生效
from . import client as search_client


def build_search_params(page, size, filter_clauses, facets_wanted, sort_expr):
    """构造 MeiliSearch 搜索参数。"""
    search_params = {
        "limit": size,
        "offset": (page - 1) * size,
        "attributesToHighlight": ["title", "content"],
        "highlightPreTag": "<mark>",
        "highlightPostTag": "</mark>",
        "attributesToCrop": ["content"],
        "cropLength": 60,
        "showMatchesPosition": False,
        "showRankingScore": True,
    }
    if filter_clauses:
        search_params["filter"] = filter_clauses
    if facets_wanted:
        search_params["facets"] = facets_wanted
    if sort_expr and not sort_expr.startswith("_score"):
        search_params["sort"] = [sort_expr]
    return search_params


def parse_filters(
    status,
    tags_list,
    match_mode,
    category_id,
    author_id,
    date_from,
    date_to,
    sort,
):
    """构造过滤条件与排序表达式。"""
    filter_clauses = []
    sort_expr = None

    if status:
        filter_clauses.append(f"status = '{status}'")
    if tags_list:
        if match_mode not in ("and", "or"):
            match_mode = "and"
        if match_mode == "and":
            for t in tags_list:
                filter_clauses.append(f"tags = '{t}'")
        else:
            ors = " OR ".join([f"tags = '{t}'" for t in tags_list])
            filter_clauses.append(f"({ors})")
    if category_id and category_id.isdigit():
        filter_clauses.append(f"category_id = {category_id}")
    if author_id and author_id.isdigit():
        filter_clauses.append(f"author_id = {author_id}")
    if date_from:
        filter_clauses.append(f"published_at >= {date_from}")
    if date_to:
        filter_clauses.append(f"published_at <= {date_to}")

    if sort:
        parts = sort.split(":", 1)
        field = parts[0]
        direction = (parts[1] if len(parts) > 1 else "asc").lower()
        if field in (
            "published_at",
            "created_at",
            "likes_count",
            "views_count",
            "_score",
        ) and direction in ("asc", "desc"):
            sort_expr = f"{field}:{direction}"

    return filter_clauses, sort_expr


def _db_fallback(
    q,
    tags_list,
    match_mode,
    category_id,
    author_id,
    date_from,
    date_to,
    sort_expr,
    page,
    size,
    facets_wanted,
):
    """MeiliSearch 不可用时回退到数据库模糊查询。"""
    from sqlalchemy import desc as sqldesc
    from sqlalchemy import func, or_

    from ..models import Article, Tag

    query = Article.query.filter_by(deleted=False, status="published")
    if q.strip():
        like = f"%{q}%"
        try:
            query = query.filter(Article.title.ilike(like))
        except Exception:
            query = query.filter(Article.title.like(like))
    if not q.strip():
        query = query.filter(Article.status == "published")
    if tags_list:
        if match_mode == "and":
            for t in tags_list:
                query = query.filter(Article.tags.any(Tag.slug == t))
        else:
            query = query.filter(
                or_(*[Article.tags.any(Tag.slug == t) for t in tags_list])
            )
    if category_id and category_id.isdigit():
        query = query.filter_by(category_id=int(category_id))
    if author_id and author_id.isdigit():
        query = query.filter_by(author_id=int(author_id))
    if sort_expr and (
        sort_expr.startswith("published_at:") or sort_expr.startswith("created_at:")
    ):
        field = sort_expr.split(":", 1)[0]
        desc = sort_expr.endswith(":desc")
        col = Article.published_at if field == "published_at" else Article.created_at
        query = query.order_by(sqldesc(col) if desc else col.asc())
    elif sort_expr and sort_expr.startswith("likes_count:"):
        desc = sort_expr.endswith(":desc")
        query = query.order_by(
            sqldesc(Article.created_at) if desc else Article.created_at.asc()
        )
    elif sort_expr and sort_expr.startswith("views_count:"):
        desc = sort_expr.endswith(":desc")
        query = query.order_by(
            sqldesc(Article.published_at) if desc else Article.published_at.asc()
        )

    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    hits = [
        {
            "id": a.id,
            "title": a.title,
            "content": (a.content_md or "")[:5000],
            "tags": [t.slug for t in a.tags],
            "status": a.status,
            "category_id": a.category_id,
            "author_id": a.author_id,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "_formatted": {},
        }
        for a in items
    ]

    facets_distribution = {}
    if facets_wanted:
        base_q = query.session.query(Article).filter_by(
            deleted=False, status="published"
        )
        if date_from:
            try:
                base_q = base_q.filter(Article.published_at >= date_from)
            except Exception:
                pass
        if date_to:
            try:
                base_q = base_q.filter(Article.published_at <= date_to)
            except Exception:
                pass
        if "category_id" in facets_wanted:
            rows = (
                base_q.with_entities(Article.category_id, func.count(Article.id))
                .group_by(Article.category_id)
                .all()
            )
            facets_distribution["category_id"] = {
                str(r[0]): r[1] for r in rows if r[0] is not None
            }
        if "author_id" in facets_wanted:
            rows = (
                base_q.with_entities(Article.author_id, func.count(Article.id))
                .group_by(Article.author_id)
                .all()
            )
            facets_distribution["author_id"] = {
                str(r[0]): r[1] for r in rows if r[0] is not None
            }
        if "tags" in facets_wanted:
            tag_rows = (
                query.session.query(Tag.slug, func.count(Tag.slug))
                .join(Article.tags)
                .filter(Article.deleted.is_(False), Article.status == "published")
                .group_by(Tag.slug)
                .all()
            )
            facets_distribution["tags"] = {r[0]: r[1] for r in tag_rows}

    return total, hits, facets_distribution


def perform_search(
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
):
    """执行搜索：优先 MeiliSearch，失败或测试空结果时回退 DB。

    返回 (total, hits, facets_distribution, used_fallback, sort_expr)。
    """
    filter_clauses, sort_expr = parse_filters(
        status,
        tags_list,
        match_mode,
        category_id,
        author_id,
        date_from,
        date_to,
        sort,
    )
    search_params = build_search_params(
        page, size, filter_clauses, facets_wanted, sort_expr
    )

    total = 0
    hits = []
    facets_distribution = {}
    used_fallback = False

    force_fallback = bool(current_app.config.get("SEARCH_FORCE_FALLBACK"))
    if not force_fallback:
        try:
            idx = search_client.ensure_index()
            search_query = q or "*"
            res = idx.search(search_query, search_params)
            total = res.get("estimatedTotalHits", 0)
            hits = res.get("hits", [])
            facets_distribution = res.get("facetsDistribution") or {}
        except Exception:
            force_fallback = True
        if (
            not force_fallback
            and current_app.config.get("TESTING")
            and q.strip()
            and total == 0
        ):
            force_fallback = True
    if force_fallback:
        used_fallback = True
        total, hits, facets_distribution = _db_fallback(
            q,
            tags_list,
            match_mode,
            category_id,
            author_id,
            date_from,
            date_to,
            sort_expr,
            page,
            size,
            facets_wanted,
        )

    return total, hits, facets_distribution, used_fallback, sort_expr


def normalize_hits(hits, used_fallback, sort_expr):
    """将原始命中结果规范化为前端数据结构。"""
    normalized = []
    for h in hits:
        hl = h.get("_formatted", {})
        score = None
        if (
            not used_fallback
            and sort_expr != "views_count:desc"
            and sort_expr != "views_count:asc"
        ):
            score = h.get("_rankingScore")
        normalized.append(
            {
                "id": h.get("id"),
                "title": hl.get("title") or h.get("title"),
                "slug": h.get("slug"),
                "status": h.get("status"),
                "published_at": h.get("published_at"),
                "created_at": h.get("created_at"),
                "tags": h.get("tags", []),
                "likes_count": h.get("likes_count"),
                "views_count": h.get("views_count"),
                "highlight": {"title": hl.get("title"), "content": hl.get("content")},
                "score": score,
                "excerpt": (
                    (hl.get("content") or "")
                    if hl.get("content")
                    else (h.get("content") or "")[:180]
                ),
            }
        )
    return normalized
