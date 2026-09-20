-- Stretch (docs/PHASE_PLAN.md "Advanced/stretch"): exposes analysis/q06's
-- station typology (commuter-hub / leisure / mixed) via the API/dashboard
-- instead of leaving it as a one-off analysis script result. Same
-- NTILE(3) commute-index/weekend-share classification as
-- analysis/queries/06_station_typology.sql, precomputed once per
-- warehouse build (identical performance rationale as 0004-0007).
CREATE MATERIALIZED VIEW IF NOT EXISTS warehouse.station_typology_agg AS
WITH station_hour AS (
    SELECT
        f.start_station_id AS station_id,
        t.is_weekend,
        extract(hour FROM f.start_time)::int AS hour_of_day
    FROM warehouse.fact_trips f
    JOIN warehouse.dim_time t ON t.date = f.start_date
    WHERE f.start_station_id IS NOT NULL AND NOT t.is_holiday
),
per_station AS (
    SELECT
        station_id,
        count(*) FILTER (WHERE NOT is_weekend) AS weekday_trips,
        count(*) FILTER (WHERE is_weekend)     AS weekend_trips,
        count(*) FILTER (WHERE NOT is_weekend AND hour_of_day BETWEEN 7 AND 10)  AS am_peak_trips,
        count(*) FILTER (WHERE NOT is_weekend AND hour_of_day BETWEEN 16 AND 19) AS pm_peak_trips,
        count(*) AS total_trips
    FROM station_hour
    GROUP BY station_id
    HAVING count(*) >= 100
),
metrics AS (
    SELECT
        station_id,
        total_trips,
        (am_peak_trips + pm_peak_trips)::numeric / NULLIF(weekday_trips, 0) AS commute_index,
        (weekend_trips::numeric / NULLIF(total_trips, 0)) / (2.0 / 7.0) AS weekend_share_index
    FROM per_station
),
tercile AS (
    SELECT *,
        ntile(3) OVER (ORDER BY commute_index)       AS commute_tercile,
        ntile(3) OVER (ORDER BY weekend_share_index) AS weekend_tercile
    FROM metrics
)
SELECT
    station_id,
    total_trips,
    round(commute_index, 3)       AS commute_index,
    round(weekend_share_index, 3) AS weekend_share_index,
    CASE
        WHEN commute_tercile = 3 AND weekend_tercile = 1 THEN 'commuter-hub'
        WHEN weekend_tercile = 3 AND commute_tercile = 1 THEN 'leisure'
        ELSE 'mixed'
    END AS typology
FROM tercile
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS ux_station_typology_agg ON warehouse.station_typology_agg (station_id);
