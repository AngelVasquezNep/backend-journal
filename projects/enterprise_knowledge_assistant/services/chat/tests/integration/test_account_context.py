"""Actual Chat RLS must deny a different account even when both belong to the same company."""

from uuid import uuid4

import pytest
from sqlalchemy import Engine, text

from taskify_chat.adapters.outbound.postgres.unit_of_work import SqlUnitOfWork

pytestmark = pytest.mark.integration


def test_same_company_other_account_cannot_read(
    runtime_engine: Engine, migration_engine: Engine
) -> None:
    """Verify both trusted settings in a forced policy; a company admin receives no account bypass."""
    table = "fixture_" + uuid4().hex
    company, account, other = uuid4(), uuid4(), uuid4()
    with migration_engine.begin() as connection:
        connection.execute(
            text(f"CREATE TABLE {table} (company_id uuid, account_id uuid, content text)")
        )
        connection.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        connection.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        connection.execute(
            text(
                f"CREATE POLICY owner ON {table} USING (company_id::text = current_setting('taskify.company_id', true) AND account_id::text = current_setting('taskify.account_id', true))"
            )
        )
    try:
        with SqlUnitOfWork(runtime_engine, company, account) as uow:
            assert uow.session is not None
            uow.session.execute(
                text(f"INSERT INTO {table} VALUES (:company, :account, :content)"),
                {"company": company, "account": account, "content": "private fixture"},
            )
            uow.commit()
        with SqlUnitOfWork(runtime_engine, company, other) as uow:
            assert uow.session is not None
            assert uow.session.execute(text(f"SELECT content FROM {table}")).all() == []
    finally:
        with migration_engine.begin() as connection:
            connection.execute(text(f"DROP TABLE {table}"))
