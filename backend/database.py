from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from config import DATABASE_POOL_MAX_SIZE, DATABASE_POOL_MIN_SIZE, DATABASE_URL


_connection_pool: ConnectionPool | None = None


def initialize_connection_pool() -> None:
    """Create the shared API pool and fail fast when PostgreSQL is unavailable."""
    global _connection_pool
    if _connection_pool is not None:
        return
    _connection_pool = ConnectionPool(
        conninfo=DATABASE_URL,
        min_size=DATABASE_POOL_MIN_SIZE,
        max_size=DATABASE_POOL_MAX_SIZE,
        kwargs={"row_factory": dict_row},
        open=False,
    )
    _connection_pool.open(wait=True)


def close_connection_pool() -> None:
    global _connection_pool
    if _connection_pool is None:
        return
    _connection_pool.close()
    _connection_pool = None


@contextmanager
def get_connection() -> Iterator[Connection]:
    if _connection_pool is None:
        initialize_connection_pool()
    assert _connection_pool is not None
    with _connection_pool.connection() as connection:
        yield connection
