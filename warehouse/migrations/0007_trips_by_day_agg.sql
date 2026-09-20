-- Phase 5: GET /insights/weekday-vs-weekend (hit by the dashboard's
-- Trends and Insights pages) joined dim_time to all 45.7M fact_trips
-- rows to count trips per day — measured ~5.9s per request. Same
-- precompute-once-per-build pattern as 0004/0005/0006: this is a ~367-
-- row daily total that doesn't change until the next warehouse rebuild.
CREATE MATERIALIZED VIEW IF NOT EXISTS warehouse.trips_by_day_agg AS
SELECT start_date AS date, count(*) AS trip_count
FROM warehouse.fact_trips
GROUP BY start_date
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS ux_trips_by_day_agg ON warehouse.trips_by_day_agg (date);
