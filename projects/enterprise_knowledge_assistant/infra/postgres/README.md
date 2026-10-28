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

On `docker compose up`, the local operator job `postgres-configure` runs
`sync-passwords.sql` to update the seven database role passwords from current
configuration in one transaction without changing data or grants. It connects
through a Unix socket volume shared only with PostgreSQL, using the local image's
trusted socket authentication. Application containers have neither that socket nor
operator credentials. The PostgreSQL healthcheck uses TCP to wait until first-boot
initialization has finished, rather than accepting the temporary bootstrap server.
Production password rotation requires coordinating deployed clients and database
operator access; this is a local development setup.

Compose explicitly starts PostgreSQL with `max_connections=100`, overriding any lower
value saved in an existing data directory's `postgresql.conf`. The five application
processes each use SQLAlchemy's default pool of five retained connections plus ten
overflow connections: at most 75 in total, leaving room for the three superuser
reserved slots, migrations, and operator commands. Revisit this budget before adding
worker replicas or API processes. Apply the setting to an existing installation with
`docker compose up -d --wait`; PostgreSQL restarts briefly and preserves stored data.
Verify it with `docker compose exec -T postgres psql -U postgres -d postgres -c 'SHOW max_connections'`.

Compose runs the operator-only `*-migrate` services after password synchronization;
each API and worker waits for its migration to finish successfully. The web app
waits for all APIs' readiness checks. For an explicit migration retry, use
`docker compose run --rm identity-migrate` (or the corresponding owned service).
Runtime API and worker environments contain no migration credentials. Each migration owns its
tables, constraints, forced RLS policies and narrowly granted definer functions.
Those functions pin their search_path; callers never choose an SQL expression or role.
Default function execution is revoked from PUBLIC.

Transactions set trusted company/account values locally and reset connection state
on return to the pool. Session resolution and queue claims use narrowly scoped owned
functions; ordinary tenant reads/writes always require trusted transaction context.
Tests may seed only the matching `_test` database and must use runtime roles for RLS
assertions. Production databases must never be truncated by a test fixture.
