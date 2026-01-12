"""add_moderator_type_to_reviews

Revision ID: 66a463fd1f4b
Revises: b7c8d9e0f1a2
Create Date: 2026-01-09 22:55:27.917671

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '66a463fd1f4b'
down_revision = '9f836e3c48f0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add review_mode and moderator_type columns to reviews table
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('review_mode', sqlmodel.sql.sqltypes.AutoString(length=20),
                     nullable=False, server_default='council')
        )
        batch_op.add_column(
            sa.Column('moderator_type', sqlmodel.sql.sqltypes.AutoString(length=20),
                     nullable=False, server_default='debate')
        )
        batch_op.create_index('ix_reviews_review_mode', ['review_mode'], unique=False)


def downgrade() -> None:
    # Remove review_mode and moderator_type columns from reviews table
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_index('ix_reviews_review_mode')
        batch_op.drop_column('moderator_type')
        batch_op.drop_column('review_mode')
