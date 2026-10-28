# Project-local storage

Run these commands from the project directory. Compose stores PostgreSQL databases in
`data/postgres/` and uploaded originals in `data/originals/`. The API and ingestion worker
share the originals directory. Git and Docker builds exclude `data/`.

The PostgreSQL Unix socket remains in the `postgres-socket` named volume so the database
and password-configuration job can communicate inside Docker's Linux environment.
Images, build cache, and container logs remain managed by Docker Desktop.

## New installation

After initializing `.env` and building the images as described in the README:

```sh
mkdir -p data/postgres data/originals
docker compose run --rm --no-deps --user root --entrypoint chown knowledge 10001:10001 /data/originals
docker compose up -d
```

The ownership command makes the originals directory writable by the application's
non-root user. PostgreSQL initializes its own empty directory on first startup.

## Start empty with existing named volumes

To start fresh without copying the old databases or documents, keep your existing
`.env` and application images. Stop the project, prepare empty local directories, and
start with the new mounts:

```sh
docker compose stop
mkdir -p data/postgres data/originals
test -z "$(ls -A data/postgres)" && test -z "$(ls -A data/originals)"
```

Continue only if the emptiness check succeeds. If either directory already contains
data, stop here and back up or move both directories before proceeding.

```sh
docker compose run --rm --no-deps --user root --entrypoint chown knowledge 10001:10001 /data/originals
docker compose up -d
docker compose ps
```

Startup creates empty databases and applies migrations. Create a new administrator
using the README's [administrator command](../README.md#create-the-first-administrator).
No previous users, chats, or uploaded documents are imported. The old
`taskify_postgres-data` and `taskify_originals` volumes, if present, remain untouched;
they are no longer attached to this Compose setup. Avoid volume pruning if you want
to retain them.

## Move existing named-volume data

Changing mounts does not copy existing data. Move both the databases and matching
originals together. Keep the existing `.env` and PostgreSQL image version. Take a
[consistent backup](backup-restore.md) first if this data is important.

The commands below apply to the original `taskify_postgres-data` and `taskify_originals`
volumes. Inspect both before proceeding; a missing volume means these commands do not
match your installation. Do not allow CLI provisioning or other writers during the move.

```sh
docker volume inspect taskify_postgres-data taskify_originals
docker compose stop
mkdir -p data/postgres data/originals
```

Only copy PostgreSQL files after the database has stopped cleanly. Both destination
directories must be empty; these commands refuse to overwrite a populated destination.

```sh
docker compose run --rm --no-deps --user root --entrypoint sh \
  -v taskify_postgres-data:/source:ro postgres -ec \
  'test -f /source/PG_VERSION; test -z "$(ls -A /var/lib/postgresql/data)"; cp -a /source/. /var/lib/postgresql/data/'

docker compose run --rm --no-deps --user root --entrypoint sh \
  -v taskify_originals:/source:ro knowledge -ec \
  'test -z "$(ls -A /data/originals)"; cp -a /source/. /data/originals/; chown -R 10001:10001 /data/originals'
```

If either copy fails, leave the application stopped and investigate before starting it.
The source volumes remain intact. After both copies succeed:

```sh
docker compose up -d
docker compose ps
```

Verify login, an existing chat, and downloading an existing document. Keep the old
volumes until you have verified the new storage and a backup. They are no longer
attached to Compose and could be deleted by a later volume-pruning command.

## Backups and cleanup

Continue using the [backup and restore guide](backup-restore.md): its commands access
the same container paths regardless of the host storage location. Do not copy a running
PostgreSQL data directory as a backup or edit its internal files manually.

`docker compose down -v` removes the shared socket volume but leaves the bind-mounted
`data/` directories intact. Deleting those directories deletes the application data.
