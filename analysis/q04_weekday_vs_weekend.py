"""Query 4: weekday vs. weekend demand comparison, with a significance
test picked by the observed distribution shape rather than defaulted to
a t-test. See docs/SPEC.md §4 query 4.

Holidays are excluded from both groups: a holiday Tuesday behaves like a
weekend day demand-wise, and folding it into "weekday" would bias the
weekday group low and understate the real weekday/weekend gap.

Usage: python analysis/q04_weekday_vs_weekend.py
"""
import pathlib
import time

from scipy import stats

from db import get_conn

SQL = (pathlib.Path(__file__).resolve().parent / "queries" / "04_weekday_vs_weekend.sql").read_text()


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            t0 = time.time()
            cur.execute(SQL)
            rows = cur.fetchall()
            elapsed = time.time() - t0
            print(f"{len(rows)} calendar days in {elapsed:.1f}s")

            cur.execute("SELECT count(*) FROM warehouse.fact_trips")
            total_trips = cur.fetchone()[0]
            total_here = sum(r[3] for r in rows)
            status = "OK" if total_here == total_trips else "FAIL"
            print(f"  [{status}] sum(trip_count) across all days == fact_trips rows: "
                  f"{total_here:,} vs {total_trips:,}\n")

            weekday = [r[3] for r in rows if not r[1] and not r[2]]
            weekend = [r[3] for r in rows if r[1] and not r[2]]
            holidays_dropped = sum(1 for r in rows if r[2])
            print(f"weekday days: n={len(weekday)}, weekend days: n={len(weekend)}, "
                  f"holidays excluded from both groups: {holidays_dropped}\n")

            print(f"weekday: mean={sum(weekday)/len(weekday):,.0f} trips/day, "
                  f"median={sorted(weekday)[len(weekday)//2]:,} trips/day")
            print(f"weekend: mean={sum(weekend)/len(weekend):,.0f} trips/day, "
                  f"median={sorted(weekend)[len(weekend)//2]:,} trips/day\n")

            # Pick the test based on shape, don't default to a t-test:
            # Shapiro-Wilk normality check on each group.
            wd_stat, wd_p = stats.shapiro(weekday)
            we_stat, we_p = stats.shapiro(weekend)
            print(f"Shapiro-Wilk normality: weekday p={wd_p:.4f}, weekend p={we_p:.4f}")
            both_normal = wd_p > 0.05 and we_p > 0.05

            if both_normal:
                test_name = "Welch's t-test (both groups pass normality, unequal variances assumed)"
                t_stat, p_value = stats.ttest_ind(weekday, weekend, equal_var=False)
                stat_label, stat_value = "t", t_stat
            else:
                test_name = "Mann-Whitney U (at least one group fails normality)"
                u_stat, p_value = stats.mannwhitneyu(weekday, weekend, alternative="two-sided")
                stat_label, stat_value = "U", u_stat

            print(f"\nTest used: {test_name}")
            print(f"  {stat_label} = {stat_value:.1f}, p = {p_value:.2e}")

            diff_pct = (sum(weekday) / len(weekday)) / (sum(weekend) / len(weekend)) - 1
            print(f"\nWeekdays average {diff_pct:+.1%} trips/day vs. weekends "
                  f"(p {'< 0.001' if p_value < 0.001 else f'= {p_value:.4f}'}, "
                  f"n={len(weekday)} weekday / {len(weekend)} weekend days).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
