"""Convert Shanghai-timezone datetimes to UTC

Revision ID: 0014_convert_shanghai_to_utc
Revises: 0013_nullable_backup_id
Create Date: 2026-08-15 16:00:00.000000

背景: models.py 部分表此前默认存上海时区(UTC+8)的 naive datetime,
现已统一为 UTC。本迁移把存量上海时区 DATETIME 行减 8 小时转为 UTC。

注意:
- 只迁移 DATETIME 列; DATE 列(visitor_stats.visited_date 等)保持上海日边界。
- 迁移应在应用写入 UTC 之前执行(flask db upgrade 先行)。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0014_convert_shanghai_to_utc'
down_revision = '0013_nullable_backup_id'
branch_labels = None
depends_on = None

# (table, column) —— 曾以 SHANGHAI_TZ 默认/写入的 DATETIME 列
TABLES = [
    ("article_likes", "created_at"),
    ("article_bookmarks", "created_at"),
    ("visitor_stats", "first_visit_time"),
    ("visitor_stats", "last_visit_time"),
    ("daily_stats", "created_at"),
    ("daily_stats", "updated_at"),
    ("log_entries", "timestamp"),
    ("log_entries", "created_at"),
    ("log_configs", "created_at"),
    ("log_configs", "updated_at"),
    ("backup_records", "created_at"),
    ("backup_records", "started_at"),
    ("backup_records", "completed_at"),
    ("restore_records", "created_at"),
    ("restore_records", "started_at"),
    ("restore_records", "completed_at"),
]


def _shift(bind, hours):
    dialect = bind.dialect.name
    for table, col in TABLES:
        if dialect == "sqlite":
            op.execute(
                sa.text(
                    f'UPDATE "{table}" SET "{col}" = '
                    f'datetime("{col}", \'{hours:+d} hours\') '
                    f'WHERE "{col}" IS NOT NULL'
                )
            )
        else:  # mysql / mariadb
            fn = "DATE_SUB" if hours < 0 else "DATE_ADD"
            op.execute(
                sa.text(
                    f'UPDATE `{table}` SET `{col}` = '
                    f'{fn}(`{col}`, INTERVAL {abs(hours)} HOUR) '
                    f'WHERE `{col}` IS NOT NULL'
                )
            )


def upgrade():
    """存量上海时区行 -> UTC(减 8 小时)"""
    bind = op.get_bind()
    _shift(bind, -8)


def downgrade():
    """回滚: UTC -> 上海时区(加 8 小时)"""
    bind = op.get_bind()
    _shift(bind, +8)
