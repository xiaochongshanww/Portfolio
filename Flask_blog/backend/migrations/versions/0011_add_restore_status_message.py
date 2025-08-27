"""add restore status message

Revision ID: 0011
Revises: 0010
Create Date: 2025-08-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0011_add_restore_status_message'
down_revision = '0010_add_backup_system_tables'
branch_labels = None
depends_on = None

def upgrade():
    """Add status_message field to restore_records table"""
    # Add status_message column to restore_records table
    op.add_column('restore_records', sa.Column('status_message', sa.String(200), nullable=True))

def downgrade():
    """Remove status_message field from restore_records table"""
    # Remove status_message column from restore_records table
    op.drop_column('restore_records', 'status_message')