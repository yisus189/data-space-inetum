"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-10-31 14:54:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create participants table
    op.create_table(
        'participants',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_participants_username'), 'participants', ['username'], unique=False)

    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('participant_id', sa.String(), nullable=False),
        sa.Column('role_name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['participant_id'], ['participants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create publications table
    op.create_table(
        'publications',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.String(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('schema', sa.JSON(), nullable=True),
        sa.Column('lineage', sa.JSON(), nullable=True),
        sa.Column('openmetadata_fqn', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['participants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('openmetadata_fqn')
    )
    op.create_index(op.f('ix_publications_openmetadata_fqn'), 'publications', ['openmetadata_fqn'], unique=False)

    # Create requests table
    op.create_table(
        'requests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('publication_id', sa.String(), nullable=True),
        sa.Column('requester_id', sa.String(), nullable=True),
        sa.Column('state', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['publication_id'], ['publications.id'], ),
        sa.ForeignKeyConstraint(['requester_id'], ['participants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create contracts table
    op.create_table(
        'contracts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('request_id', sa.String(), nullable=False),
        sa.Column('terms', sa.JSON(), nullable=True),
        sa.Column('state', sa.String(), nullable=True),
        sa.Column('signed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['request_id'], ['requests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create transfers table
    op.create_table(
        'transfers',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('destination', sa.String(), nullable=True),
        sa.Column('state', sa.String(), nullable=True),
        sa.Column('presigned_url', sa.Text(), nullable=True),
        sa.Column('method', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('resource_type', sa.String(), nullable=True),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_event_type'), 'audit_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_event_type'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_table('transfers')
    op.drop_table('contracts')
    op.drop_table('requests')
    op.drop_index(op.f('ix_publications_openmetadata_fqn'), table_name='publications')
    op.drop_table('publications')
    op.drop_table('roles')
    op.drop_index(op.f('ix_participants_username'), table_name='participants')
    op.drop_table('participants')
