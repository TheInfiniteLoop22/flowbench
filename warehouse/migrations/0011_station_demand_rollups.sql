-- Deployment prep: api/queries.py's STATION_DAILY_DEMAND and
-- STATION_DEMAND both queried warehouse.fact_trips directly, filtered
-- to a single station_id. Fine locally (fact_trips is indexed on
-- start_station_id, a single station's slice is thousands of rows,
-- not millions) -- but it means a production deploy of the API needs
-- the full 17GB fact_trips table present, which doesn't fit any free
-- Postgres tier. Same precompute-once-per-build pattern as
-- 0004-0008/0010: two small station-keyed rollups replace those two
-- live queries so fact_trips itself never has to ship to prod.
--
-- No city column needed on either: station_id is already globally
-- unique across cities (see 0009/0010's comments), same reasoning as
-- station_hourly_balance_hourly_agg/rebalancing_candidates_agg/
-- station_typology_agg.

-- Backs STATION_DAILY_DEMAND (the daily series behind the forecast
-- endpoint's 7-day trailing average) -- ~4,530 stations x up to 367
-- days, a couple million rows at most, vs. fact_trips's 51.8M.
CREATE MATERIALIZED VIEW IF NOT EXISTS warehouse.station_daily_demand_agg AS
SELECT start_station_id AS station_id, start_date AS date, count(*) AS trip_count
FROM warehouse.fact_trips
WHERE start_station_id IS NOT NULL
GROUP BY start_station_id, start_date
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS ux_station_daily_demand_agg
    ON warehouse.station_daily_demand_agg (station_id, date);

-- Backs STATION_DEMAND (the hour-of-day curve behind /stations/{id},
-- with the dashboard's 7d/30d/90d/all-time range toggle). The
-- dashboard only ever asks for one of those four fixed ranges
-- (dashboard/src/components/StationDetail.tsx's RANGES), so rather
-- than storing per-day-per-hour granularity (which would be roughly
-- fact_trips-sized again), precompute exactly those four range
-- buckets per station per hour. range_days=0 is the "all time"
-- sentinel (NULL would break the unique index's duplicate handling).
CREATE MATERIALIZED VIEW IF NOT EXISTS warehouse.station_hourly_demand_agg AS
WITH station_max AS (
    SELECT start_station_id AS station_id, max(start_date) AS max_date
    FROM warehouse.fact_trips
    WHERE start_station_id IS NOT NULL
    GROUP BY start_station_id
),
ranges (range_days) AS (VALUES (7), (30), (90), (0))
SELECT
    f.start_station_id AS station_id,
    r.range_days,
    extract(hour FROM f.start_time)::int AS hour_of_day,
    count(*) AS total_trips,
    count(DISTINCT f.start_date) AS distinct_days
FROM warehouse.fact_trips f
JOIN station_max sm ON sm.station_id = f.start_station_id
CROSS JOIN ranges r
WHERE f.start_station_id IS NOT NULL
  AND (r.range_days = 0 OR f.start_date >= sm.max_date - r.range_days * interval '1 day')
GROUP BY f.start_station_id, r.range_days, 3
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS ux_station_hourly_demand_agg
    ON warehouse.station_hourly_demand_agg (station_id, range_days, hour_of_day);
