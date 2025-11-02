"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2025-11-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE roleenum AS ENUM ('provider', 'consumer', 'broker')")
    op.execute("CREATE TYPE publicationstatus AS ENUM ('active', 'inactive', 'archived')")
    op.execute("CREATE TYPE requeststatus AS ENUM ('open', 'approved', 'rejected', 'contracted')")
    op.execute("CREATE TYPE contractstatus AS ENUM ('active', 'suspended', 'terminated')")
    op.execute("CREATE TYPE transferstatus AS ENUM ('initiated', 'in_progress', 'completed', 'failed')")
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keycloak_id', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('organization', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_keycloak_id'), 'users', ['keycloak_id'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', postgresql.ENUM('PROVIDER', 'CONSUMER', 'BROKER', name='roleenum', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create publications table
    op.create_table(
        'publications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('ACTIVE', 'INACTIVE', 'ARCHIVED', name='publicationstatus', create_type=False), nullable=False),
        sa.Column('publication_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('openmetadata_id', sa.String(length=255), nullable=True),
        sa.Column('s3_path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_publications_title'), 'publications', ['title'], unique=False)
    op.create_index(op.f('ix_publications_openmetadata_id'), 'publications', ['openmetadata_id'], unique=False)
    
    # Create requests table
    op.create_table(
        'requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('publication_id', sa.Integer(), nullable=False),
        sa.Column('requester_id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('OPEN', 'APPROVED', 'REJECTED', 'CONTRACTED', name='requeststatus', create_type=False), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('response_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['publication_id'], ['publications.id'], ),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['provider_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create contracts table
    op.create_table(
        'contracts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('ACTIVE', 'SUSPENDED', 'TERMINATED', name='contractstatus', create_type=False), nullable=False),
        sa.Column('terms', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('signed_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['requests.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('request_id')
    )
    
    # Create transfers table
    op.create_table(
        'transfers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('INITIATED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='transferstatus', create_type=False), nullable=False),
        sa.Column('destination', sa.String(length=500), nullable=True),
        sa.Column('presigned_url', sa.Text(), nullable=True),
        sa.Column('s3_key', sa.String(length=500), nullable=True),
        sa.Column('bytes_transferred', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_event_type'), 'audit_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_entity_type'), 'audit_logs', ['entity_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_entity_id'), 'audit_logs', ['entity_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_entity_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_entity_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_event_type'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_table('transfers')
    op.drop_table('contracts')
    op.drop_table('requests')
    op.drop_index(op.f('ix_publications_openmetadata_id'), table_name='publications')
    op.drop_index(op.f('ix_publications_title'), table_name='publications')
    op.drop_table('publications')
    op.drop_table('roles')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_keycloak_id'), table_name='users')
    op.drop_table('users')
    
    op.execute("DROP TYPE transferstatus")
    op.execute("DROP TYPE contractstatus")
    op.execute("DROP TYPE requeststatus")
    op.execute("DROP TYPE publicationstatus")
    op.execute("DROP TYPE roleenum")
