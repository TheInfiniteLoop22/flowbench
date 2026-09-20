"""Query 7 (P1): lost-trip estimate from station_hourly_balance. See
docs/SPEC.md §4 query 7 for the stated assumptions this relies on.

Usage: python analysis/q07_lost_trips.py
"""
import pathlib
import time

from db import get_conn

SQL = (pathlib.Path(__file__).resolve().parent / "queries" / "07_lost_trip_estimate.sql").read_text()


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            t0 = time.time()
            cur.execute(SQL)
            rows = cur.fetchall()
            elapsed = time.time() - t0
            print(f"{len(rows):,} stations with at least one likely-empty hour, in {elapsed:.1f}s\n")

            total_lost = sum(r[4] for r in rows)
            cur.execute("SELECT count(*) FROM warehouse.fact_trips")
            total_trips = cur.fetchone()[0]
            print(f"Estimated total lost trips (network-wide, 12 months): {total_lost:,.0f}")
            print(f"  as a share of observed trips: {total_lost/total_trips:.2%}\n")

            print("Top 15 stations by estimated lost trips:")
            for station_id, name, empty_hours, hours_obs, lost in rows[:15]:
                print(f"  {name[:40]:40}  empty_hours={empty_hours:>5,}/{hours_obs:<6,}  "
                      f"est. lost trips={lost:>8,.0f}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
