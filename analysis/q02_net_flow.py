"""Query 2: net inflow/outflow per station (rebalancing signal). See
docs/SPEC.md §4.

Usage: python analysis/q02_net_flow.py
"""
import pathlib
import time

from db import get_conn

SQL = (pathlib.Path(__file__).resolve().parent / "queries" / "02_net_flow_by_station.sql").read_text()


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            t0 = time.time()
            cur.execute(SQL)
            rows = cur.fetchall()
            elapsed = time.time() - t0
            print(f"{len(rows):,} stations in {elapsed:.1f}s")

            # Sanity check: system-wide sum of net_balance across all
            # stations should equal the FB-005 asymmetry documented in
            # docs/RESULTS.md (inflow - outflow at the fact_trips level).
            total_net = sum(r[4] for r in rows)
            print(f"  system-wide sum(net_balance) across all stations: {total_net:,} "
                  f"(cross-check against warehouse_checks.py's inflow/outflow reconciliation)")

            bleeders = rows[:10]
            accumulators = sorted(rows, key=lambda r: r[4], reverse=True)[:10]

            print("\nTop 10 'bleeder' stations (net outflow — chronically run low, restock candidates):")
            for station_id, name, inflow, outflow, net, hours in bleeders:
                print(f"  {station_id:>10}  {name[:40]:40}  net {net:>8,}  (in {inflow:,} / out {outflow:,})")

            print("\nTop 10 'accumulator' stations (net inflow — chronically fill up, empty candidates):")
            for station_id, name, inflow, outflow, net, hours in accumulators:
                print(f"  {station_id:>10}  {name[:40]:40}  net {net:>8,}  (in {inflow:,} / out {outflow:,})")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
