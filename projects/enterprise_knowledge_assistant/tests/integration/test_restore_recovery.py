"""Opt-in owned-database/private-original restore exercise uses isolated disposable databases, never live data."""

import hashlib
import os
import re
import subprocess
import tarfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[2]


def operator(command: list[str], *, payload: bytes | None = None) -> bytes:
    """Run explicit host operator work with captured diagnostics; never echo secrets or dumps in failures."""
    result = subprocess.run(
        command, input=payload, cwd=ROOT, capture_output=True, check=False
    )
    if result.returncode:
        from tests.fixtures.public import save_private

        save_private(
            Path("/tmp/taskify-restore-diagnostic.json"),
            {"diagnostic": result.stderr.decode(errors="replace")},
        )
        raise RuntimeError(
            "The isolated restore operator command failed; private diagnostics were retained for review."
        )
    return result.stdout


def local_environment() -> dict[str, str]:
    """Read only the private local development role credentials, never a shell-evaluated configuration."""
    result = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def psql(statement: str, database: str = "postgres") -> None:
    """Use the explicitly operator-owned bootstrap connection only for isolated database lifecycle."""
    operator(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "postgres",
            "-d",
            database,
        ],
        payload=statement.encode(),
    )


def database_name(run: str, service: str, stage: str) -> str:
    """Constrain creation/drop targets to this test's random dedicated restore namespace."""
    value = f"taskify_restore_{run}_{service}_{stage}"
    if not re.fullmatch(
        r"taskify_restore_[0-9a-f]{8}_(identity|knowledge|chat)_(seed|target)", value
    ):
        raise ValueError("Invalid isolated restore database identity.")
    return value


def connect(environment: dict, service: str, database: str, *, migration: bool = False):
    """Connect with only the owning role; runtime verification never uses superuser authority."""
    role = f"{service}_migration" if migration else f"{service}_runtime"
    key = (
        f"{service.upper()}_MIGRATION_PASSWORD"
        if migration
        else f"{service.upper()}_DB_PASSWORD"
    )
    return psycopg.connect(
        host="127.0.0.1",
        port=55432,
        dbname=database,
        user=role,
        password=environment[key],
    )


@pytest.mark.restore
def test_consistent_owned_restore_and_pending_claim_recovery(tmp_path) -> None:
    """Restore all three owned snapshots plus exact original bytes, then verify RLS and pending work recovery."""
    if os.environ.get("TASKIFY_RUN_RESTORE") != "1":
        pytest.skip(
            "Explicit isolated restore exercise requires host Docker/operator access."
        )
    environment = local_environment()
    run = uuid4().hex[:8]
    created = []
    company, account, session, item, revision, job, conversation, turn, message = (
        uuid4() for _ in range(9)
    )
    now = datetime.now(UTC)
    original = b"Company restore policy grants 21 days."
    key = uuid4().hex
    originals = tmp_path / "seed-originals"
    originals.mkdir(mode=0o700)
    (originals / key).write_bytes(original)
    (originals / key).chmod(0o400)
    try:
        for service in ("identity", "knowledge", "chat"):
            for stage in ("seed", "target"):
                name = database_name(run, service, stage)
                psql(
                    f"CREATE DATABASE {name} OWNER {service}_migration; REVOKE CONNECT ON DATABASE {name} FROM PUBLIC; GRANT CONNECT ON DATABASE {name} TO {service}_migration,{service}_runtime;"
                )
                created.append(name)
                psql(
                    f"""REVOKE CREATE ON SCHEMA public FROM PUBLIC;
                    GRANT USAGE ON SCHEMA public TO {service}_runtime;
                    ALTER DEFAULT PRIVILEGES FOR ROLE {service}_migration IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO {service}_runtime;
                    ALTER DEFAULT PRIVILEGES FOR ROLE {service}_migration IN SCHEMA public GRANT USAGE,SELECT ON SEQUENCES TO {service}_runtime;
                    ALTER DEFAULT PRIVILEGES FOR ROLE {service}_migration IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;""",
                    name,
                )
                if service == "knowledge":
                    psql("CREATE EXTENSION vector;", name)
            seed = database_name(run, service, "seed")
            env = dict(os.environ)
            env["DATABASE_URL"] = (
                f"postgresql+psycopg://{service}_migration:{environment[service.upper() + '_MIGRATION_PASSWORD']}@127.0.0.1:55432/{seed}"
            )
            result = subprocess.run(
                [
                    str(ROOT / f"services/{service}/.venv/bin/alembic"),
                    "-c",
                    str(ROOT / f"services/{service}/alembic.ini"),
                    "upgrade",
                    "head",
                ],
                env=env,
                check=False,
                cwd=ROOT,
                capture_output=True,
            )
            assert result.returncode == 0, "Owned isolated seed migration failed."
        with connect(
            environment,
            "identity",
            database_name(run, "identity", "seed"),
            migration=True,
        ) as connection:
            connection.execute(
                "INSERT INTO companies VALUES(%s,%s,%s)",
                (company, "Restore fixture", now),
            )
            connection.execute(
                "INSERT INTO accounts VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    account,
                    company,
                    "restore@example.test",
                    "restore@example.test",
                    "Restore reader",
                    "user",
                    "$argon2id$fixture-only",
                    1,
                    False,
                    now,
                    now,
                ),
            )
            connection.execute(
                "INSERT INTO login_sessions VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (session, account, "a" * 64, 1, "b" * 64, now, now, None),
            )
        with connect(
            environment,
            "knowledge",
            database_name(run, "knowledge", "seed"),
            migration=True,
        ) as connection:
            connection.execute(
                "INSERT INTO pipeline_configurations VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    "restore-pipeline",
                    "nfc-newlines-offsets-v1",
                    Jsonb({"fixture": "restore"}),
                    "recursive-tiktoken-v1",
                    800,
                    100,
                    "text-embedding-3-small",
                    1536,
                    "cl100k_base",
                    now,
                ),
            )
            connection.execute(
                "INSERT INTO knowledge_items VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    item,
                    company,
                    "Restore policy",
                    account,
                    None,
                    revision,
                    1,
                    now,
                    now,
                    None,
                ),
            )
            connection.execute(
                "INSERT INTO knowledge_revisions VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    revision,
                    company,
                    item,
                    account,
                    "policy.txt",
                    "text/plain",
                    len(original),
                    hashlib.sha256(original).hexdigest(),
                    key,
                    "processing",
                    "restore-pipeline",
                    None,
                    now,
                    None,
                ),
            )
            connection.execute(
                "INSERT INTO ingestion_jobs VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    job,
                    company,
                    revision,
                    "restore-pipeline",
                    "running",
                    1,
                    now,
                    uuid4(),
                    now - timedelta(seconds=1),
                    1,
                    now,
                    None,
                    now,
                ),
            )
        with connect(
            environment, "chat", database_name(run, "chat", "seed"), migration=True
        ) as connection:
            connection.execute(
                "INSERT INTO conversations VALUES(%s,%s,%s,%s,%s,%s)",
                (conversation, company, account, 1, now, now),
            )
            connection.execute(
                """INSERT INTO chat_turns(id,company_id,account_id,conversation_id,client_message_id,user_message_id,accepted_login_session_id,state,attempt_count,lease_version,created_at,ai_mode,model,graph_version,prompt_version,model_config_version)
                VALUES(%s,%s,%s,%s,%s,%s,%s,'queued',0,0,%s,'stub','stub-fixture-v1','graph-v1','prompt-v1','responses-v1')""",
                (turn, company, account, conversation, uuid4(), message, session, now),
            )
            connection.execute(
                """INSERT INTO chat_messages(id,company_id,account_id,conversation_id,turn_id,sequence,sender,content,created_at)
                VALUES(%s,%s,%s,%s,%s,1,'user','What is the company restore policy?',%s)""",
                (message, company, account, conversation, turn, now),
            )
        # No writers exist against these seed databases: all three dumps and files form one quiescent set.
        dumps = {}
        for service in ("identity", "knowledge", "chat"):
            seed = database_name(run, service, "seed")
            script = f'PGPASSWORD="${service.upper()}_MIGRATION_PASSWORD" pg_dump -h 127.0.0.1 -U {service}_migration --enable-row-security -Fc {seed}'
            dumps[service] = operator(
                ["docker", "compose", "exec", "-T", "postgres", "sh", "-c", script]
            )
            assert dumps[service].startswith(b"PGDMP"), (
                "A valid owned custom-format snapshot is required."
            )
        archive = tmp_path / "originals.tar"
        with tarfile.open(archive, "w") as stream:
            stream.add(originals / key, arcname=key)
        restored = tmp_path / "restored-originals"
        restored.mkdir(mode=0o700)
        with tarfile.open(archive) as stream:
            stream.extractall(restored, filter="data")
        assert (restored / key).read_bytes() == original
        for service, dump in dumps.items():
            target = database_name(run, service, "target")
            script = f'PGPASSWORD="${service.upper()}_MIGRATION_PASSWORD" pg_restore -h 127.0.0.1 -U {service}_migration --exit-on-error --no-owner --no-comments -d {target}'
            operator(
                ["docker", "compose", "exec", "-T", "postgres", "sh", "-c", script],
                payload=dump,
            )
        for service, table in (
            ("identity", "accounts"),
            ("knowledge", "knowledge_items"),
            ("chat", "conversations"),
        ):
            with connect(
                environment, service, database_name(run, service, "target")
            ) as connection:
                assert (
                    connection.execute(
                        sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
                    ).fetchone()[0]
                    == 0
                )
                connection.execute(
                    "SELECT set_config('taskify.company_id',%s,true),set_config('taskify.account_id',%s,true)",
                    (str(company), str(account)),
                )
                assert (
                    connection.execute(
                        sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
                    ).fetchone()[0]
                    == 1
                )
                connection.execute(
                    "SELECT set_config('taskify.company_id',%s,true)", (str(uuid4()),)
                )
                assert (
                    connection.execute(
                        sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
                    ).fetchone()[0]
                    == 0
                )
        with connect(
            environment, "knowledge", database_name(run, "knowledge", "target")
        ) as connection:
            recovered = connection.execute(
                "SELECT id,lease_version,attempt_count FROM taskify_claim_ingestion(%s,%s)",
                (uuid4(), now),
            ).fetchone()
            assert recovered == (job, 2, 2)
        with connect(
            environment, "chat", database_name(run, "chat", "target")
        ) as connection:
            recovered = connection.execute(
                "SELECT id,accepted_login_session_id,retrieval_config_version FROM taskify_claim_turn(%s,%s)",
                (uuid4(), now),
            ).fetchone()
            assert recovered == (turn, session, None)
        with connect(
            environment, "identity", database_name(run, "identity", "target")
        ) as connection:
            assert (
                connection.execute(
                    "SELECT id FROM taskify_session(%s,NULL)", ("a" * 64,)
                ).fetchone()[0]
                == session
            )
    finally:
        for name in reversed(created):
            assert re.fullmatch(
                r"taskify_restore_[0-9a-f]{8}_(identity|knowledge|chat)_(seed|target)",
                name,
            )
            psql(f"DROP DATABASE {name} WITH (FORCE);")
