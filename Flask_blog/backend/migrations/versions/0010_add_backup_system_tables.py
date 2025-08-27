"""Add backup system tables

Revision ID: 0010
Revises: 0009
Create Date: 2025-08-26 17:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '0010_add_backup_system_tables'
down_revision = '0009_add_log_management_tables'
branch_labels = None
depends_on = None


def upgrade():
    # 创建备份记录表
    op.create_table('backup_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backup_id', sa.String(length=50), nullable=False),
        sa.Column('backup_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('compressed_size', sa.BigInteger(), nullable=True),
        sa.Column('compression_ratio', sa.Float(), nullable=True),
        sa.Column('encryption_enabled', sa.Boolean(), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=True),
        sa.Column('storage_providers', sa.Text(), nullable=True),
        sa.Column('extra_data', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('files_count', sa.Integer(), nullable=True),
        sa.Column('databases_count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('ix_backup_records_backup_id', 'backup_records', ['backup_id'], unique=True)
    op.create_index('ix_backup_records_backup_type', 'backup_records', ['backup_type'], unique=False)
    op.create_index('ix_backup_records_status', 'backup_records', ['status'], unique=False)
    op.create_index('ix_backup_records_created_at', 'backup_records', ['created_at'], unique=False)
    
    # 创建备份配置表
    op.create_table('backup_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_key', sa.String(length=100), nullable=False),
        sa.Column('config_value', sa.Text(), nullable=True),
        sa.Column('config_type', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('ix_backup_configs_config_key', 'backup_configs', ['config_key'], unique=True)
    op.create_index('ix_backup_configs_category', 'backup_configs', ['category'], unique=False)
    
    # 创建备份任务表
    op.create_table('backup_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(length=50), nullable=False),
        sa.Column('task_name', sa.String(length=100), nullable=False),
        sa.Column('task_type', sa.String(length=20), nullable=False),
        sa.Column('schedule_expression', sa.String(length=100), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False),
        sa.Column('backup_type', sa.String(length=20), nullable=True),
        sa.Column('include_database', sa.Boolean(), nullable=False),
        sa.Column('include_files', sa.Boolean(), nullable=False),
        sa.Column('include_patterns', sa.Text(), nullable=True),
        sa.Column('exclude_patterns', sa.Text(), nullable=True),
        sa.Column('storage_config', sa.Text(), nullable=True),
        sa.Column('retention_days', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('total_runs', sa.Integer(), nullable=True),
        sa.Column('successful_runs', sa.Integer(), nullable=True),
        sa.Column('failed_runs', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('ix_backup_tasks_task_id', 'backup_tasks', ['task_id'], unique=True)
    
    # 创建恢复记录表
    op.create_table('restore_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restore_id', sa.String(length=50), nullable=False),
        sa.Column('backup_record_id', sa.Integer(), nullable=False),
        sa.Column('restore_type', sa.String(length=20), nullable=False),
        sa.Column('target_path', sa.String(length=500), nullable=True),
        sa.Column('restore_options', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('restored_files_count', sa.Integer(), nullable=True),
        sa.Column('restored_databases_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('requested_by', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['backup_record_id'], ['backup_records.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('ix_restore_records_restore_id', 'restore_records', ['restore_id'], unique=True)
    op.create_index('ix_restore_records_status', 'restore_records', ['status'], unique=False)
    
    # 插入默认备份配置
    backup_configs_table = sa.table('backup_configs',
        sa.column('config_key', sa.String),
        sa.column('config_value', sa.Text),
        sa.column('config_type', sa.String),
        sa.column('description', sa.Text),
        sa.column('category', sa.String),
        sa.column('is_active', sa.Boolean),
        sa.column('updated_at', sa.DateTime),
        sa.column('updated_by', sa.String)
    )
    
    from datetime import datetime
    now = datetime.utcnow()
    
    op.bulk_insert(backup_configs_table, [
        # 通用配置
        {
            'config_key': 'backup_retention_days',
            'config_value': '30',
            'config_type': 'int',
            'description': '备份保留天数',
            'category': 'general',
            'is_active': True,
            'updated_at': now,
            'updated_by': 'system'
        },
        {
            'config_key': 'backup_encryption_enabled',
            'config_value': 'true',
            'config_type': 'bool',
            'description': '是否启用备份加密',
            'category': 'security',
            'is_active': True,
            'updated_at': now,
            'updated_by': 'system'
        },
        {
            'config_key': 'backup_compression_level',
            'config_value': '6',
            'config_type': 'int',
            'description': '备份压缩级别 (1-9)',
            'category': 'general',
            'is_active': True,
            'updated_at': now,
            'updated_by': 'system'
        },
        # 调度配置
        {
            'config_key': 'auto_backup_enabled',
            'config_value': 'true',
            'config_type': 'bool',
            'description': '是否启用自动备份',
            'category': 'schedule',
            'is_active': True,
            'updated_at': now,
            'updated_by': 'system'
        },
        {
            'config_key': 'incremental_backup_interval',
            'config_value': '6',
            'config_type': 'int',
            'description': '增量备份间隔 (小时)',
            'category': 'schedule',
            'is_active': True,
            'updated_at': now,
            'updated_by': 'system'
        },
        {
            'config_key': 'full_backup_day',
            'config_value': '0',
            'config_type': 'int',
            'description': '全量备份日 (0=周日)',
            'category': 'schedule',
            'is_active': True,
            'updated_at': now,
            'updated_by': 'system'
        },
        # 存储配置
        {
            'config_key': 'default_storage_providers',
            'config_value': '["local"]',
            'config_type': 'json',
            'description': '默认存储提供商列表',
            'category': 'storage',
            'is_active': True,
            'updated_at': now,
            'updated_by': 'system'
        },
        {
            'config_key': 'local_backup_path',
            'config_value': 'backups/local',
            'config_type': 'string',
            'description': '本地备份存储路径',
            'category': 'storage',
            'is_active': True,
            'updated_at': now,
            'updated_by': 'system'
        }
    ])


def downgrade():
    # 删除表 (按依赖关系倒序)
    op.drop_table('restore_records')
    op.drop_table('backup_tasks')  
    op.drop_table('backup_configs')
    op.drop_table('backup_records')