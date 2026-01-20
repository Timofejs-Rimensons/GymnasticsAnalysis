"""restructure with users and exercise features

Revision ID: 2
Revises: 1
Create Date: 2026-01-20 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2'
down_revision: Union[str, None] = '1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('username', sa.String(length=255), nullable=False, unique=True),
    sa.Column('email', sa.String(length=255), nullable=False, unique=True),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create exercise_features table
    op.create_table('exercise_features',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('exercise_id', sa.Integer(), nullable=False),
    sa.Column('feature_name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('feature_type', sa.String(length=50), nullable=False),  # 'pose', 'alignment', 'position', etc.
    sa.Column('max_score', sa.Float(), nullable=False, server_default='10.0'),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exercise_features_exercise_id'), 'exercise_features', ['exercise_id'], unique=False)

    # Add user_id column to analysis_jobs
    op.add_column('analysis_jobs', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('analysis_jobs', sa.Column('exercise_id', sa.Integer(), nullable=True))
    op.add_column('analysis_jobs', sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    op.add_column('analysis_jobs', sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('analysis_jobs', sa.Column('video_blob', sa.LargeBinary(), nullable=True))

    # Create foreign key constraints
    op.create_foreign_key('fk_analysis_jobs_user_id', 'analysis_jobs', 'users', ['user_id'], ['id'])
    op.create_foreign_key('fk_analysis_jobs_exercise_id', 'analysis_jobs', 'exercises', ['exercise_id'], ['id'])
    op.create_index(op.f('ix_analysis_jobs_user_id'), 'analysis_jobs', ['user_id'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_exercise_id'), 'analysis_jobs', ['exercise_id'], unique=False)

    # Create processed_files table to track output videos, PDFs, etc.
    op.create_table('processed_files',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('file_type', sa.String(length=50), nullable=False),  # 'video', 'pdf', 'json'
    sa.Column('file_path', sa.String(length=500), nullable=False),
    sa.Column('file_size', sa.BigInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['job_id'], ['analysis_jobs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_processed_files_job_id'), 'processed_files', ['job_id'], unique=False)
    op.create_index(op.f('ix_processed_files_file_type'), 'processed_files', ['file_type'], unique=False)

    # Create pose_scores table for detailed pose analysis
    op.create_table('pose_scores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('feature_id', sa.Integer(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('max_score', sa.Float(), nullable=False),
    sa.Column('feedback', sa.Text(), nullable=True),
    sa.Column('needs_improvement', sa.Boolean(), nullable=False, server_default='false'),
    sa.ForeignKeyConstraint(['job_id'], ['analysis_jobs.id'], ),
    sa.ForeignKeyConstraint(['feature_id'], ['exercise_features.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pose_scores_job_id'), 'pose_scores', ['job_id'], unique=False)
    op.create_index(op.f('ix_pose_scores_feature_id'), 'pose_scores', ['feature_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_pose_scores_feature_id'), table_name='pose_scores')
    op.drop_index(op.f('ix_pose_scores_job_id'), table_name='pose_scores')
    op.drop_table('pose_scores')
    
    op.drop_index(op.f('ix_processed_files_file_type'), table_name='processed_files')
    op.drop_index(op.f('ix_processed_files_job_id'), table_name='processed_files')
    op.drop_table('processed_files')
    
    op.drop_index(op.f('ix_analysis_jobs_exercise_id'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_user_id'), table_name='analysis_jobs')
    op.drop_constraint('fk_analysis_jobs_exercise_id', 'analysis_jobs', type_='foreignkey')
    op.drop_constraint('fk_analysis_jobs_user_id', 'analysis_jobs', type_='foreignkey')
    op.drop_column('analysis_jobs', 'video_blob')
    op.drop_column('analysis_jobs', 'processed_at')
    op.drop_column('analysis_jobs', 'uploaded_at')
    op.drop_column('analysis_jobs', 'exercise_id')
    op.drop_column('analysis_jobs', 'user_id')
    
    op.drop_index(op.f('ix_exercise_features_exercise_id'), table_name='exercise_features')
    op.drop_table('exercise_features')
    
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
