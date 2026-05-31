"""Pydantic 请求/响应模型"""

from pydantic import BaseModel, field_validator

try:
    from pydantic import ValidationError
except Exception:
    class ValidationError(Exception):
        pass


class ArticleCreateModel(BaseModel):
    title: str
    slug: str | None = None
    content_md: str | None = ''
    summary: str | None = None
    seo_title: str | None = None
    seo_desc: str | None = None
    featured_image: str | None = None
    featured_focal_x: float | None = None
    featured_focal_y: float | None = None
    category_id: int | None = None
    scheduled_at: str | None = None
    tags: list[str] | None = None

    @field_validator('featured_image')
    @classmethod
    def featured_optional(cls, v):
        return v.strip() if v else None

    @field_validator('title')
    @classmethod
    def title_ok(cls, v):
        v = (v or '').strip()
        if not v:
            raise ValueError('title required')
        if len(v) > 200:
            raise ValueError('title too long')
        return v

    @field_validator('summary')
    @classmethod
    def summary_ok(cls, v):
        if v and len(v) > 500:
            raise ValueError('summary too long')
        return v

    @field_validator('tags')
    @classmethod
    def tags_ok(cls, v):
        if not v:
            return []
        if len(v) > 10:
            raise ValueError('too many tags (max 10)')
        cleaned = []
        for t in v:
            t2 = (t or '').strip()
            if not t2:
                continue
            if len(t2) > 30:
                raise ValueError('tag too long')
            cleaned.append(t2)
        return cleaned

    @field_validator('featured_focal_x', 'featured_focal_y')
    @classmethod
    def focal_ok(cls, v):
        if v is None:
            return v
        if v < 0 or v > 1:
            raise ValueError('focal must be between 0 and 1')
        return v


class ArticleUpdateModel(ArticleCreateModel):
    title: str | None = None
    status: str | None = None
