import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_conn():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL not set. Copy .env.example to .env and adjust if needed."
        )
    return psycopg2.connect(dsn)
