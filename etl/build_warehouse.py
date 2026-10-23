"""Builds (or rebuilds) the star-schema warehouse from staging.

Runs any pending schema migrations first, then re-runs every script in
warehouse/transforms/ in filename order. Transforms are idempotent
(TRUNCATE + INSERT, or REFRESH MATERIALIZED VIEW) — safe to run this
any time staging changes, e.g. after a new month is loaded.

Usage: python etl/build_warehouse.py
"""
import pathlib
import sys
import time

from db import get_conn
from run_migrations import main as run_migrations

TRANSFORMS_DIR = pathlib.Path(__file__).resolve().parent.parent / "warehouse" / "transforms"


def main():
    print("Applying pending schema migrations...")
    run_migrations()

    conn = get_conn()
    conn.autocommit = False
    try:
        for path in sorted(TRANSFORMS_DIR.glob("*.sql")):
            sql = path.read_text(encoding="utf-8")
            t0 = time.time()
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            print(f"  {path.name}: {time.time() - t0:.1f}s")
    finally:
        conn.close()

    print("\nWarehouse build complete.")


if __name__ == "__main__":
    sys.exit(main())
