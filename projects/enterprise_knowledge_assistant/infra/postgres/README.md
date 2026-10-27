# Database ownership

All identifiers are UUIDs; timestamps are UTC.
Text lengths count Unicode code points, not bytes, unless explicitly stated.

Bootstrap creates one database and an isolated `_test` database per service. Only the
corresponding migration/runtime roles can connect. Runtime roles neither own tables
nor have superuser, role creation, database creation, or BYPASSRLS privileges. No role
is a member of another service's role. Only Knowledge has the vector extension.

`bootstrap.sql` runs once when PostgreSQL initializes a new volume. It reads passwords
from the private container environment using psql's getenv command. Do not log the
resolved Compose configuration. Production backups and upgrades preserve existing
roles and data; never delete an existing volume to rerun initialization.

Run migrations through the operator-only `*-migrate` Compose services. Runtime API
and worker environments contain no migration credentials. Each migration owns its
tables, constraints, forced RLS policies and narrowly granted definer functions.
Those functions pin their search_path; callers never choose an SQL expression or role.
Default function execution is revoked from PUBLIC.

Transactions set trusted company/account values locally and reset connection state
on return to the pool. Session resolution and queue claims use narrowly scoped owned
functions; ordinary tenant reads/writes always require trusted transaction context.
Tests may seed only the matching `_test` database and must use runtime roles for RLS
assertions. Production databases must never be truncated by a test fixture.
