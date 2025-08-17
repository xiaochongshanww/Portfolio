"""init schema

Revision ID: 0001_init
Revises: 
Create Date: 2025-08-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False, server_default='author', index=True),
        sa.Column('nickname', sa.String(length=80)),
        sa.Column('bio', sa.Text()),
        sa.Column('avatar', sa.String(length=255)),
        sa.Column('social_links', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)'))
    )

    op.create_table('categories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=150), unique=True, index=True),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('categories.id')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)'))
    )

    op.create_table('tags',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('slug', sa.String(length=120), unique=True, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)'))
    )

    op.create_table('articles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('author_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), unique=True, index=True),
        sa.Column('content_md', sa.Text()),
        sa.Column('content_html', sa.Text()),
        sa.Column('status', sa.String(length=32), index=True, server_default='draft'),
        sa.Column('seo_title', sa.String(length=255)),
        sa.Column('seo_desc', sa.String(length=255)),
        sa.Column('summary', sa.String(length=500)),
        sa.Column('featured_image', sa.String(length=255)),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('categories.id'), index=True),
        sa.Column('scheduled_at', sa.DateTime()),
        sa.Column('published_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default=sa.text('0'), index=True)
    )

    op.create_table('article_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), nullable=False, index=True),
        sa.Column('version_no', sa.Integer(), nullable=False),
        sa.Column('content_md', sa.Text()),
        sa.Column('content_html', sa.Text()),
        sa.Column('editor_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)'))
    )
    op.create_index('ix_article_versions_article_version', 'article_versions', ['article_id','version_no'])

    op.create_table('comments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), nullable=False, index=True),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('comments.id')),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=16), index=True, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)'))
    )

    op.create_table('article_tags',
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), primary_key=True),
        sa.Column('tag_id', sa.Integer(), sa.ForeignKey('tags.id'), primary_key=True)
    )

    op.create_table('article_likes',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)'))
    )

    op.create_table('article_bookmarks',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)'))
    )


def downgrade():
    op.drop_table('article_bookmarks')
    op.drop_table('article_likes')
    op.drop_table('article_tags')
    op.drop_table('comments')
    op.drop_index('ix_article_versions_article_version', table_name='article_versions')
    op.drop_table('article_versions')
    op.drop_table('articles')
    op.drop_table('tags')
    op.drop_table('categories')
    op.drop_table('users')
