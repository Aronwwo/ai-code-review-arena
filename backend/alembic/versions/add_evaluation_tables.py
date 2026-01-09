"""Add evaluation tables for Model Duel

Revision ID: a1b2c3d4e5f6
Revises: 9f836e3c48f0
Create Date: 2026-01-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '9f836e3c48f0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create evaluation_sessions table
    op.create_table('evaluation_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('num_rounds', sa.Integer(), nullable=False),
        sa.Column('current_round', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_sessions_created_by'), 'evaluation_sessions', ['created_by'], unique=False)
    op.create_index(op.f('ix_evaluation_sessions_project_id'), 'evaluation_sessions', ['project_id'], unique=False)
    op.create_index(op.f('ix_evaluation_sessions_status'), 'evaluation_sessions', ['status'], unique=False)

    # Create evaluation_candidates table
    op.create_table('evaluation_candidates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('position', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('model', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('agent_role', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('custom_provider_config', sa.JSON(), nullable=True),
        sa.Column('review_id', sa.Integer(), nullable=True),
        sa.Column('issues_found', sa.Integer(), nullable=False),
        sa.Column('raw_output', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('parsed_successfully', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['evaluation_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_candidates_review_id'), 'evaluation_candidates', ['review_id'], unique=False)
    op.create_index(op.f('ix_evaluation_candidates_session_id'), 'evaluation_candidates', ['session_id'], unique=False)

    # Create evaluation_votes table
    op.create_table('evaluation_votes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('choice', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('comment', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('voter_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['evaluation_sessions.id'], ),
        sa.ForeignKeyConstraint(['voter_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_votes_round_number'), 'evaluation_votes', ['round_number'], unique=False)
    op.create_index(op.f('ix_evaluation_votes_session_id'), 'evaluation_votes', ['session_id'], unique=False)
    op.create_index(op.f('ix_evaluation_votes_voter_id'), 'evaluation_votes', ['voter_id'], unique=False)

    # Create rating_configs table
    op.create_table('rating_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('model', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('agent_role', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('elo_rating', sa.Float(), nullable=False),
        sa.Column('games_played', sa.Integer(), nullable=False),
        sa.Column('wins', sa.Integer(), nullable=False),
        sa.Column('losses', sa.Integer(), nullable=False),
        sa.Column('ties', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rating_configs_agent_role'), 'rating_configs', ['agent_role'], unique=False)
    op.create_index(op.f('ix_rating_configs_model'), 'rating_configs', ['model'], unique=False)
    op.create_index(op.f('ix_rating_configs_provider'), 'rating_configs', ['provider'], unique=False)

    # Create rating_models table
    op.create_table('rating_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('model', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('elo_rating', sa.Float(), nullable=False),
        sa.Column('games_played', sa.Integer(), nullable=False),
        sa.Column('wins', sa.Integer(), nullable=False),
        sa.Column('losses', sa.Integer(), nullable=False),
        sa.Column('ties', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rating_models_model'), 'rating_models', ['model'], unique=False)
    op.create_index(op.f('ix_rating_models_provider'), 'rating_models', ['provider'], unique=False)


def downgrade() -> None:
    # Drop all evaluation tables in reverse order
    op.drop_index(op.f('ix_rating_models_provider'), table_name='rating_models')
    op.drop_index(op.f('ix_rating_models_model'), table_name='rating_models')
    op.drop_table('rating_models')

    op.drop_index(op.f('ix_rating_configs_provider'), table_name='rating_configs')
    op.drop_index(op.f('ix_rating_configs_model'), table_name='rating_configs')
    op.drop_index(op.f('ix_rating_configs_agent_role'), table_name='rating_configs')
    op.drop_table('rating_configs')

    op.drop_index(op.f('ix_evaluation_votes_voter_id'), table_name='evaluation_votes')
    op.drop_index(op.f('ix_evaluation_votes_session_id'), table_name='evaluation_votes')
    op.drop_index(op.f('ix_evaluation_votes_round_number'), table_name='evaluation_votes')
    op.drop_table('evaluation_votes')

    op.drop_index(op.f('ix_evaluation_candidates_session_id'), table_name='evaluation_candidates')
    op.drop_index(op.f('ix_evaluation_candidates_review_id'), table_name='evaluation_candidates')
    op.drop_table('evaluation_candidates')

    op.drop_index(op.f('ix_evaluation_sessions_status'), table_name='evaluation_sessions')
    op.drop_index(op.f('ix_evaluation_sessions_project_id'), table_name='evaluation_sessions')
    op.drop_index(op.f('ix_evaluation_sessions_created_by'), table_name='evaluation_sessions')
    op.drop_table('evaluation_sessions')
