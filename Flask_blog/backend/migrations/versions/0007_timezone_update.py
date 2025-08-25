"""update timezone for article likes and bookmarks to Shanghai timezone

Revision ID: 0007_timezone_update
Revises: 0006_use_longtext_for_article
Create Date: 2025-08-22 22:50:00.000000

Note: This migration only updates the model defaults for new records.
Existing records in article_likes and article_bookmarks tables remain unchanged.
New likes and bookmarks will use Shanghai timezone (UTC+8) instead of UTC.
"""
from alembic import op
import sqlalchemy as sa

revision = '0007_timezone_update'
down_revision = '0006_use_longtext_for_article'
branch_labels = None
depends_on = None

def upgrade():
    # No database schema changes needed - only model default value changes
    # This affects new ArticleLike and ArticleBookmark records created after deployment
    pass

def downgrade():
    # No database schema changes to revert
    pass