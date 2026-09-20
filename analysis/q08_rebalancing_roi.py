"""Query 8 (P1): rebalancing ROI ranking — top 20 stations by estimated
lost trips recovered per truck-hour of rebalancing effort. This is the
headline artifact referenced in docs/SPEC.md §8 and feeds
GET /insights/rebalancing-candidates (Phase 4). See the .sql file for the
stated truck-capacity assumption.

Usage: python analysis/q08_rebalancing_roi.py
"""
import pathlib
import time

from db import get_conn

SQL = (pathlib.Path(__file__).resolve().parent / "queries" / "08_rebalancing_roi.sql").read_text()


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            t0 = time.time()
            cur.execute(SQL)
            rows = cur.fetchall()
            elapsed = time.time() - t0
            print(f"Top {len(rows)} rebalancing candidates in {elapsed:.1f}s\n")

            print(f"{'station':40}  {'deficit':>9}  {'lost trips':>11}  {'truck-hrs':>10}  {'trips/truck-hr':>15}")
            for station_id, name, deficit, lost, truck_hrs, roi in rows:
                print(f"{name[:40]:40}  {deficit:>9,}  {lost:>11,.0f}  {truck_hrs:>10,.1f}  {roi:>15.2f}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
