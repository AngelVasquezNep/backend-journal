"""Run this service's owned migrations with explicit operator database credentials.

All identifiers are UUIDs; timestamps are UTC.
Text lengths count Unicode code points, not bytes, unless explicitly stated.
No provider, cross-service database, or application bootstrap is invoked.
"""

import os

from alembic import context
from sqlalchemy import create_engine, pool

url = os.environ["DATABASE_URL"]
if context.is_offline_mode():
    context.configure(url=url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
