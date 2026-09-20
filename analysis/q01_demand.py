"""Query 1: demand by station/hour. See docs/SPEC.md §4.

Usage: python analysis/q01_demand.py
"""
import pathlib
import time

from db import get_conn

SQL = (pathlib.Path(__file__).resolve().parent / "queries" / "01_demand_by_station_hour.sql").read_text()


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            t0 = time.time()
            cur.execute(SQL)
            rows = cur.fetchall()
            elapsed = time.time() - t0
            print(f"{len(rows):,} station-hour rows in {elapsed:.1f}s")

            # Sanity check: total demand here should equal fact_trips rows
            # with a resolved start station (the same figure warehouse_checks
            # reports as trips_with_start).
            total_demand = sum(r[2] for r in rows)
            cur.execute("SELECT count(*) FROM warehouse.fact_trips WHERE start_station_id IS NOT NULL")
            trips_with_start = cur.fetchone()[0]
            status = "OK" if total_demand == trips_with_start else "FAIL"
            print(f"  [{status}] sum(trip_count) == trips with resolved start_station_id: "
                  f"{total_demand:,} vs {trips_with_start:,}")

            # System-wide hourly demand curve (sum across all stations).
            by_hour = {}
            for station_id, hour, trip_count, avg_per_day in rows:
                by_hour[hour] = by_hour.get(hour, 0) + trip_count
            total = sum(by_hour.values())
            print("\nSystem-wide demand by hour-of-day (share of daily total):")
            for hour in sorted(by_hour):
                share = by_hour[hour] / total
                bar = "#" * int(share * 200)
                print(f"  {hour:02d}:00  {share:6.2%}  {bar}")

            peak_hour = max(by_hour, key=by_hour.get)
            trough_hour = min(by_hour, key=by_hour.get)
            print(f"\nPeak hour: {peak_hour:02d}:00 ({by_hour[peak_hour]:,} trips, "
                  f"{by_hour[peak_hour]/total:.1%} of daily demand)")
            print(f"Trough hour: {trough_hour:02d}:00 ({by_hour[trough_hour]:,} trips, "
                  f"{by_hour[trough_hour]/total:.1%} of daily demand)")

            # Top 10 station-hour combos by average trips/day — the busiest
            # single station-hour slots in the network.
            top10 = sorted(rows, key=lambda r: r[3], reverse=True)[:10]
            print("\nTop 10 busiest station-hour slots (avg trips/day):")
            for station_id, hour, trip_count, avg_per_day in top10:
                print(f"  station {station_id:>10}  {hour:02d}:00  {avg_per_day:6.1f} trips/day avg")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
