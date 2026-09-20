"""Query 10 (stretch, second city): NYC (Citi Bike) vs. Chicago (Divvy)
comparison. See docs/PHASE_PLAN.md "Advanced/stretch" and
docs/PROGRESS_LOG.md for how the second city was added.

Usage: python analysis/q10_cross_city.py
"""
import pathlib
import time

from scipy import stats

from db import get_conn

SUMMARY_SQL = (pathlib.Path(__file__).resolve().parent / "queries" / "10_cross_city_comparison.sql").read_text()

DAILY_SQL = """
    SELECT t.date, t.is_weekend, t.is_holiday, count(f.ride_id) AS trip_count
    FROM warehouse.dim_time t
    LEFT JOIN warehouse.fact_trips f ON f.start_date = t.date AND f.city = %(city)s
    GROUP BY t.date, t.is_weekend, t.is_holiday
    ORDER BY t.date
"""

HOURLY_SQL = """
    SELECT extract(hour FROM start_time)::int AS hour_of_day, count(*) AS trip_count
    FROM warehouse.fact_trips
    WHERE city = %(city)s AND start_station_id IS NOT NULL
    GROUP BY 1 ORDER BY 1
"""

CITIES = ["new_york", "chicago"]


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            t0 = time.time()
            summaries = {}
            for city in CITIES:
                cur.execute(SUMMARY_SQL, {"city": city})
                cols = [d.name for d in cur.description]
                summaries[city] = dict(zip(cols, cur.fetchone()))
            print(f"queried in {time.time() - t0:.1f}s\n")

            print(f"{'metric':30}  {'new_york':>15}  {'chicago':>15}")
            for key in summaries["new_york"]:
                nyc, chi = summaries["new_york"][key], summaries["chicago"][key]
                print(f"{key:30}  {nyc!s:>15}  {chi!s:>15}")

            weekday_by_city = {}
            weekend_by_city = {}
            for city in CITIES:
                cur.execute(DAILY_SQL, {"city": city})
                rows = cur.fetchall()
                weekday_by_city[city] = [r[3] for r in rows if not r[1] and not r[2]]
                weekend_by_city[city] = [r[3] for r in rows if r[1] and not r[2]]

            print("\nWeekday vs. weekend, per city:")
            for city in CITIES:
                wd, we = weekday_by_city[city], weekend_by_city[city]
                _, p = stats.mannwhitneyu(wd, we, alternative="two-sided")
                pct = (sum(wd) / len(wd)) / (sum(we) / len(we)) - 1
                print(f"  {city}: weekday {pct:+.1%} vs. weekend (Mann-Whitney p={p:.2e})")

            hourly_by_city = {}
            for city in CITIES:
                cur.execute(HOURLY_SQL, {"city": city})
                rows = cur.fetchall()
                total = sum(r[1] for r in rows)
                hourly_by_city[city] = {r[0]: r[1] / total for r in rows}

            print("\nPeak/trough hour, per city:")
            for city in CITIES:
                by_hour = hourly_by_city[city]
                peak = max(by_hour, key=by_hour.get)
                trough = min(by_hour, key=by_hour.get)
                print(f"  {city}: peak {peak:02d}:00 ({by_hour[peak]:.1%}), "
                      f"trough {trough:02d}:00 ({by_hour[trough]:.1%}), "
                      f"ratio {by_hour[peak]/by_hour[trough]:.1f}x")

            # Do the two cities' hourly demand *shapes* differ, or is one
            # just a scaled-up version of the other? Spearman on the
            # 24-hour share vectors answers "same shape" vs. "different
            # rhythm" independent of NYC's much larger absolute volume.
            hours = sorted(hourly_by_city["new_york"])
            nyc_shape = [hourly_by_city["new_york"][h] for h in hours]
            chi_shape = [hourly_by_city["chicago"].get(h, 0) for h in hours]
            rho, p = stats.spearmanr(nyc_shape, chi_shape)
            print(f"\nHourly demand-shape correlation (NYC vs. Chicago, Spearman): "
                  f"rho={rho:.3f}, p={p:.2e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
