"""Add log management tables

Revision ID: 0009_add_log_management_tables
Revises: 0008_add_visitor_stats
Create Date: 2025-08-26 14:36:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '0009_add_log_management_tables'
down_revision = '0008_add_visitor_stats'
branch_labels = None
depends_on = None


def upgrade():
    # Create log_entries table
    op.create_table(
        'log_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('level', sa.String(length=10), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text().with_variant(mysql.LONGTEXT(), 'mysql'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('request_id', sa.String(length=36), nullable=True),
        sa.Column('endpoint', sa.String(length=200), nullable=True),
        sa.Column('method', sa.String(length=10), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for log_entries
    op.create_index('idx_level_timestamp', 'log_entries', ['level', 'timestamp'])
    op.create_index('idx_source_timestamp', 'log_entries', ['source', 'timestamp'])
    op.create_index('idx_user_timestamp', 'log_entries', ['user_id', 'timestamp'])
    op.create_index('idx_request_id', 'log_entries', ['request_id'])
    op.create_index('idx_endpoint_timestamp', 'log_entries', ['endpoint', 'timestamp'])
    op.create_index(op.f('ix_log_entries_level'), 'log_entries', ['level'])
    op.create_index(op.f('ix_log_entries_source'), 'log_entries', ['source'])
    op.create_index(op.f('ix_log_entries_timestamp'), 'log_entries', ['timestamp'])
    op.create_index(op.f('ix_log_entries_user_id'), 'log_entries', ['user_id'])
    
    # Create log_configs table
    op.create_table(
        'log_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_key', sa.String(length=50), nullable=False),
        sa.Column('config_value', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key')
    )
    
    op.create_index(op.f('ix_log_configs_config_key'), 'log_configs', ['config_key'])
    
    # Insert default log configurations
    op.execute("""
        INSERT INTO log_configs (config_key, config_value, description, created_at, updated_at)
        VALUES 
        ('log_level', 'INFO', '系统日志级别', NOW(), NOW()),
        ('max_log_days', '30', '日志保留天数', NOW(), NOW()),
        ('enable_user_logs', 'true', '启用用户行为日志', NOW(), NOW()),
        ('enable_api_logs', 'true', '启用API访问日志', NOW(), NOW()),
        ('enable_error_logs', 'true', '启用错误日志', NOW(), NOW())
    """)


def downgrade():
    # Drop log_configs table
    op.drop_index(op.f('ix_log_configs_config_key'), table_name='log_configs')
    op.drop_table('log_configs')
    
    # Drop log_entries indexes
    op.drop_index(op.f('ix_log_entries_user_id'), table_name='log_entries')
    op.drop_index(op.f('ix_log_entries_timestamp'), table_name='log_entries')
    op.drop_index(op.f('ix_log_entries_source'), table_name='log_entries')
    op.drop_index(op.f('ix_log_entries_level'), table_name='log_entries')
    op.drop_index('idx_endpoint_timestamp', table_name='log_entries')
    op.drop_index('idx_request_id', table_name='log_entries')
    op.drop_index('idx_user_timestamp', table_name='log_entries')
    op.drop_index('idx_source_timestamp', table_name='log_entries')
    op.drop_index('idx_level_timestamp', table_name='log_entries')
    
    # Drop log_entries table
    op.drop_table('log_entries')