"""add_agent_role_to_issues

Revision ID: add_agent_role_issues
Revises: a1b2c3d4e5f6
Create Date: 2026-01-17 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_agent_role_issues'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add agent_role column to issues table
    op.add_column('issues', sa.Column('agent_role', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_issues_agent_role'), 'issues', ['agent_role'], unique=False)


def downgrade() -> None:
    # Remove agent_role column from issues table
    op.drop_index(op.f('ix_issues_agent_role'), table_name='issues')
    op.drop_column('issues', 'agent_role')
