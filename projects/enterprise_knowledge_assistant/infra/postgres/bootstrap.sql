-- Operator-only initialization: separate owners and non-owner, non-BYPASSRLS runtimes.
-- All identifiers are UUIDs; timestamps are UTC.
-- Text lengths count Unicode code points, not bytes, unless explicitly stated.
\set ON_ERROR_STOP on
\getenv identity_password IDENTITY_DB_PASSWORD
\getenv identity_migration_password IDENTITY_MIGRATION_PASSWORD
\getenv knowledge_password KNOWLEDGE_DB_PASSWORD
\getenv knowledge_migration_password KNOWLEDGE_MIGRATION_PASSWORD
\getenv chat_password CHAT_DB_PASSWORD
\getenv chat_migration_password CHAT_MIGRATION_PASSWORD

CREATE ROLE identity_migration LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD :'identity_migration_password';
CREATE ROLE identity_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD :'identity_password';
CREATE ROLE knowledge_migration LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD :'knowledge_migration_password';
CREATE ROLE knowledge_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD :'knowledge_password';
CREATE ROLE chat_migration LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD :'chat_migration_password';
CREATE ROLE chat_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD :'chat_password';

CREATE DATABASE identity OWNER identity_migration;
CREATE DATABASE knowledge OWNER knowledge_migration;
CREATE DATABASE chat OWNER chat_migration;
CREATE DATABASE identity_test OWNER identity_migration;
CREATE DATABASE knowledge_test OWNER knowledge_migration;
CREATE DATABASE chat_test OWNER chat_migration;

REVOKE ALL ON DATABASE identity, knowledge, chat, identity_test, knowledge_test, chat_test FROM PUBLIC;
GRANT CONNECT ON DATABASE identity, identity_test TO identity_migration, identity_runtime;
GRANT CONNECT ON DATABASE knowledge, knowledge_test TO knowledge_migration, knowledge_runtime;
GRANT CONNECT ON DATABASE chat, chat_test TO chat_migration, chat_runtime;

\connect identity
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO identity_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE identity_migration IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO identity_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE identity_migration IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
\connect identity_test
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO identity_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE identity_migration IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO identity_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE identity_migration IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
\connect knowledge
CREATE EXTENSION vector;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO knowledge_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE knowledge_migration IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO knowledge_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE knowledge_migration IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
\connect knowledge_test
CREATE EXTENSION vector;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO knowledge_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE knowledge_migration IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO knowledge_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE knowledge_migration IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
\connect chat
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO chat_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE chat_migration IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO chat_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE chat_migration IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
\connect chat_test
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO chat_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE chat_migration IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO chat_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE chat_migration IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
