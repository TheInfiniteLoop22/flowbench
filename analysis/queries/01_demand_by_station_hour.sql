-- Query 1: demand by station/hour-of-day.
-- Demand = trips *started* at a station (outflow), grouped by hour-of-day
-- (0-23), averaged over every calendar day in the window so it reads as
-- "typical Tuesday-at-8am" rather than a raw sum. See SPEC.md §4 query 1.
--
-- city = 'new_york' (second-city stretch): this query and the recorded
-- RESULTS.md numbers predate Chicago's data landing in the same
-- fact_trips table — without this filter, re-running it today would
-- silently blend both cities' station-hour counts together. See query
-- 10 for the cross-city comparison.
SELECT
    start_station_id                       AS station_id,
    extract(hour FROM start_time)::int     AS hour_of_day,
    count(*)                               AS trip_count,
    count(*)::numeric / (SELECT count(DISTINCT date) FROM warehouse.dim_time) AS avg_trips_per_day
FROM warehouse.fact_trips
WHERE start_station_id IS NOT NULL AND city = 'new_york'
GROUP BY 1, 2
ORDER BY 1, 2;
