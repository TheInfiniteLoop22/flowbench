"""Applies warehouse/migrations/*.sql in filename order, once each.

Usage: python etl/run_migrations.py
"""
import pathlib

from db import get_conn

MIGRATIONS_DIR = pathlib.Path(__file__).resolve().parent.parent / "warehouse" / "migrations"


def main():
    conn = get_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(filename text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            conn.commit()

            cur.execute("SELECT filename FROM schema_migrations")
            applied = {row[0] for row in cur.fetchall()}

        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in applied:
                print(f"skip  {path.name} (already applied)")
                continue
            sql = path.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,)
                )
            conn.commit()
            print(f"apply {path.name}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
