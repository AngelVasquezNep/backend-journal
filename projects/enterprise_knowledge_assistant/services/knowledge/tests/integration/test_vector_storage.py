"""Real pgvector checks use the Knowledge-owned test database and exact vector space."""

import pytest
from sqlalchemy import Engine, text

pytestmark = pytest.mark.integration


def test_vector_dimensions_are_1536(runtime_engine: Engine) -> None:
    """Require the installed extension and verify the initial embedding shape in PostgreSQL."""
    vector = "[" + ",".join(["0"] * 1536) + "]"
    with runtime_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
            == 1
        )
        assert (
            connection.execute(
                text("SELECT vector_dims(CAST(:vector AS vector(1536)))"), {"vector": vector}
            ).scalar()
            == 1536
        )
