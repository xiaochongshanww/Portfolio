"""use longtext for article content

Revision ID: 0006_use_longtext_for_article
Revises: 0005_add_article_focal_fields
Create Date: 2025-08-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '0006_use_longtext_for_article'
down_revision = '0005_add_article_focal_fields'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'sqlite':
        # SQLite: 使用 batch_alter_table 恢复兼容（不尝试设置 MySQL 专有类型）
        with op.batch_alter_table('articles') as batch_op:
            batch_op.alter_column('content_md', existing_type=sa.Text(), type_=sa.Text(), nullable=True)
            batch_op.alter_column('content_html', existing_type=sa.Text(), type_=sa.Text(), nullable=True)
        with op.batch_alter_table('article_versions') as batch_op:
            batch_op.alter_column('content_md', existing_type=sa.Text(), type_=sa.Text(), nullable=True)
            batch_op.alter_column('content_html', existing_type=sa.Text(), type_=sa.Text(), nullable=True)
    else:
        # MySQL / 其他支持 LONGTEXT 的方言：使用 LONGTEXT
        with op.batch_alter_table('articles') as batch_op:
            batch_op.alter_column('content_md', existing_type=sa.Text(), type_=mysql.LONGTEXT(), nullable=True)
            batch_op.alter_column('content_html', existing_type=sa.Text(), type_=mysql.LONGTEXT(), nullable=True)
        with op.batch_alter_table('article_versions') as batch_op:
            batch_op.alter_column('content_md', existing_type=sa.Text(), type_=mysql.LONGTEXT(), nullable=True)
            batch_op.alter_column('content_html', existing_type=sa.Text(), type_=mysql.LONGTEXT(), nullable=True)

def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'sqlite':
        # SQLite 上无需变化（保持 Text）
        return
    else:
        with op.batch_alter_table('articles') as batch_op:
            batch_op.alter_column('content_md', existing_type=mysql.LONGTEXT(), type_=sa.Text(), nullable=True)
            batch_op.alter_column('content_html', existing_type=mysql.LONGTEXT(), type_=sa.Text(), nullable=True)
        with op.batch_alter_table('article_versions') as batch_op:
            batch_op.alter_column('content_md', existing_type=mysql.LONGTEXT(), type_=sa.Text(), nullable=True)
            batch_op.alter_column('content_html', existing_type=mysql.LONGTEXT(), type_=sa.Text(), nullable=True)