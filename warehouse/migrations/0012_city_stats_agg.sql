-- Deployment prep continued (see 0011_*.sql): GET /cities' CITIES query
-- also aggregated all of fact_trips live (count(*) + count(DISTINCT
-- start_station_id) grouped by city). Two rows, precomputed like
-- everything else -- fact_trips has no place in production.
CREATE MATERIALIZED VIEW IF NOT EXISTS warehouse.city_stats_agg AS
SELECT city, count(*) AS trip_count, count(DISTINCT start_station_id) AS station_count
FROM warehouse.fact_trips
GROUP BY city
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS ux_city_stats_agg ON warehouse.city_stats_agg (city);
