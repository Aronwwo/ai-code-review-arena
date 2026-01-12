"""remove_arena_references_from_reviews

Revision ID: 1f300dbdbe3a
Revises: 66a463fd1f4b
Create Date: 2026-01-12 10:44:36.783149

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '1f300dbdbe3a'
down_revision = '66a463fd1f4b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op: The arena columns were never successfully added to the database
    # (the arena migration failed), so there's nothing to remove
    pass


def downgrade() -> None:
    # No-op: Nothing to undo
    pass
