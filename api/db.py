import os
from contextlib import contextmanager

from dotenv import load_dotenv
from psycopg2.pool import SimpleConnectionPool

load_dotenv()

_pool: SimpleConnectionPool | None = None


def init_pool():
    global _pool
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL not set. Copy .env.example to .env and adjust if needed."
        )
    _pool = SimpleConnectionPool(minconn=1, maxconn=10, dsn=dsn)


def close_pool():
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


@contextmanager
def get_cursor():
    """FastAPI dependency: yields a cursor on a pooled, read-only connection."""
    if _pool is None:
        init_pool()
    conn = _pool.getconn()
    conn.set_session(readonly=True, autocommit=True)
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        _pool.putconn(conn)
