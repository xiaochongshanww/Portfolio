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
    # 检查列是否已存在
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('articles')]
    
    if 'views_count' not in columns:
        op.add_column('articles', sa.Column('views_count', sa.Integer(), server_default='0', nullable=False))
        print("✅ Added views_count column to articles table")
    else:
        print("⚠️  views_count column already exists, skipping")
    
    # 检查索引是否已存在
    indexes = [idx['name'] for idx in inspector.get_indexes('articles')]
    if 'ix_articles_views_count' not in indexes:
        op.create_index('ix_articles_views_count', 'articles', ['views_count'])
        print("✅ Created index ix_articles_views_count")
    else:
        print("⚠️  Index ix_articles_views_count already exists, skipping")

def downgrade():
    # 安全地移除索引和列
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 移除索引
    indexes = [idx['name'] for idx in inspector.get_indexes('articles')]
    if 'ix_articles_views_count' in indexes:
        op.drop_index('ix_articles_views_count', table_name='articles')
        print("✅ Dropped index ix_articles_views_count")
    
    # 移除列
    columns = [col['name'] for col in inspector.get_columns('articles')]
    if 'views_count' in columns:
        op.drop_column('articles', 'views_count')
        print("✅ Dropped views_count column from articles table")
