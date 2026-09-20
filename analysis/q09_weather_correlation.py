"""Query 9 (stretch): weather correlation via Open-Meteo's free historical
archive API (no key required). Joins system-wide daily trip counts
(reusing query 5's series) to daily precipitation and max temperature for
NYC, then tests correlation. See docs/SPEC.md §4 query 9.

Usage: python analysis/q09_weather_correlation.py
"""
import pathlib
import time
import urllib.request
import json

from scipy import stats

from db import get_conn

SQL = (pathlib.Path(__file__).resolve().parent / "queries" / "05_daily_demand.sql").read_text()

# Central Park, a reasonable single-point proxy for citywide NYC weather.
WEATHER_URL = (
    "https://archive-api.open-meteo.com/v1/archive"
    "?latitude=40.7829&longitude=-73.9654"
    "&start_date={start}&end_date={end}"
    "&daily=precipitation_sum,temperature_2m_max"
    "&timezone=America%2FNew_York"
)


def fetch_weather(start, end):
    url = WEATHER_URL.format(start=start, end=end)
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read())
    daily = data["daily"]
    return dict(zip(daily["time"], zip(daily["precipitation_sum"], daily["temperature_2m_max"])))


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            t0 = time.time()
            cur.execute(SQL)
            rows = cur.fetchall()
            print(f"{len(rows)} calendar days of trip data in {time.time() - t0:.1f}s")
    finally:
        conn.close()

    start, end = rows[0][0].isoformat(), rows[-1][0].isoformat()
    print(f"Fetching Open-Meteo daily weather for {start}..{end}...")
    t0 = time.time()
    weather = fetch_weather(start, end)
    print(f"  got {len(weather)} days in {time.time() - t0:.1f}s\n")

    trips, precip, tmax = [], [], []
    missing = 0
    for date, is_weekend, is_holiday, trip_count in rows:
        w = weather.get(date.isoformat())
        if w is None or w[0] is None or w[1] is None:
            missing += 1
            continue
        trips.append(trip_count)
        precip.append(w[0])
        tmax.append(w[1])
    print(f"matched {len(trips)}/{len(rows)} days ({missing} missing from weather API)\n")

    r_precip, p_precip = stats.spearmanr(precip, trips)
    r_temp, p_temp = stats.spearmanr(tmax, trips)
    print(f"Precipitation vs. daily trips:  Spearman r={r_precip:.3f}, p={p_precip:.2e}")
    print(f"Max temp vs. daily trips:       Spearman r={r_temp:.3f}, p={p_temp:.2e}")

    # Simple, interpretable effect size: trips on wet vs. dry days.
    wet = [t for t, p in zip(trips, precip) if p > 1.0]   # >1mm counted as a "wet" day
    dry = [t for t, p in zip(trips, precip) if p <= 1.0]
    if wet and dry:
        u_stat, p_value = stats.mannwhitneyu(dry, wet, alternative="two-sided")
        wet_mean, dry_mean = sum(wet) / len(wet), sum(dry) / len(dry)
        pct_change = wet_mean / dry_mean - 1
        direction = "fewer" if pct_change < 0 else "more"
        print(f"\nWet days (>1mm precip, n={len(wet)}, mean={wet_mean:,.0f}/day) have "
              f"{abs(pct_change):.1%} {direction} trips than dry days "
              f"(n={len(dry)}, mean={dry_mean:,.0f}/day), Mann-Whitney p={p_value:.2e}")


if __name__ == "__main__":
    main()
