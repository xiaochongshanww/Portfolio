"""Add visitor statistics tables

Revision ID: 0008
Revises: 0007
Create Date: 2025-01-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone, timedelta

# revision identifiers, used by Alembic.
revision = '0008_add_visitor_stats'
down_revision = '0007_timezone_update'
branch_labels = None
depends_on = None

# 定义上海时区 (UTC+8)
SHANGHAI_TZ = timezone(timedelta(hours=8))

def upgrade():
    """创建访客统计表"""
    # 创建访客统计表
    op.create_table('visitor_stats',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ip_address', sa.String(45), nullable=False, index=True),
        sa.Column('user_agent_hash', sa.String(64), nullable=False, index=True), 
        sa.Column('visited_date', sa.Date(), nullable=False, index=True),
        sa.Column('first_visit_time', sa.DateTime(), nullable=False, default=lambda: datetime.now(SHANGHAI_TZ)),
        sa.Column('last_visit_time', sa.DateTime(), nullable=False, default=lambda: datetime.now(SHANGHAI_TZ)),
        sa.Column('page_views', sa.Integer(), default=1),
    )
    
    # 创建唯一约束和索引
    op.create_unique_constraint('unique_visitor_per_day', 'visitor_stats', ['ip_address', 'user_agent_hash', 'visited_date'])
    op.create_index('idx_visitor_date', 'visitor_stats', ['visited_date'])
    op.create_index('idx_visitor_ip', 'visitor_stats', ['ip_address'])
    
    # 创建每日统计汇总表
    op.create_table('daily_stats',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('stat_date', sa.Date(), nullable=False, unique=True, index=True),
        sa.Column('unique_visitors', sa.Integer(), default=0),
        sa.Column('total_page_views', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), default=lambda: datetime.now(SHANGHAI_TZ)),
        sa.Column('updated_at', sa.DateTime(), default=lambda: datetime.now(SHANGHAI_TZ)),
    )

def downgrade():
    """删除访客统计表"""
    op.drop_table('daily_stats')
    op.drop_table('visitor_stats')