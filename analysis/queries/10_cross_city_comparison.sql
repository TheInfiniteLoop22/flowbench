-- Query 10 (stretch, second city): per-city summary stats, parametrized
-- by :city. Run once per city and compare in Python (q10_cross_city.py)
-- rather than a single UNION query, since the weekday/weekend
-- significance test (like query 4) needs each city's daily series as its
-- own array for scipy, not pre-aggregated.
SELECT
    count(*)                                                       AS total_trips,
    count(DISTINCT start_station_id)                                AS distinct_start_stations,
    round(avg(duration_s))                                          AS mean_duration_s,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_s)         AS median_duration_s,
    round(100.0 * count(*) FILTER (WHERE user_type = 'casual') / count(*), 1) AS pct_casual
FROM warehouse.fact_trips
WHERE city = %(city)s;
