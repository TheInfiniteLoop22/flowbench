"""Query 7: rebalancing ROI ranking — top 20 stations by estimated
lost trips recovered per truck-hour of rebalancing effort. This is an
exploratory, assumption-based ranking and feeds
GET /insights/rebalancing-candidates. See the .sql file for the
stated truck-capacity assumption.

Usage: python analysis/q07_rebalancing_roi.py
"""
import pathlib
import time

from db import get_conn

SQL = (pathlib.Path(__file__).resolve().parent / "queries" / "07_rebalancing_roi.sql").read_text()


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            t0 = time.time()
            cur.execute(SQL)
            rows = cur.fetchall()
            elapsed = time.time() - t0
            print(f"Top {len(rows)} rebalancing candidates in {elapsed:.1f}s\n")

            print(f"{'station':40}  {'episodes':>9}  {'lost trips':>11}  {'truck-hrs':>10}  {'trips/truck-hr':>15}")
            for station_id, name, episodes, lost, truck_hrs, roi in rows:
                print(f"{name[:40]:40}  {episodes:>9,}  {lost:>11,.0f}  {truck_hrs:>10,.1f}  {roi:>15.2f}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
