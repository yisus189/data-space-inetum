-- Create additional databases for Keycloak and OpenMetadata
-- Note: PostgreSQL does not support CREATE DATABASE IF NOT EXISTS
-- These commands will fail if databases already exist
CREATE DATABASE keycloak;
CREATE DATABASE openmetadata_db;
