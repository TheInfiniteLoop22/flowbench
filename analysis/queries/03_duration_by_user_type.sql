-- Query 3: trip-duration distribution by user type. Excludes FB-002 rows
-- (non-positive duration) — already dropped at warehouse-load time, so no
-- extra filter needed here. See SPEC.md §4 query 3.
SELECT
    user_type,
    count(*)                                              AS n,
    round(avg(duration_s))                                AS mean_s,
    percentile_cont(0.5)  WITHIN GROUP (ORDER BY duration_s) AS median_s,
    percentile_cont(0.9)  WITHIN GROUP (ORDER BY duration_s) AS p90_s,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY duration_s) AS p99_s,
    round(stddev(duration_s))                             AS stddev_s,
    max(duration_s)                                       AS max_s
FROM warehouse.fact_trips
WHERE city = 'new_york'  -- second-city stretch: scope to the original NYC-only result, see query 10
GROUP BY user_type
ORDER BY user_type;
