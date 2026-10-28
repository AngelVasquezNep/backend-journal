# Consistent single-host backup and recovery

Taskify has three owned PostgreSQL databases plus Knowledge's private originals.
A database-only or files-only backup is not a consistent recovery set. This initial
single-host procedure uses a maintenance window: stop ingress/APIs/workers and exclude
operator CLI writes before taking all four artifacts. Do not advertise an RPO/RTO;
none has been measured. The automated exercise uses disposable fixture databases,
not customer data or the running application databases.

Keep separate runtime/migration role credentials and provider/session/service secrets
in the operator's secret manager. Backups contain documents, private chats, password
hashes, session digests and CSRF material: use owner-private storage and the operator's
encryption/retention/access policy. Never commit or publish dumps or credential files.
Restoring database state does not replace secret rotation or invalidate a compromised
session; revoke sessions through an explicitly reviewed operator procedure when needed.

Before a real backup, inspect readiness and record application image digests, migration
heads, pipeline/model versions, database server version and the storage paths
(`data/postgres/` and `data/originals/` in the local Compose setup).
Freeze all writes, including CLI provisioning and cleanup:

```sh
docker compose stop web identity knowledge knowledge-worker chat chat-worker
```

Use a private backup directory (`umask 077`). Dump each owned database separately through
its own migration role; the host operator may execute PostgreSQL's tools inside the
Postgres container. Do not grant Docker/operator access to Chat. For example, redirect
stdout to a private file; the shell expands the already private container environment
without putting a password in command arguments:

```sh
docker compose exec -T postgres sh -c 'PGPASSWORD="$IDENTITY_MIGRATION_PASSWORD" pg_dump -h 127.0.0.1 -U identity_migration --enable-row-security -Fc identity' > /private/backup/identity.dump
docker compose exec -T postgres sh -c 'PGPASSWORD="$KNOWLEDGE_MIGRATION_PASSWORD" pg_dump -h 127.0.0.1 -U knowledge_migration --enable-row-security -Fc knowledge' > /private/backup/knowledge.dump
docker compose exec -T postgres sh -c 'PGPASSWORD="$CHAT_MIGRATION_PASSWORD" pg_dump -h 127.0.0.1 -U chat_migration --enable-row-security -Fc chat' > /private/backup/chat.dump
docker compose run --rm --no-deps --entrypoint tar knowledge -C /data -cf - originals > /private/backup/originals.tar
```

`--enable-row-security` is required because FORCE RLS remains on; the dedicated migration
role has the explicitly scoped owner policies needed for a complete owned snapshot.
Verify exit codes, archive membership, artifact digests and permissions before unfreezing
writes. Keep the three dumps, originals archive and metadata together as one immutable
backup set. No service may write between the first dump and last file snapshot.

Restore first to an isolated host/network and empty owned databases with the matching
role names, default privileges and pgvector installed only in Knowledge. Use the matching
PostgreSQL major version and reviewed application images. Stop all writers and restore
all three databases plus the matching private originals; never mix dates or point live
services at a partly restored set. Use each migration role for its own dump, preserve
runtime ACLs and function grants, and do not restore owners as a superuser. The isolated
exercise uses `pg_restore --exit-on-error --no-owner --no-comments`: preinstalled pgvector
remains operator-owned, so its comment must not be reassigned by a migration role.
Runtime grants/ACLs remain restored; do not use --no-acl. Original filenames remain private
server-generated keys, with the Knowledge UID/permissions; do not expose the archive via
static hosting. Archive extraction must reject traversal/symlinks outside the destination.

Before enabling ingress, verify schema heads/roles, original size/SHA-256, current pointers,
RLS without actor context, cross-company/account denials and source unavailability after
removal/replacement. Run migrations only with operator-owned credentials. Start Identity,
Knowledge, Chat and workers, then nonpublic readiness, then ingress. Online session
validation still enforces current inactivity/revocation; a restored old session never
becomes fresh merely because the database was restored.

Pending jobs/turns remain durable. Expired leases are reclaimed with a higher fencing
version; unexpired abandoned leases wait until their 120-second ingestion / 30-second
turn boundary. Workers restart complete attempts with fresh authorized history/evidence.
They never reuse a previous candidate or source receipt. Provider calls/cost may repeat;
unique terminal constraints prevent duplicate saved answers. Accepted model/graph/prompt/
profile versions must still have compatible handlers. Retrieval uses Knowledge's then-active
configuration; incompatible vector spaces fail explicitly. Source changes remain effective
at the final validation checkpoint and on every later source open.

Exercise recovery without touching live data:

```sh
TASKIFY_RUN_RESTORE=1 services/knowledge/.venv/bin/pytest tests/integration/test_restore_recovery.py -q
```

This explicitly operator-run test creates six randomly named `taskify_restore_<run>_*`
databases, migrates/seeds three isolated sources, captures quiescent owned dumps and an
original archive, restores three empty targets, checks original identity and forced RLS,
then reclaims a pending ingestion job and turn. Cleanup drops only that run's validated
database names. The test never resets `identity`, `knowledge`, `chat` or their test databases.
Keep actual exercise results and limitations in the feature validation record.
