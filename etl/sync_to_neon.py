"""Copies the dimensions and rollups the API reads from the local warehouse into another
Postgres (production: Neon) as plain tables, in ONE transaction, so readers see either the
old data or the new data and never a half-copied mix.

Usage:
    python etl/sync_to_neon.py --target "postgresql://..."            # dry run: lists what would be copied
    python etl/sync_to_neon.py --target "postgresql://..." --yes      # does it

The source is DATABASE_URL (the local warehouse). The target needs the PostGIS extension
(Neon has it). Run warehouse_checks.py on the source first.
"""
import argparse
import io
import sys

import psycopg2

from db import get_conn

SCHEMA = "warehouse"
TABLES = [
    "dim_station",
    "dim_time",
    "city_stats_agg",
    "demand_by_hour_agg",
    "trips_by_day_agg",
    "station_daily_demand_agg",
    "station_hourly_demand_agg",
    "station_hourly_balance_hourly_agg",
    "rebalancing_candidates_agg",
]


def column_defs(cur, table):
    cur.execute(
        """
        SELECT a.attname, format_type(a.atttypid, a.atttypmod)
        FROM pg_attribute a
        WHERE a.attrelid = %s::regclass AND a.attnum > 0 AND NOT a.attisdropped
        ORDER BY a.attnum
        """,
        (f"{SCHEMA}.{table}",),
    )
    return cur.fetchall()


def index_defs(cur, table):
    cur.execute(
        "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = %s AND tablename = %s",
        (SCHEMA, table),
    )
    return cur.fetchall()


def row_count(cur, table):
    cur.execute(f"SELECT count(*) FROM {SCHEMA}.{table}")
    return cur.fetchone()[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="target database URL")
    ap.add_argument("--yes", action="store_true", help="actually copy (default is a dry run)")
    args = ap.parse_args()

    src = get_conn()
    scur = src.cursor()
    print("Source tables:")
    plan = {}
    for t in TABLES:
        n = row_count(scur, t)
        plan[t] = n
        print(f"  {t:36} {n:>10,} rows")
    if not args.yes:
        print("\nDry run. Re-run with --yes to copy into the target.")
        return 0

    dst = psycopg2.connect(args.target)
    dst.autocommit = False
    dcur = dst.cursor()
    try:
        dcur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        dcur.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
        for t in TABLES:
            cols = column_defs(scur, t)
            names = ", ".join(c[0] for c in cols)
            dcur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{t}_new")
            dcur.execute(
                f"CREATE TABLE {SCHEMA}.{t}_new (" + ", ".join(f'"{n}" {ty}' for n, ty in cols) + ")"
            )
            buf = io.StringIO()
            scur.copy_expert(f"COPY (SELECT {names} FROM {SCHEMA}.{t}) TO STDOUT", buf)
            buf.seek(0)
            dcur.copy_expert(f"COPY {SCHEMA}.{t}_new ({names}) FROM STDIN", buf)
            for name, definition in index_defs(scur, t):
                definition = definition.replace(f"{SCHEMA}.{t} ", f"{SCHEMA}.{t}_new ").replace(
                    name, name + "_new", 1
                )
                dcur.execute(definition)
            print(f"  loaded {t} ({plan[t]:,} rows)")

        # Swap: all inside the same transaction.
        for t in TABLES:
            dcur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{t}")
            dcur.execute(f"ALTER TABLE {SCHEMA}.{t}_new RENAME TO {t}")
            for name, _ in index_defs(scur, t):
                dcur.execute(f"ALTER INDEX IF EXISTS {SCHEMA}.{name}_new RENAME TO {name}")
            dcur.execute(f"ANALYZE {SCHEMA}.{t}")

        # Verify before committing.
        for t in TABLES:
            n = row_count(dcur, t)
            if n != plan[t]:
                raise RuntimeError(f"{t}: copied {n:,} rows, expected {plan[t]:,}")
        dst.commit()
        print("\nCommitted. Target row counts match the source.")
    except Exception:
        dst.rollback()
        print("\nFailed; rolled back. The target is unchanged.", file=sys.stderr)
        raise
    finally:
        dst.close()
        src.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
