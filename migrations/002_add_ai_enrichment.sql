"""
Add AI enrichment fields to jobs table

Revision ID: 002
Revises: 001
Create Date: 2026-02-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Add AI enrichment columns"""
    
    # Add new columns
    op.add_column('jobs', sa.Column('skills', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('jobs', sa.Column('ai_category', sa.String(length=50), nullable=True))
    op.add_column('jobs', sa.Column('ai_quality_score', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('ai_urgency', sa.String(length=20), nullable=True))
    op.add_column('jobs', sa.Column('ai_extracted_deadline', sa.DateTime(timezone=True), nullable=True))
    op.add_column('jobs', sa.Column('ai_deadline_confidence', sa.String(length=20), nullable=True))
    op.add_column('jobs', sa.Column('ai_seniority', sa.String(length=20), nullable=True))
    op.add_column('jobs', sa.Column('ai_work_arrangement', sa.String(length=20), nullable=True))
    op.add_column('jobs', sa.Column('ai_visa_sponsorship', sa.String(length=20), nullable=True))
    op.add_column('jobs', sa.Column('ai_required_years', sa.Integer(), nullable=True))
    
    # Create indexes
    op.create_index('idx_ai_category', 'jobs', ['ai_category'], unique=False)
    op.create_index('idx_skills_gin', 'jobs', ['skills'], unique=False, postgresql_using='gin')


def downgrade():
    """Remove AI enrichment columns"""
    
    op.drop_index('idx_skills_gin', table_name='jobs')
    op.drop_index('idx_ai_category', table_name='jobs')
    
    op.drop_column('jobs', 'ai_required_years')
    op.drop_column('jobs', 'ai_visa_sponsorship')
    op.drop_column('jobs', 'ai_work_arrangement')
    op.drop_column('jobs', 'ai_seniority')
    op.drop_column('jobs', 'ai_deadline_confidence')
    op.drop_column('jobs', 'ai_extracted_deadline')
    op.drop_column('jobs', 'ai_urgency')
    op.drop_column('jobs', 'ai_quality_score')
    op.drop_column('jobs', 'ai_category')
    op.drop_column('jobs', 'skills')
