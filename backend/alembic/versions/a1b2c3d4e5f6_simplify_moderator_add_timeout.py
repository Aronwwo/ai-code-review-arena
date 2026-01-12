"""simplify_moderator_add_timeout

Revision ID: a1b2c3d4e5f6
Revises: 1f300dbdbe3a
Create Date: 2026-01-12 15:00:00.000000

Changes:
- Drop moderator_type column from reviews (no longer needed)
- Add summary column to reviews (moderator's final report)
- Add timed_out and timeout_seconds columns to review_agents
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '1f300dbdbe3a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop moderator_type column from reviews
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_column('moderator_type')
        batch_op.add_column(
            sa.Column('summary', sa.Text(), nullable=True)
        )

    # Add timeout columns to review_agents
    with op.batch_alter_table('review_agents', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('timed_out', sa.Boolean(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('timeout_seconds', sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    # Remove timeout columns from review_agents
    with op.batch_alter_table('review_agents', schema=None) as batch_op:
        batch_op.drop_column('timeout_seconds')
        batch_op.drop_column('timed_out')

    # Restore moderator_type column and remove summary
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_column('summary')
        batch_op.add_column(
            sa.Column('moderator_type', sqlmodel.sql.sqltypes.AutoString(length=20),
                     nullable=False, server_default='debate')
        )
