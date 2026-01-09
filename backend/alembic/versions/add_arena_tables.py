"""Add Arena tables for Combat Arena mode

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-01-09 18:30:00.000000

Dodaje tabele dla Combat Arena:
- arena_sessions: Sesje porównujące dwa schematy review (A vs B)
- schema_ratings: Rankingi ELO dla pełnych schematów konfiguracji

Modyfikuje tabelę reviews:
- review_mode: 'council' (współpraca) lub 'combat_arena' (porównanie)
- arena_schema_name: 'A' lub 'B' (tylko dla combat_arena)
- arena_session_id: FK do arena_sessions (tylko dla combat_arena)
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'b7c8d9e0f1a2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema - dodaje tabele Arena i modyfikuje reviews."""

    # === ARENA_SESSIONS TABLE ===
    # Tabela przechowująca sesje porównań dwóch pełnych schematów review
    op.create_table('arena_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('schema_a_config', sa.JSON(), nullable=False),
        sa.Column('schema_b_config', sa.JSON(), nullable=False),
        sa.Column('review_a_id', sa.Integer(), nullable=True),
        sa.Column('review_b_id', sa.Integer(), nullable=True),
        sa.Column('winner', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('vote_comment', sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column('voter_id', sa.Integer(), nullable=True),
        sa.Column('voted_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['review_a_id'], ['reviews.id'], ),
        sa.ForeignKeyConstraint(['review_b_id'], ['reviews.id'], ),
        sa.ForeignKeyConstraint(['voter_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # Indeksy dla szybkiego wyszukiwania
    op.create_index(op.f('ix_arena_sessions_project_id'), 'arena_sessions', ['project_id'], unique=False)
    op.create_index(op.f('ix_arena_sessions_created_by'), 'arena_sessions', ['created_by'], unique=False)
    op.create_index(op.f('ix_arena_sessions_status'), 'arena_sessions', ['status'], unique=False)
    op.create_index(op.f('ix_arena_sessions_review_a_id'), 'arena_sessions', ['review_a_id'], unique=False)
    op.create_index(op.f('ix_arena_sessions_review_b_id'), 'arena_sessions', ['review_b_id'], unique=False)

    # === SCHEMA_RATINGS TABLE ===
    # Tabela rankingów ELO dla pełnych schematów konfiguracji (4 role każdy)
    op.create_table('schema_ratings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('schema_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('schema_config', sa.JSON(), nullable=False),
        sa.Column('elo_rating', sa.Float(), nullable=False),
        sa.Column('games_played', sa.Integer(), nullable=False),
        sa.Column('wins', sa.Integer(), nullable=False),
        sa.Column('losses', sa.Integer(), nullable=False),
        sa.Column('ties', sa.Integer(), nullable=False),
        sa.Column('avg_issues_found', sa.Float(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('schema_hash')
    )
    # Indeks na schema_hash dla szybkiego wyszukiwania przez hash
    op.create_index(op.f('ix_schema_ratings_schema_hash'), 'schema_ratings', ['schema_hash'], unique=True)

    # === MODIFY REVIEWS TABLE ===
    # Dodaj nowe kolumny do tabeli reviews dla obsługi Arena mode

    # review_mode: 'council' (domyślny) lub 'combat_arena'
    op.add_column('reviews',
        sa.Column('review_mode', sqlmodel.sql.sqltypes.AutoString(length=20),
                  nullable=False, server_default='council')
    )
    op.create_index(op.f('ix_reviews_review_mode'), 'reviews', ['review_mode'], unique=False)

    # arena_schema_name: 'A' lub 'B' (tylko dla combat_arena)
    op.add_column('reviews',
        sa.Column('arena_schema_name', sqlmodel.sql.sqltypes.AutoString(length=1),
                  nullable=True)
    )

    # arena_session_id: FK do arena_sessions (tylko dla combat_arena)
    op.add_column('reviews',
        sa.Column('arena_session_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_reviews_arena_session_id',
        'reviews',
        'arena_sessions',
        ['arena_session_id'],
        ['id']
    )
    op.create_index(op.f('ix_reviews_arena_session_id'), 'reviews', ['arena_session_id'], unique=False)


def downgrade() -> None:
    """Downgrade database schema - usuwa tabele Arena i kolumny w reviews."""

    # === REMOVE COLUMNS FROM REVIEWS ===
    op.drop_index(op.f('ix_reviews_arena_session_id'), table_name='reviews')
    op.drop_constraint('fk_reviews_arena_session_id', 'reviews', type_='foreignkey')
    op.drop_column('reviews', 'arena_session_id')
    op.drop_column('reviews', 'arena_schema_name')
    op.drop_index(op.f('ix_reviews_review_mode'), table_name='reviews')
    op.drop_column('reviews', 'review_mode')

    # === DROP SCHEMA_RATINGS TABLE ===
    op.drop_index(op.f('ix_schema_ratings_schema_hash'), table_name='schema_ratings')
    op.drop_table('schema_ratings')

    # === DROP ARENA_SESSIONS TABLE ===
    op.drop_index(op.f('ix_arena_sessions_review_b_id'), table_name='arena_sessions')
    op.drop_index(op.f('ix_arena_sessions_review_a_id'), table_name='arena_sessions')
    op.drop_index(op.f('ix_arena_sessions_status'), table_name='arena_sessions')
    op.drop_index(op.f('ix_arena_sessions_created_by'), table_name='arena_sessions')
    op.drop_index(op.f('ix_arena_sessions_project_id'), table_name='arena_sessions')
    op.drop_table('arena_sessions')
