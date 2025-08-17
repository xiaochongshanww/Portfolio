"""add audit_logs and article.reject_reason

Revision ID: 0002_add_audit
Revises: 0001_init
Create Date: 2025-08-10
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_add_audit'
down_revision = '0001_init'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('articles', sa.Column('reject_reason', sa.String(length=500)))
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), nullable=False, index=True),
        sa.Column('operator_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('note', sa.String(length=500)),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    )
    op.create_index('ix_audit_logs_article', 'audit_logs', ['article_id'])
    op.create_index('ix_audit_logs_operator', 'audit_logs', ['operator_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])


def downgrade():
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_operator', table_name='audit_logs')
    op.drop_index('ix_audit_logs_article', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_column('articles', 'reject_reason')
