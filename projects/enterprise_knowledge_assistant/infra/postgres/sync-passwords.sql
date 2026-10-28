-- Local operator startup job: align role passwords with current Compose configuration.
-- Runs after PostgreSQL initialization and before any service migrations.
-- Preserves databases, grants, and data; never rerun bootstrap.sql on an existing volume.
\set ECHO none
\set ON_ERROR_STOP on
\getenv postgres_password POSTGRES_PASSWORD
\getenv identity_password IDENTITY_DB_PASSWORD
\getenv identity_migration_password IDENTITY_MIGRATION_PASSWORD
\getenv knowledge_password KNOWLEDGE_DB_PASSWORD
\getenv knowledge_migration_password KNOWLEDGE_MIGRATION_PASSWORD
\getenv chat_password CHAT_DB_PASSWORD
\getenv chat_migration_password CHAT_MIGRATION_PASSWORD

BEGIN;
ALTER ROLE postgres PASSWORD :'postgres_password';
ALTER ROLE identity_migration PASSWORD :'identity_migration_password';
ALTER ROLE identity_runtime PASSWORD :'identity_password';
ALTER ROLE knowledge_migration PASSWORD :'knowledge_migration_password';
ALTER ROLE knowledge_runtime PASSWORD :'knowledge_password';
ALTER ROLE chat_migration PASSWORD :'chat_migration_password';
ALTER ROLE chat_runtime PASSWORD :'chat_password';
COMMIT;
\echo Local database role passwords synchronized.
