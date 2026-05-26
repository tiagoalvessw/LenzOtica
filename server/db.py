import os
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            os.getenv("DATABASE_URL"),
            min_size=1,
            max_size=5,
            open=True,
        )
    return _pool


def execute(query: str, params: tuple = ()) -> None:
    with _get_pool().connection() as conn:
        conn.execute(query, params)


def executemany(query: str, params_seq) -> None:
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, params_seq)


def fetchall(query: str, params: tuple = ()) -> list[dict]:
    with _get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            return cur.fetchall()


def fetchone(query: str, params: tuple = ()) -> dict | None:
    with _get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            return cur.fetchone()


def fetchval(query: str, params: tuple = ()):
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return row[0] if row else None
