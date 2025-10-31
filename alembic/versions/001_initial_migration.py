"""Initial migration - create all tables

Revision ID: 001
Revises: 
Create Date: 2025-10-31 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create participants table
    op.create_table('participants',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('role', sa.Enum('PROVIDER', 'CONSUMER', 'BROKER', name='userrole'), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_participants_username'), 'participants', ['username'], unique=True)
    
    # Create publications table
    op.create_table('publications',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('metadata', sa.JSON(), nullable=True),
    sa.Column('owner_id', sa.String(), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['participants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Create requests table
    op.create_table('requests',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('subject', sa.String(), nullable=False),
    sa.Column('publication_id', sa.String(), nullable=True),
    sa.Column('requester_id', sa.String(), nullable=True),
    sa.Column('state', sa.Enum('OPEN', 'CONTRACTED', 'REJECTED', name='requeststate'), nullable=False),
    sa.Column('metadata', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['publication_id'], ['publications.id'], ),
    sa.ForeignKeyConstraint(['requester_id'], ['participants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Create contracts table
    op.create_table('contracts',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('request_id', sa.String(), nullable=False),
    sa.Column('terms', sa.JSON(), nullable=True),
    sa.Column('state', sa.Enum('ACTIVE', 'EXPIRED', 'REVOKED', name='contractstate'), nullable=False),
    sa.Column('signed_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['request_id'], ['requests.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Create transfers table
    op.create_table('transfers',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('contract_id', sa.String(), nullable=False),
    sa.Column('destination', sa.String(), nullable=True),
    sa.Column('presigned_url', sa.Text(), nullable=True),
    sa.Column('state', sa.Enum('INITIATED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='transferstate'), nullable=False),
    sa.Column('metadata', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Create audit_logs table
    op.create_table('audit_logs',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('event_type', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=True),
    sa.Column('entity_type', sa.String(), nullable=True),
    sa.Column('entity_id', sa.String(), nullable=True),
    sa.Column('payload', sa.JSON(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_event_type'), 'audit_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_entity_id'), 'audit_logs', ['entity_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_entity_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_event_type'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_table('transfers')
    op.drop_table('contracts')
    op.drop_table('requests')
    op.drop_table('publications')
    op.drop_index(op.f('ix_participants_username'), table_name='participants')
    op.drop_table('participants')
