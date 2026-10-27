# Taskify Identity

Companies, accounts, password hashing, login sessions, operator provisioning and user creation.

Status: operator provisioning and first-party authentication are implemented and
validated with real PostgreSQL and Chromium. Company-user creation remains in US4.
This service has no model, embedding or document-provider dependency.

The domain and application layers import only standard-library code and owned core
ports. HTTP, PostgreSQL and provider adapters point inward. No service reads another
service's database or private file mount. Runtime roles never own tables or bypass
RLS. Migration credentials exist only in the operator-only migration service.

From this directory:

```sh
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run lint-imports
uv run pytest tests/unit tests/contract
TASKIFY_RUN_DB_TESTS=1 uv run pytest tests/integration
```

Real storage tests require the repository's private `.env` and PostgreSQL on loopback
port 55432, or explicit TASKIFY_TEST_DATABASE_URL/TASKIFY_TEST_MIGRATION_DATABASE_URL
values targeting only `identity_test`. Fixtures reject production database names.
Use the `identity-migrate` Compose service for owned schema migrations. Passwords and
private configuration must never be logged; tests use short tracebacks and hidden
SQL parameters. All identifiers are UUIDs and timestamps are aware UTC values.

From the project root, initialize PostgreSQL and the owned schema:

```sh
docker compose up -d postgres
docker compose run --rm --build identity-migrate
docker compose run --rm identity taskify-admin create --company-name "Company A" --display-name "Admin A" --email admin-a@example.test
```

The CLI prompts twice without echoing the initial password. Automation may use
`--password-stdin`; only the line terminator is removed. Never put the password in
arguments. Use exactly one company-name or company-id selector. Success is JSON
with company_id/admin_id/role/must_change_password/company_created. Exit statuses:
0 success; 2 validation; 3 unavailable email; 4 unknown company; 5 storage/configuration.
Duplicate provisioning rolls back the optional new company as well as the account.

For an isolated auth demonstration before the other services are ready, run these
in separate terminals, with the API origin matching the browser exactly:

```sh
docker compose run --rm --no-deps -p 127.0.0.1:18081:8000 -e PUBLIC_ORIGIN=http://127.0.0.1:5173 identity
TASKIFY_API_URL=http://127.0.0.1:18081 pnpm --dir frontend run dev
```

Open `http://127.0.0.1:5173`. Initial sessions are restricted until password change.
Passwords are Argon2id hashes; cookies contain random 256-bit opaque tokens and only
their SHA-256 digests are persisted. Production cookies use Secure/HttpOnly/SameSite=Lax,
Path=/, no Domain and the __Host-taskify_session name. All authenticated browser
mutations require exact Origin plus a session-bound synchronizer CSRF header.

Login account locks fence credential verification and session insertion against
password changes. A change increments credential_version, revokes all previous
account sessions and creates one replacement in one transaction. Five failed logins
for the same normalized email within 15 minutes impose a 15-minute pause, including
unknown emails. Error messages do not disclose email membership.

Login inactivity expires exactly at 30 minutes. User-triggered session reads may
refresh activity; polling/background validation never does. Internal caller secrets
are separate for each API/worker. Workers can use stored session UUIDs only with
background activity. Internal requests always require the initial password to have
been changed. No public route can create an admin, select a company/role or access
another account. Logout revokes only its login, preserving future Chat-owned history.

Public and internal contract definitions are under
`specs/001-company-knowledge-qa/contracts/`. Unknown mutation fields, bad Origin,
missing/invalid CSRF and invalid session claims fail closed. Service credentials are
caller-specific, internal routes are not proxied, polling/background resolution
never refreshes inactivity, and no positive authentication cache exists.

Readiness is nonpublic and must check owned storage/configuration without a paid
provider call. Provider/parser/storage failures use redacted typed errors, never an
invented absence of knowledge. Company text, prompts, passwords, cookies, API keys
and CSRF secrets are excluded from normal logs and third-party tracing.

Company admins who have changed their initial password can use **Create user** or
`POST /api/v1/users` with exactly `display_name`, `email`, `initial_password`.
Origin plus current CSRF are required; the session is validated again in the committing
transaction. The company derives from the caller and role is always `user` with
mandatory first-password change. Unknown company/role fields are rejected. Duplicate
normalized emails in any company return the same generic `account_unavailable` 409,
with no partial account. The initial password is hashed and never returned, logged or
stored in browser persistence; the admin shares it through the company's trusted
channel. The form clears its secret after every attempt. User-creation tests use real
owned storage and CLI-provisioned browser credentials; they require no AI provider.

Operational readiness and metrics are available only on the private service port:
`/health/live`, `/health/ready`, `/metrics`. Ingress returns 404 for these paths.
Counters contain only request/status-class/time and readiness totals; they are process
local and reset on restart. Workers emit fixed outcome/error-code/attempt/count fields,
never documents, queries, prompts, chat text, identities or secrets. Normal readiness
makes no paid provider call; Knowledge/Chat additionally check configured first-party
dependency readiness over bounded nonredirecting HTTP. Third-party tracing remains off.
See `infra/backup-restore.md` for consistent owned-database/private-original recovery.
