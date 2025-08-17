"""performance composite indexes

Revision ID: 0003_perf_indexes
Revises: 0002_add_audit
Create Date: 2025-08-11
"""
from alembic import op
import sqlalchemy as sa

revision = '0003_perf_indexes'
down_revision = '0002_add_audit'
branch_labels = None
depends_on = None

def upgrade():
    # Articles composite indexes to accelerate listing & filtering
    try:
        op.create_index('ix_articles_status_published_at', 'articles', ['status','published_at'])
    except Exception:
        pass
    try:
        op.create_index('ix_articles_author_published_at', 'articles', ['author_id','published_at'])
    except Exception:
        pass
    try:
        op.create_index('ix_articles_category_published_at', 'articles', ['category_id','published_at'])
    except Exception:
        pass
    # Comments composite for moderation & display order
    try:
        op.create_index('ix_comments_article_status_created', 'comments', ['article_id','status','created_at'])
    except Exception:
        pass
    # Likes & bookmarks separate index on article_id for fast count (PK order user_id,article_id not ideal for article aggregation)
    try:
        op.create_index('ix_article_likes_article', 'article_likes', ['article_id'])
    except Exception:
        pass
    try:
        op.create_index('ix_article_bookmarks_article', 'article_bookmarks', ['article_id'])
    except Exception:
        pass
    # NOTE: future migration may add index for articles.views_count hot ranking

def downgrade():
    for name in [
        'ix_article_bookmarks_article',
        'ix_article_likes_article',
        'ix_comments_article_status_created',
        'ix_articles_category_published_at',
        'ix_articles_author_published_at',
        'ix_articles_status_published_at',
    ]:
        try:
            op.drop_index(name, table_name=None)
        except Exception:
            pass
