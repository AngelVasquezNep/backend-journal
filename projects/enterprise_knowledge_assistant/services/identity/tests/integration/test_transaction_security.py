"""Real PostgreSQL role and pooling checks supplement application predicates with actual RLS."""

from uuid import uuid4

import pytest
from sqlalchemy import Engine, text

from taskify_identity.adapters.outbound.postgres.unit_of_work import SqlUnitOfWork

pytestmark = pytest.mark.integration


def test_runtime_role_and_transaction_context(runtime_engine: Engine) -> None:
    """Verify non-owner/no-BYPASSRLS role and transaction-local company/account context cleanup."""
    company, account = uuid4(), uuid4()
    with SqlUnitOfWork(runtime_engine, company, account) as uow:
        assert uow.session is not None
        row = uow.session.execute(
            text(
                "SELECT current_setting('taskify.company_id'), current_setting('taskify.account_id')"
            )
        ).one()
        assert row == (str(company), str(account))
        role = uow.session.execute(
            text(
                "SELECT rolsuper, rolbypassrls, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user"
            )
        ).one()
        assert role == (False, False, False, False)
        uow.commit()
    with runtime_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT nullif(current_setting('taskify.company_id', true), '')")
            ).scalar()
            is None
        )
        assert (
            connection.execute(
                text("SELECT nullif(current_setting('taskify.account_id', true), '')")
            ).scalar()
            is None
        )


def test_rls_blocks_foreign_rows_and_missing_context(
    runtime_engine: Engine, migration_engine: Engine
) -> None:
    """Force tenant policies on real rows, verify rollback, and remove only this private test table."""
    table = "fixture_" + uuid4().hex
    owner, other = uuid4(), uuid4()
    with migration_engine.begin() as connection:
        # The table identifier is generated in this test, never accepted from external input.
        connection.execute(
            text(f"CREATE TABLE {table} (company_id uuid NOT NULL, value text NOT NULL)")
        )
        connection.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        connection.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        connection.execute(
            text(
                f"CREATE POLICY tenant ON {table} USING (company_id::text = current_setting('taskify.company_id', true)) WITH CHECK (company_id::text = current_setting('taskify.company_id', true))"
            )
        )
    try:
        with SqlUnitOfWork(runtime_engine, owner) as uow:
            assert uow.session is not None
            uow.session.execute(
                text(f"INSERT INTO {table} VALUES (:owner, :value)"),
                {"owner": owner, "value": "owned fixture"},
            )
            uow.commit()
        with SqlUnitOfWork(runtime_engine, other) as uow:
            assert uow.session is not None
            assert uow.session.execute(text(f"SELECT value FROM {table}")).all() == []
        with runtime_engine.connect() as connection:
            assert connection.execute(text(f"SELECT value FROM {table}")).all() == []
        with SqlUnitOfWork(runtime_engine, owner) as uow:
            assert uow.session is not None
            uow.session.execute(
                text(f"INSERT INTO {table} VALUES (:owner, :value)"),
                {"owner": owner, "value": "rolled back"},
            )
        with SqlUnitOfWork(runtime_engine, owner) as uow:
            assert uow.session is not None
            assert uow.session.execute(text(f"SELECT value FROM {table}")).scalars().all() == [
                "owned fixture"
            ]
    finally:
        with migration_engine.begin() as connection:
            connection.execute(text(f"DROP TABLE {table}"))
