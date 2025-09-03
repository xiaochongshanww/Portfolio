"""Nullable backup record id

Revision ID: 0013_nullable_backup_id
Revises: 0012_add_media_library_models
Create Date: 2025-09-01 13:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0013_nullable_backup_id'
down_revision = '0012_add_media_library_models'
branch_labels = None
depends_on = None


def upgrade():
    """修改 backup_record_id 字段为可空，支持物理恢复"""
    # 修改 backup_record_id 字段允许为空
    op.alter_column('restore_records', 'backup_record_id',
                    existing_type=sa.Integer(),
                    nullable=True)


def downgrade():
    """回滚：将 backup_record_id 字段改回不可空"""
    # 首先清理 NULL 值（如果有的话）
    op.execute("UPDATE restore_records SET backup_record_id = 0 WHERE backup_record_id IS NULL")
    
    # 然后修改字段为不可空
    op.alter_column('restore_records', 'backup_record_id',
                    existing_type=sa.Integer(),
                    nullable=False)