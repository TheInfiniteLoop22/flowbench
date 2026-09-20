-- Phase 5: the dashboard's city-wide trends view needs a system-wide
-- hourly demand curve (analysis/q01's system-wide rollup). Same
-- performance lesson as 0004: precompute the ~24-row aggregate once per
-- warehouse build instead of scanning all 45.7M fact_trips rows per
-- dashboard page load.
CREATE MATERIALIZED VIEW IF NOT EXISTS warehouse.demand_by_hour_agg AS
SELECT
    extract(hour FROM start_time)::int AS hour_of_day,
    count(*) AS trip_count
FROM warehouse.fact_trips
WHERE start_station_id IS NOT NULL
GROUP BY 1
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS ux_demand_by_hour_agg ON warehouse.demand_by_hour_agg (hour_of_day);
