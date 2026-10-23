import os
import threading
from contextlib import contextmanager

import psycopg2
from dotenv import load_dotenv
from psycopg2.pool import ThreadedConnectionPool

load_dotenv()

MAX_CONNECTIONS = 10
_pool: ThreadedConnectionPool | None = None
_slots: threading.BoundedSemaphore | None = None


def init_pool():
    global _pool, _slots
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL not set. Copy .env.example to .env and adjust if needed."
        )
    _pool = ThreadedConnectionPool(minconn=1, maxconn=MAX_CONNECTIONS, dsn=dsn)
    # psycopg2's pool raises when all connections are in use; this makes extra requests wait instead.
    _slots = threading.BoundedSemaphore(MAX_CONNECTIONS)


def close_pool():
    global _pool, _slots
    if _pool is not None:
        _pool.closeall()
        _pool = None
        _slots = None


def _checkout():
    """Borrow a live connection. A pooled connection can be closed by the server while idle
    (Neon suspends idle compute), so ping it and replace it if it is dead."""
    last_error = None
    for _ in range(_pool.maxconn):
        conn = _pool.getconn()
        try:
            conn.set_session(readonly=True, autocommit=True)
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return conn
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
            last_error = exc
            _pool.putconn(conn, close=True)
    raise last_error


@contextmanager
def get_cursor():
    """Yields a cursor on a pooled, read-only connection."""
    if _pool is None:
        init_pool()
    _slots.acquire()
    try:
        conn = _checkout()
        try:
            with conn.cursor() as cur:
                yield cur
        finally:
            _pool.putconn(conn)
    finally:
        _slots.release()
