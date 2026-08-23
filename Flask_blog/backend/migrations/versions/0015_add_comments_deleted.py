"""Add deleted column to comments table

Revision ID: 0015_add_comments_deleted
Revises: 0014_convert_shanghai_to_utc
Create Date: 2026-08-16 19:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0015_add_comments_deleted'
down_revision = '0014_convert_shanghai_to_utc'
branch_labels = None
depends_on = None


def upgrade():
    """补上 comments 软删除列(模型已有 deleted,0001 建表时遗漏)"""
    op.add_column('comments', sa.Column('deleted', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    op.create_index('ix_comments_deleted', 'comments', ['deleted'])


def downgrade():
    """回滚:删除 comments 软删除列"""
    op.drop_index('ix_comments_deleted', table_name='comments')
    op.drop_column('comments', 'deleted')
