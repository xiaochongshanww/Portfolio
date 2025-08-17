"""add article views_count

Revision ID: 0004_add_article_views_count
Revises: 0003_perf_indexes
Create Date: 2025-08-11
"""
from alembic import op
import sqlalchemy as sa

revision = '0004_add_article_views_count'
down_revision = '0003_perf_indexes'
branch_labels = None
depends_on = None

def upgrade():
    try:
        op.add_column('articles', sa.Column('views_count', sa.Integer(), server_default='0', nullable=False))
        op.create_index('ix_articles_views_count', 'articles', ['views_count'])
    except Exception:
        pass

def downgrade():
    try:
        op.drop_index('ix_articles_views_count', table_name='articles')
    except Exception:
        pass
    try:
        op.drop_column('articles', 'views_count')
    except Exception:
        pass
