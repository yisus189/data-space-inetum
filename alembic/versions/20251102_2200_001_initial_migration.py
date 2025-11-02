"""Initial migration - create all tables

Revision ID: 001
Revises: 
Create Date: 2025-11-02 22:00:00.000000

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
    # Create users table
    op.create_table('users',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('username', sa.String(length=255), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=True),
    sa.Column('organization', sa.String(length=255), nullable=True),
    sa.Column('keycloak_id', sa.String(length=255), nullable=True),
    sa.Column('roles', sa.JSON(), nullable=True),
    sa.Column('attributes', sa.JSON(), nullable=True),
    sa.Column('is_active', sa.Enum('true', 'false', name='boolean_enum'), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_keycloak_id'), 'users', ['keycloak_id'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create roles table
    op.create_table('roles',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('permissions', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)

    # Create publications table
    op.create_table('publications',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('publisher_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('metadata', sa.JSON(), nullable=True),
    sa.Column('schema_info', sa.JSON(), nullable=True),
    sa.Column('openmetadata_id', sa.String(length=500), nullable=True),
    sa.Column('openmetadata_fqn', sa.String(length=500), nullable=True),
    sa.Column('status', sa.Enum('DRAFT', 'PUBLISHED', 'ARCHIVED', name='publicationstatus'), nullable=False),
    sa.Column('data_location', sa.String(length=1000), nullable=True),
    sa.Column('access_url', sa.String(length=1000), nullable=True),
    sa.Column('tags', sa.JSON(), nullable=True),
    sa.Column('categories', sa.JSON(), nullable=True),
    sa.Column('terms', sa.JSON(), nullable=True),
    sa.Column('policies', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['publisher_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_publications_openmetadata_fqn'), 'publications', ['openmetadata_fqn'], unique=False)
    op.create_index(op.f('ix_publications_openmetadata_id'), 'publications', ['openmetadata_id'], unique=True)
    op.create_index(op.f('ix_publications_title'), 'publications', ['title'], unique=False)

    # Create requests table
    op.create_table('requests',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('subject', sa.String(length=500), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('requester_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('publication_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('status', sa.Enum('OPEN', 'APPROVED', 'REJECTED', 'CONTRACTED', 'CANCELLED', name='requeststatus'), nullable=False),
    sa.Column('purpose', sa.Text(), nullable=True),
    sa.Column('intended_use', sa.Text(), nullable=True),
    sa.Column('duration_days', sa.String(length=50), nullable=True),
    sa.Column('response_notes', sa.Text(), nullable=True),
    sa.Column('approver_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('metadata', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['approver_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['publication_id'], ['publications.id'], ),
    sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_requests_status'), 'requests', ['status'], unique=False)

    # Create contracts table
    op.create_table('contracts',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('provider_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('consumer_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('publication_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('terms', sa.JSON(), nullable=True),
    sa.Column('policies', sa.JSON(), nullable=True),
    sa.Column('status', sa.Enum('ACTIVE', 'EXPIRED', 'TERMINATED', 'SUSPENDED', name='contractstatus'), nullable=False),
    sa.Column('signature_method', sa.String(length=100), nullable=True),
    sa.Column('signature_timestamp', sa.String(length=100), nullable=True),
    sa.Column('signature_hash', sa.String(length=255), nullable=True),
    sa.Column('start_date', sa.String(length=100), nullable=True),
    sa.Column('end_date', sa.String(length=100), nullable=True),
    sa.Column('metadata', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['consumer_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['provider_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['publication_id'], ['publications.id'], ),
    sa.ForeignKeyConstraint(['request_id'], ['requests.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contracts_status'), 'contracts', ['status'], unique=False)

    # Create transfers table
    op.create_table('transfers',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('contract_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('destination', sa.String(length=1000), nullable=True),
    sa.Column('source', sa.String(length=1000), nullable=True),
    sa.Column('status', sa.Enum('INITIATED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED', name='transferstatus'), nullable=False),
    sa.Column('transfer_method', sa.String(length=100), nullable=True),
    sa.Column('presigned_url', sa.Text(), nullable=True),
    sa.Column('presigned_url_expires_at', sa.String(length=100), nullable=True),
    sa.Column('bucket_name', sa.String(length=255), nullable=True),
    sa.Column('object_key', sa.String(length=1000), nullable=True),
    sa.Column('file_size', sa.Integer(), nullable=True),
    sa.Column('file_format', sa.String(length=100), nullable=True),
    sa.Column('checksum', sa.String(length=255), nullable=True),
    sa.Column('bytes_transferred', sa.Integer(), nullable=True),
    sa.Column('progress_percentage', sa.Integer(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('retry_count', sa.Integer(), nullable=True),
    sa.Column('metadata', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transfers_status'), 'transfers', ['status'], unique=False)

    # Create audit_logs table
    op.create_table('audit_logs',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('event_type', sa.String(length=255), nullable=False),
    sa.Column('event_category', sa.String(length=100), nullable=True),
    sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('actor_username', sa.String(length=255), nullable=True),
    sa.Column('actor_ip', sa.String(length=100), nullable=True),
    sa.Column('target_type', sa.String(length=100), nullable=True),
    sa.Column('target_id', sa.String(length=255), nullable=True),
    sa.Column('event_data', sa.JSON(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('http_method', sa.String(length=10), nullable=True),
    sa.Column('http_path', sa.String(length=1000), nullable=True),
    sa.Column('http_status_code', sa.Integer(), nullable=True),
    sa.Column('session_id', sa.String(length=255), nullable=True),
    sa.Column('request_id', sa.String(length=255), nullable=True),
    sa.Column('metadata', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_actor_username'), 'audit_logs', ['actor_username'], unique=False)
    op.create_index(op.f('ix_audit_logs_event_category'), 'audit_logs', ['event_category'], unique=False)
    op.create_index(op.f('ix_audit_logs_event_type'), 'audit_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_request_id'), 'audit_logs', ['request_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_status'), 'audit_logs', ['status'], unique=False)
    op.create_index(op.f('ix_audit_logs_target_id'), 'audit_logs', ['target_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_target_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_status'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_request_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_event_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_event_category'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_actor_username'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_transfers_status'), table_name='transfers')
    op.drop_table('transfers')
    op.drop_index(op.f('ix_contracts_status'), table_name='contracts')
    op.drop_table('contracts')
    op.drop_index(op.f('ix_requests_status'), table_name='requests')
    op.drop_table('requests')
    op.drop_index(op.f('ix_publications_title'), table_name='publications')
    op.drop_index(op.f('ix_publications_openmetadata_id'), table_name='publications')
    op.drop_index(op.f('ix_publications_openmetadata_fqn'), table_name='publications')
    op.drop_table('publications')
    op.drop_index(op.f('ix_roles_name'), table_name='roles')
    op.drop_table('roles')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_keycloak_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
