"""add focal point fields to article featured image

Revision ID: 0005_add_article_focal_fields
Revises: 0004_add_article_views_count
Create Date: 2025-08-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0005_add_article_focal_fields'
down_revision = '0004_add_article_views_count'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('articles') as batch:
        batch.add_column(sa.Column('featured_focal_x', sa.Float(), nullable=True))
        batch.add_column(sa.Column('featured_focal_y', sa.Float(), nullable=True))


def downgrade():
    with op.batch_alter_table('articles') as batch:
        batch.drop_column('featured_focal_y')
        batch.drop_column('featured_focal_x')
