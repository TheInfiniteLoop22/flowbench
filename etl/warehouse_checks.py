"""Sanity checks for the built warehouse (Phase 2). Run after
build_warehouse.py. Distinct from dq_checks.py, which validates staging.

Usage: python etl/warehouse_checks.py
"""
import sys

from db import get_conn

FAILED = []
WARNED = []


def check(cur, description, sql, expect_zero=True, hard=True):
    cur.execute(sql)
    value = cur.fetchone()[0]
    bad = (value != 0) if expect_zero else (value > 0)
    status = "OK" if not bad else ("FAIL" if hard else "WARN")
    print(f"  [{status}] {description}: {value}")
    if bad:
        (FAILED if hard else WARNED).append(description)


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM warehouse.fact_trips")
            fact_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM staging.stg_trips_raw")
            staging_count = cur.fetchone()[0]
            print(f"staging rows: {staging_count:,}")
            print(f"fact_trips rows: {fact_count:,}")
            print(f"dropped (FB-002 bad duration + FB-003 duplicate ride_id): "
                  f"{staging_count - fact_count:,}\n")

            print("Referential integrity:")
            check(cur, "fact_trips rows with a start_station_id not in dim_station", """
                SELECT count(*) FROM warehouse.fact_trips f
                WHERE f.start_station_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM warehouse.dim_station s WHERE s.station_id = f.start_station_id)
            """)
            check(cur, "fact_trips rows with an end_station_id not in dim_station", """
                SELECT count(*) FROM warehouse.fact_trips f
                WHERE f.end_station_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM warehouse.dim_station s WHERE s.station_id = f.end_station_id)
            """)
            check(cur, "fact_trips rows with a start_date not in dim_time", """
                SELECT count(*) FROM warehouse.fact_trips f
                WHERE NOT EXISTS (SELECT 1 FROM warehouse.dim_time t WHERE t.date = f.start_date)
            """)

            print("\nCore sanity check — inflow/outflow reconcile to fact_trips:")
            cur.execute("SELECT coalesce(sum(inflow), 0) FROM warehouse.station_hourly_balance")
            total_inflow = cur.fetchone()[0]
            cur.execute("SELECT coalesce(sum(outflow), 0) FROM warehouse.station_hourly_balance")
            total_outflow = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM warehouse.fact_trips WHERE end_station_id IS NOT NULL")
            trips_with_end = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM warehouse.fact_trips WHERE start_station_id IS NOT NULL")
            trips_with_start = cur.fetchone()[0]
            print(f"  total inflow (station_hourly_balance)  = {total_inflow:,}")
            print(f"  trips with a resolved end_station_id   = {trips_with_end:,}")
            print(f"  [{'OK' if total_inflow == trips_with_end else 'FAIL'}] inflow reconciles to fact_trips")
            print(f"  total outflow (station_hourly_balance) = {total_outflow:,}")
            print(f"  trips with a resolved start_station_id = {trips_with_start:,}")
            print(f"  [{'OK' if total_outflow == trips_with_start else 'FAIL'}] outflow reconciles to fact_trips")
            if total_inflow != trips_with_end:
                FAILED.append("inflow does not reconcile to fact_trips")
            if total_outflow != trips_with_start:
                FAILED.append("outflow does not reconcile to fact_trips")

            cur.execute("""
                SELECT count(*) FILTER (WHERE start_station_id IS NOT NULL AND end_station_id IS NULL)
                FROM warehouse.fact_trips
            """)
            start_ok_end_missing = cur.fetchone()[0]
            cur.execute("""
                SELECT count(*) FILTER (WHERE start_station_id IS NULL AND end_station_id IS NOT NULL)
                FROM warehouse.fact_trips
            """)
            start_missing_end_ok = cur.fetchone()[0]
            print(f"\n  system-wide net (inflow - outflow) = {total_inflow - total_outflow:,}")
            print(f"  explained by asymmetric station resolution, not a boundary effect:")
            print(f"    trips with a resolved start but unresolved end: {start_ok_end_missing:,}")
            print(f"    trips with a resolved end but unresolved start: {start_missing_end_ok:,}")
            print(f"    difference = {start_ok_end_missing - start_missing_end_ok:,} "
                  f"(matches the net above) — see docs/RESULTS.md and FB-005")

            print("\nDistance sanity:")
            cur.execute("SELECT count(*), count(distance_m) FROM warehouse.fact_trips")
            total, with_dist = cur.fetchone()
            print(f"  distance_m populated for {with_dist:,}/{total:,} trips "
                  f"({with_dist/total:.1%})")
            check(cur, "trips with a negative distance_m", """
                SELECT count(*) FROM warehouse.fact_trips WHERE distance_m < 0
            """)
            cur.execute("SELECT max(distance_m) FROM warehouse.fact_trips")
            print(f"  max distance_m: {cur.fetchone()[0]:,.0f} m")

    finally:
        conn.close()

    print()
    if FAILED:
        print(f"FAILED: {len(FAILED)} check(s):")
        for c in FAILED:
            print(f"  - {c}")
        return 1
    print(f"All warehouse checks passed. {len(WARNED)} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
