"""Create projects table (P2 Project entity)

Revision ID: 0016_create_projects
Revises: 0015_add_comments_deleted
Create Date: 2026-08-24 12:00:00.000000

双兼容说明(SQLite + MySQL,遵循 0014/0015 修复经验):
- 新建表不涉及 ALTER,无 batch 需求;
- 不使用 NOW() 等服务端时间函数,时间列由应用层填充;
- 长文本列使用 LONGTEXT with_variant(MySQL)。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0016_create_projects"
down_revision = "0015_add_comments_deleted"
branch_labels = None
depends_on = None

LONGTEXT = sa.Text().with_variant(sa.dialects.mysql.LONGTEXT(), "mysql")


def upgrade():
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("tag", sa.String(50), nullable=True),
        sa.Column("tech_stack", LONGTEXT, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column(
            "is_current", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("preview_type", sa.String(16), nullable=False, server_default="none"),
        sa.Column("preview_data", LONGTEXT, nullable=True),
        sa.Column("link_url", sa.String(255), nullable=True),
        sa.Column("repo_url", sa.String(255), nullable=True),
        sa.Column("motivation", LONGTEXT, nullable=True),
        sa.Column("progress", LONGTEXT, nullable=True),
        sa.Column("design_notes", LONGTEXT, nullable=True),
        sa.Column("related_article_slugs", LONGTEXT, nullable=True),
        sa.Column("changelog", LONGTEXT, nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_projects_slug", "projects", ["slug"], unique=True)
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_projects_is_current", "projects", ["is_current"])


def downgrade():
    op.drop_index("ix_projects_is_current", table_name="projects")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_index("ix_projects_slug", table_name="projects")
    op.drop_table("projects")
